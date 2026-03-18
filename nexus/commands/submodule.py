"""nxs submodule 명령어 - Git Submodule로 설정 적용"""

import os
import subprocess
from pathlib import Path

import typer

from nexus.core.agents import get_agent
from nexus.core.merger import ConfigMerger
from nexus.core.registry import Registry, RegistryNotFoundError
from nexus.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from nexus.utils.git import GitError, GitRepo

submodule_app = typer.Typer(help="Git Submodule로 설정 적용")

SUBMODULE_DIR = ".nexus-config"


# ── 유틸리티 ───────────────────────────────────────────────────────────────────


def _get_registry() -> Registry:
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """프로젝트 디렉토리에서 git 명령 실행"""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} 실패:\n{result.stderr.strip()}")
    return result


def _get_configured_agents(registry: Registry, app_name: str) -> list[str]:
    """앱에 설정된 에이전트 목록 반환"""
    app_agents_path = registry.get_app_path(app_name) / "agents"
    if not app_agents_path.exists():
        return []
    return [d.name for d in sorted(app_agents_path.iterdir()) if d.is_dir()]


def _resolve_target_agents(
    registry: Registry, app_name: str, agent_option: str | None
) -> list[str]:
    """적용할 에이전트 목록 결정 및 검증"""
    configured = _get_configured_agents(registry, app_name)
    if not configured:
        print_error(f"앱 '{app_name}'에 등록된 에이전트가 없습니다.")
        raise typer.Exit(1)

    if agent_option is None:
        return configured

    requested = [a.strip() for a in agent_option.split(",")]
    valid = [a for a in requested if a in configured]
    if not valid:
        print_error(f"요청한 에이전트가 앱에 없습니다: {', '.join(requested)}")
        raise typer.Exit(1)
    return valid


# ── 명령어 ─────────────────────────────────────────────────────────────────────


@submodule_app.command("add")
def submodule_add(
    app_name: str = typer.Argument(..., help="앱 이름"),
    target: Path | None = typer.Option(
        None, "--target", "-t", help="프로젝트 경로 (기본: 현재 디렉토리)"
    ),
    agent: str | None = typer.Option(
        None, "--agent", help="특정 에이전트만 적용 (쉼표 구분: claude,gemini)"
    ),
):
    """프로젝트에 nexus 설정을 git submodule로 적용합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if not registry.app_exists(app_name):
        print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다.")
        raise typer.Exit(1)

    # remote URL 확인
    nexus_repo = GitRepo(registry.base_path)
    remote_url = nexus_repo.get_remote_url()
    if not remote_url:
        print_error(
            "Registry의 원격 레포가 설정되지 않았습니다. 'nxs sync remote set <url>'로 설정하세요."
        )
        raise typer.Exit(1)

    # 대상 프로젝트 경로
    project_path = Path(target).resolve() if target else Path.cwd()
    if not project_path.exists():
        print_error(f"프로젝트 경로를 찾을 수 없습니다: {project_path}")
        raise typer.Exit(1)
    if not (project_path / ".git").exists():
        print_error(f"대상 디렉토리가 git 레포가 아닙니다: {project_path}")
        raise typer.Exit(1)

    # 적용할 에이전트 결정
    agent_ids = _resolve_target_agents(registry, app_name, agent)

    # resolve 실행 (resolved/ 최신화)
    print_info("[1/3] 설정 병합 중...")
    try:
        merger = ConfigMerger(registry.base_path)
        merger.resolve_app(app_name)
    except Exception as exc:
        print_error(f"resolve 실패: {exc}")
        raise typer.Exit(1)

    # resolved/ 포함하여 nexus 레포 push
    print_info(f"[2/3] resolved/ 를 remote에 push 중: {remote_url}")
    try:
        sha = nexus_repo.commit_all(f"chore: resolve {app_name}")
        if sha:
            print_info(f"      커밋: {sha[:8]}")
        nexus_repo.push()
    except GitError as exc:
        print_error(f"push 실패: {exc}")
        raise typer.Exit(1)

    print_info("[3/3] git submodule 추가 중...")
    # submodule 추가
    submodule_path = project_path / SUBMODULE_DIR
    if submodule_path.exists():
        print_warning(f"'{SUBMODULE_DIR}'이 이미 존재합니다. submodule 추가를 건너뜁니다.")
    else:
        try:
            _run_git(["submodule", "add", remote_url, SUBMODULE_DIR], cwd=project_path)
        except GitError as exc:
            print_error(str(exc))
            raise typer.Exit(1)

    # 에이전트별 상대 경로 심볼릭 링크 생성
    console.print()
    for agent_id in agent_ids:
        try:
            agent_cfg = get_agent(agent_id)
        except ValueError:
            print_warning(f"알 수 없는 에이전트: {agent_id}, 건너뜁니다.")
            continue

        # 심볼릭 링크 위치: project/<link_target>
        link_path = project_path / agent_cfg.link_target

        if link_path.exists() or link_path.is_symlink():
            print_warning(f"이미 존재합니다: {agent_cfg.link_target}, 건너뜁니다.")
            continue

        # submodule 내 대상 경로: .nexus-config/resolved/<app>/<agent>/<link_target>
        submodule_target_abs = (
            project_path / SUBMODULE_DIR / "resolved" / app_name / agent_id / agent_cfg.link_target
        )

        # 상대 경로 계산 (symlink 위치의 부모 디렉토리 기준)
        link_path.parent.mkdir(parents=True, exist_ok=True)
        rel_target = Path(os.path.relpath(submodule_target_abs, link_path.parent))

        link_path.symlink_to(rel_target)
        print_success(f"  {agent_cfg.link_target} → {rel_target}")

    console.print()
    print_success(f"'{app_name}' submodule 설정 완료: {project_path}")
    print_info("팀원은 레포 클론 후 'git submodule update --init'을 실행하세요.")


@submodule_app.command("remove")
def submodule_remove(
    app_name: str = typer.Argument(..., help="앱 이름"),
    target: Path | None = typer.Option(
        None, "--target", "-t", help="프로젝트 경로 (기본: 현재 디렉토리)"
    ),
    agent: str | None = typer.Option(
        None, "--agent", help="특정 에이전트 심볼릭 링크만 제거 (쉼표 구분: claude,gemini)"
    ),
    keep_submodule: bool = typer.Option(
        False, "--keep-submodule", help="submodule은 유지하고 심볼릭 링크만 제거"
    ),
):
    """프로젝트에서 nexus submodule 설정을 제거합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if not registry.app_exists(app_name):
        print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다.")
        raise typer.Exit(1)

    project_path = Path(target).resolve() if target else Path.cwd()
    if not project_path.exists():
        print_error(f"프로젝트 경로를 찾을 수 없습니다: {project_path}")
        raise typer.Exit(1)

    # 적용할 에이전트 결정
    agent_ids = _resolve_target_agents(registry, app_name, agent)

    # 심볼릭 링크 제거
    console.print()
    for agent_id in agent_ids:
        try:
            agent_cfg = get_agent(agent_id)
        except ValueError:
            continue

        link_path = project_path / agent_cfg.link_target
        if link_path.is_symlink():
            link_path.unlink()
            print_success(f"  심볼릭 링크 제거: {agent_cfg.link_target}")
        else:
            print_warning(f"  심볼릭 링크 없음: {agent_cfg.link_target}")

    # submodule 제거
    if not keep_submodule:
        submodule_path = project_path / SUBMODULE_DIR
        if submodule_path.exists():
            print_info(f"\n'{SUBMODULE_DIR}' submodule 제거 중...")
            try:
                _run_git(["submodule", "deinit", "-f", SUBMODULE_DIR], cwd=project_path)
                _run_git(["rm", "-f", SUBMODULE_DIR], cwd=project_path)
                git_modules_path = project_path / ".git" / "modules" / SUBMODULE_DIR
                if git_modules_path.exists():
                    import shutil

                    shutil.rmtree(git_modules_path)
                print_success(f"'{SUBMODULE_DIR}' submodule 제거 완료")
            except GitError as exc:
                print_error(str(exc))
                raise typer.Exit(1)
        else:
            print_warning(f"'{SUBMODULE_DIR}'이 존재하지 않습니다.")

    console.print()
    print_success(f"'{app_name}' submodule 설정 제거 완료: {project_path}")
