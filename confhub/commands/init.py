"""nxs init 명령어 - ConfHub Registry 초기화"""

import json
from pathlib import Path

import yaml

from confhub.core.registry import Registry
from confhub.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)

# ── 템플릿 상수 ────────────────────────────────────────────────────────────────

CONFHUB_CONFIG_TEMPLATE = {
    "version": "1.0.0",
    "registry": {
        "name": "my-confhub",
        "description": "ConfHub 에이전트 설정 Registry",
    },
    "remote": {
        "url": None,
        "branch": "main",
        "auto_pull": False,
    },
    "defaults": {
        "inheritance_strategy": "deep-merge",
        "link_mode": "symlink",
    },
}

AGENT_CONFIG_TEMPLATE = """\
agent: claude
version: "1.0.0"
scope: root

merge:
  CLAUDE.md: append
  settings.json: deep-merge
"""

CLAUDE_MD_TEMPLATE = """\
# 공통 AI 에이전트 규칙

## 코딩 표준
- 함수 단위 단일 책임 원칙 준수
- 명확한 변수명과 함수명 사용

## 보안 규칙
- 환경 변수는 .env 파일로만 관리
- 민감 정보 로그 출력 금지

## Git 규칙
- 커밋 메시지: [타입]: [내용] 형식
"""

PRE_COMMIT_HOOK_TEMPLATE = """\
#!/bin/sh
# ConfHub: 커밋 전 자동으로 resolved/ 를 최신 상태로 빌드합니다.
confhub resolve --all && git add resolved/
"""

SETTINGS_JSON_TEMPLATE = {
    "model": "claude-sonnet-4-6",
    "permissions": {
        "allow": [],
        "deny": [],
    },
}


# ── 핵심 로직 ──────────────────────────────────────────────────────────────────


def _find_git_root(path: Path) -> Path | None:
    """주어진 경로에서 가장 가까운 git root를 찾습니다."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(path),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None


def _install_pre_commit_hook(registry_path: Path) -> None:
    """Registry git 저장소에 pre-commit 훅을 설치합니다."""
    import subprocess

    # 현재 경로의 git root를 찾거나, 없으면 git 초기화
    git_root = _find_git_root(registry_path)
    if git_root is None:
        subprocess.run(["git", "init", str(registry_path)], check=True, capture_output=True)
        git_root = registry_path

    hooks_dir = git_root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_file = hooks_dir / "pre-commit"
    hook_file.write_text(PRE_COMMIT_HOOK_TEMPLATE, encoding="utf-8")
    hook_file.chmod(0o755)


def do_init(path: Path | None, from_repo: str | None) -> None:
    """nxs init 핵심 로직.

    Args:
        path: Registry를 생성할 경로. None이면 Registry.DEFAULT_PATH 사용.
        from_repo: Git 레포 URL (Phase 7에서 완성 예정).
    """
    # --from-repo: Phase 7에서 완성 예정
    if from_repo is not None:
        print_error("--from-repo 옵션은 Phase 7에서 지원될 예정입니다.")
        return

    # 대상 경로 결정 (기본: 현재 디렉토리)
    registry_path = Path(path) if path is not None else Path.cwd()

    # 이미 초기화된 경우 훅만 업데이트 후 종료
    registry = Registry(registry_path)
    if registry.is_initialized():
        print_warning(f"이미 초기화된 Registry입니다: {registry_path}")
        print_info("pre-commit 훅을 최신 버전으로 업데이트합니다...")
        _install_pre_commit_hook(registry_path)
        print_success("pre-commit 훅 업데이트 완료.")
        return

    try:
        console.print(f"\n[bold blue]ConfHub Registry 초기화[/bold blue]: {registry_path}\n")

        # ── [1/5] 디렉토리 구조 생성 ─────────────────────────────────────────
        print_info("[1/5] 디렉토리 구조 생성...")
        registry.root_agents_path.mkdir(parents=True, exist_ok=True)
        registry.apps_path.mkdir(parents=True, exist_ok=True)
        registry.resolved_path.mkdir(parents=True, exist_ok=True)
        registry.links_path.mkdir(parents=True, exist_ok=True)

        # ── [2/5] confhub.config.yaml 생성 ─────────────────────────────────────
        print_info("[2/5] confhub.config.yaml 생성...")
        with open(registry.config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                CONFHUB_CONFIG_TEMPLATE,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        # ── [3/5] 기본 Claude 에이전트 템플릿 생성 ───────────────────────────
        print_info("[3/5] 기본 Claude 에이전트 템플릿 생성...")
        claude_agent_dir = registry.get_root_agent_path("claude")
        claude_dot_dir = claude_agent_dir / ".claude"
        claude_dot_dir.mkdir(parents=True, exist_ok=True)

        # agent.config.yaml
        agent_config_file = claude_agent_dir / "agent.config.yaml"
        agent_config_file.write_text(AGENT_CONFIG_TEMPLATE, encoding="utf-8")

        # .claude/CLAUDE.md
        (claude_dot_dir / "CLAUDE.md").write_text(CLAUDE_MD_TEMPLATE, encoding="utf-8")

        # .claude/settings.json
        with open(claude_dot_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump(SETTINGS_JSON_TEMPLATE, f, indent=2, ensure_ascii=False)

        # ── [4/6] links/links.json 생성 ──────────────────────────────────────
        print_info("[4/6] links/links.json 생성...")
        with open(registry.links_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        # ── [5/6] git 초기화 및 pre-commit 훅 설치 ───────────────────────────
        print_info("[5/6] git 초기화 및 pre-commit 훅 설치...")
        _install_pre_commit_hook(registry_path)

        # ── [6/6] ~/.confhubrc 등록 ─────────────────────────────────────────────
        print_info("[6/6] ~/.confhubrc에 경로 등록...")
        Registry.save_nexusrc(registry_path)

        console.print()
        print_success(f"Registry 초기화 완료: {registry_path}")
        print_info("apps/ 파일 수정 후 git commit 시 resolved/ 가 자동으로 갱신됩니다.")

    except PermissionError as exc:
        print_error(f"권한 오류: {exc}")
    except OSError as exc:
        print_error(f"파일 시스템 오류: {exc}")
