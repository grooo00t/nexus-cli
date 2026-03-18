"""nxs submodule 명령어 - Git Submodule로 설정 적용"""

import os
import subprocess
from pathlib import Path

import typer

from confhub.core.agents import get_agent
from confhub.core.merger import ConfigMerger
from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from confhub.utils.git import GitError, GitRepo

submodule_app = typer.Typer(help="Git Submodule로 설정 적용")

SUBMODULE_DIR = ".nexus-config"


# ── 유틸리티 ───────────────────────────────────────────────────────────────────


def _get_registry() -> Registry:
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """지정 디렉토리에서 git 명령 실행"""
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


def _apply_sparse_checkout(submodule_path: Path, app_name: str) -> None:
    """submodule에 sparse-checkout 적용 — resolved/<app>/ 만 체크아웃"""
    _run_git(["sparse-checkout", "init", "--cone"], cwd=submodule_path)
    _run_git(["sparse-checkout", "set", f"resolved/{app_name}"], cwd=submodule_path)


def _create_symlinks(project_path: Path, app_name: str, agent_ids: list[str]) -> list[str]:
    """에이전트별 상대 경로 심볼릭 링크 생성. 생성된 link_target 목록 반환."""
    created: list[str] = []
    for agent_id in agent_ids:
        try:
            agent_cfg = get_agent(agent_id)
        except ValueError:
            print_warning(f"알 수 없는 에이전트: {agent_id}, 건너뜁니다.")
            continue

        link_path = project_path / agent_cfg.link_target

        if link_path.exists() or link_path.is_symlink():
            print_warning(f"  이미 존재합니다: {agent_cfg.link_target}, 건너뜁니다.")
            continue

        submodule_target_abs = (
            project_path / SUBMODULE_DIR / "resolved" / app_name / agent_id / agent_cfg.link_target
        )

        link_path.parent.mkdir(parents=True, exist_ok=True)
        rel_target = Path(os.path.relpath(submodule_target_abs, link_path.parent))

        link_path.symlink_to(rel_target)
        print_success(f"  {agent_cfg.link_target} → {rel_target}")
        created.append(agent_cfg.link_target)

    return created


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
    """프로젝트에 confhub 설정을 git submodule + sparse-checkout으로 적용합니다."""
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

    agent_ids = _resolve_target_agents(registry, app_name, agent)

    # [1/4] resolve
    print_info("[1/4] 설정 병합 중...")
    try:
        ConfigMerger(registry.base_path).resolve_app(app_name)
    except Exception as exc:
        print_error(f"resolve 실패: {exc}")
        raise typer.Exit(1)

    # [2/4] nexus 레포 push (resolved/ 포함)
    print_info(f"[2/4] resolved/ 를 remote에 push 중: {remote_url}")
    try:
        sha = nexus_repo.commit_all(f"chore: resolve {app_name}")
        if sha:
            print_info(f"      커밋: {sha[:8]}")
        nexus_repo.push()
    except GitError as exc:
        print_error(f"push 실패: {exc}")
        raise typer.Exit(1)

    # [3/4] submodule 추가
    print_info("[3/4] git submodule 추가 중...")
    submodule_path = project_path / SUBMODULE_DIR
    if submodule_path.exists():
        print_warning(f"'{SUBMODULE_DIR}'이 이미 존재합니다. submodule 추가를 건너뜁니다.")
    else:
        try:
            _run_git(["submodule", "add", remote_url, SUBMODULE_DIR], cwd=project_path)
        except GitError as exc:
            print_error(str(exc))
            raise typer.Exit(1)

    # [4/4] sparse-checkout — resolved/<app>/ 만 체크아웃
    print_info(f"[4/4] sparse-checkout 적용 중: resolved/{app_name}/")
    try:
        _apply_sparse_checkout(submodule_path, app_name)
    except GitError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    # 심볼릭 링크 생성 + 프로젝트 레포에 커밋
    console.print()
    created_links = _create_symlinks(project_path, app_name, agent_ids)

    if created_links:
        try:
            _run_git(["add"] + created_links, cwd=project_path)
            _run_git(
                ["commit", "-m", f"chore: add confhub submodule for {app_name}"],
                cwd=project_path,
            )
            print_info(f"\n  심볼릭 링크 {len(created_links)}개를 프로젝트 레포에 커밋했습니다.")
        except GitError as exc:
            print_error(f"커밋 실패: {exc}")
            raise typer.Exit(1)

    console.print()
    print_success(f"'{app_name}' submodule 설정 완료: {project_path}")
    print_info(
        "팀원은 'git clone --recurse-submodules' 후 "
        "'nxs submodule init <app>'으로 sparse-checkout을 적용하세요."
    )


@submodule_app.command("init")
def submodule_init(
    app_name: str = typer.Argument(..., help="앱 이름"),
    target: Path | None = typer.Option(
        None, "--target", "-t", help="프로젝트 경로 (기본: 현재 디렉토리)"
    ),
):
    """클론 후 sparse-checkout을 적용합니다. (팀원용)"""
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

    submodule_path = project_path / SUBMODULE_DIR

    # submodule 초기화 (미완료 상태이면)
    if not submodule_path.exists() or not any(submodule_path.iterdir()):
        print_info("git submodule 초기화 중...")
        try:
            _run_git(["submodule", "update", "--init", SUBMODULE_DIR], cwd=project_path)
        except GitError as exc:
            print_error(str(exc))
            raise typer.Exit(1)

    if not submodule_path.exists():
        print_error(
            f"'{SUBMODULE_DIR}' submodule을 찾을 수 없습니다. "
            "먼저 'git submodule update --init'을 실행하세요."
        )
        raise typer.Exit(1)

    # sparse-checkout 적용 (resolved/<app>/ 만 체크아웃)
    print_info(f"sparse-checkout 적용 중: resolved/{app_name}/")
    try:
        _apply_sparse_checkout(submodule_path, app_name)
    except GitError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    console.print()
    print_success(f"'{app_name}' 초기화 완료: {project_path}")
    print_info("심볼릭 링크는 레포에 이미 포함되어 있습니다.")


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
    """프로젝트에서 confhub submodule 설정을 제거합니다."""
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
