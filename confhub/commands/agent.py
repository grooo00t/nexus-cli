"""nxs agent 명령어 - 에이전트 설정 관리"""

import shutil
from pathlib import Path

import typer
import yaml
from rich.panel import Panel
from rich.syntax import Syntax

from confhub.core.agents import get_agent
from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import (
    console,
    make_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)

app = typer.Typer(help="에이전트 설정 관리")


# ── 에이전트 config.yaml 템플릿 ────────────────────────────────────────────────


def _build_agent_config(agent_id: str, scope: str) -> dict:
    """agent.config.yaml 템플릿 생성"""
    agent = get_agent(agent_id)
    merge_dict = {}
    for filename in agent.default_files:
        base = Path(filename).name
        if base.endswith(".md"):
            merge_dict[base] = "append"
        elif base.endswith(".json"):
            merge_dict[base] = "deep-merge"
        else:
            merge_dict[base] = "overwrite"

    return {
        "agent": agent_id,
        "version": "1.0.0",
        "scope": scope,
        "merge": merge_dict,
    }


# ── 유틸리티 ───────────────────────────────────────────────────────────────────


def _get_registry() -> Registry:
    """기본 Registry를 반환하고, 초기화 여부를 확인한다."""
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


def _resolve_scope_and_dir(
    registry: Registry,
    agent_id: str,
    app_name: str | None,
    root: bool,
) -> tuple[str, Path]:
    """(scope, agent_dir) 튜플 반환. 유효성 검사도 포함."""
    if root and app_name:
        print_error("--root 와 --app 옵션을 동시에 사용할 수 없습니다.")
        raise typer.Exit(1)
    if not root and not app_name:
        print_error("--app <앱이름> 또는 --root 중 하나를 지정해야 합니다.")
        raise typer.Exit(1)

    if root:
        scope = "root"
        agent_dir = registry.get_root_agent_path(agent_id)
    else:
        assert app_name is not None
        if not registry.app_exists(app_name):
            print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다. (not found)")
            raise typer.Exit(1)
        scope = "app"
        agent_dir = registry.get_app_agent_path(app_name, agent_id)

    return scope, agent_dir


# ── 명령어 ─────────────────────────────────────────────────────────────────────


@app.command("add")
def agent_add(
    agent_id: str = typer.Argument(
        ..., help="에이전트 식별자 (claude, gemini, codex, cursor, copilot)"
    ),
    app_name: str | None = typer.Option(None, "--app", "-a", help="앱 이름"),
    root: bool = typer.Option(False, "--root", "-r", help="루트 레벨에 추가"),
):
    """에이전트 설정을 추가합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    # 에이전트 유효성 검사
    try:
        agent_cfg = get_agent(agent_id)
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    # 스코프 결정
    try:
        scope, agent_dir = _resolve_scope_and_dir(registry, agent_id, app_name, root)
    except typer.Exit:
        raise

    # 이미 존재 여부 확인
    if (agent_dir / "agent.config.yaml").exists():
        print_warning(f"에이전트 '{agent_id}' 설정이 이미 존재합니다. ({agent_dir})")
        raise typer.Exit(1)

    try:
        # 디렉토리 생성
        agent_dir.mkdir(parents=True, exist_ok=True)

        # agent.config.yaml 생성
        config = _build_agent_config(agent_id, scope)
        with open(agent_dir / "agent.config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # 기본 파일들 생성
        for rel_path, content in agent_cfg.default_files.items():
            file_path = agent_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        # app scope이면 app.config.yaml의 agents 리스트에 추가
        if scope == "app" and app_name:
            app_config = registry.load_app_config(app_name)
            agents_list = app_config.get("agents", [])
            if agent_id not in agents_list:
                agents_list.append(agent_id)
                app_config["agents"] = agents_list
                registry.save_app_config(app_name, app_config)

        print_success(f"에이전트 '{agent_id}' ({agent_cfg.display_name}) 추가 완료")

    except OSError as exc:
        print_error(f"파일 시스템 오류: {exc}")
        raise typer.Exit(1)


@app.command("list")
def agent_list(
    app_name: str | None = typer.Option(None, "--app", "-a", help="앱 이름"),
    root: bool = typer.Option(False, "--root", "-r", help="루트 레벨 목록"),
):
    """에이전트 목록을 표시합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if root and app_name:
        print_error("--root 와 --app 옵션을 동시에 사용할 수 없습니다.")
        raise typer.Exit(1)
    if not root and not app_name:
        print_error("--app <앱이름> 또는 --root 중 하나를 지정해야 합니다.")
        raise typer.Exit(1)

    if root:
        scope_label = "루트"
        agents_base = registry.root_agents_path
    else:
        assert app_name is not None
        if not registry.app_exists(app_name):
            print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다. (not found)")
            raise typer.Exit(1)
        scope_label = f"앱: {app_name}"
        agents_base = registry.get_app_path(app_name) / "agents"

    if not agents_base.exists():
        print_info(f"등록된 에이전트가 없습니다. ({scope_label})")
        return

    found_agents = []
    for agent_dir in sorted(agents_base.iterdir()):
        if agent_dir.is_dir() and (agent_dir / "agent.config.yaml").exists():
            found_agents.append(agent_dir.name)

    if not found_agents:
        print_info(f"등록된 에이전트가 없습니다. ({scope_label})")
        return

    table = make_table(f"에이전트 목록 ({scope_label})", ["Agent", "Display Name", "Files"])

    for agent_id in found_agents:
        try:
            agent_cfg = get_agent(agent_id)
            display_name = agent_cfg.display_name
        except ValueError:
            display_name = "(알 수 없음)"

        agent_dir = agents_base / agent_id
        actual_files = []
        for item in sorted(agent_dir.rglob("*")):
            if item.is_file() and item.name != "agent.config.yaml":
                actual_files.append(item.relative_to(agent_dir).as_posix())
        files_str = ", ".join(actual_files) if actual_files else "-"
        table.add_row(agent_id, display_name, files_str)

    console.print(table)


@app.command("show")
def agent_show(
    agent_id: str = typer.Argument(..., help="에이전트 식별자"),
    app_name: str | None = typer.Option(None, "--app", "-a", help="앱 이름"),
    root: bool = typer.Option(False, "--root", "-r", help="루트 레벨"),
    resolved: bool = typer.Option(False, "--resolved", help="상속 병합 후 최종값 조회"),
):
    """에이전트 설정을 표시합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if resolved:
        print_info("--resolved 옵션은 Phase 5에서 지원 예정입니다.")
        raise typer.Exit(0)

    # 에이전트 유효성 검사
    try:
        agent_cfg = get_agent(agent_id)
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    try:
        scope, agent_dir = _resolve_scope_and_dir(registry, agent_id, app_name, root)
    except typer.Exit:
        raise

    if not (agent_dir / "agent.config.yaml").exists():
        print_error(f"에이전트 '{agent_id}' 설정을 찾을 수 없습니다. ({agent_dir})")
        raise typer.Exit(1)

    # agent.config.yaml 내용 표시
    config_content = (agent_dir / "agent.config.yaml").read_text(encoding="utf-8")
    syntax = Syntax(config_content, "yaml", theme="monokai", line_numbers=True)
    console.print(
        Panel(syntax, title=f"에이전트: {agent_id} ({agent_cfg.display_name})", style="blue")
    )

    # 기본 파일들도 표시
    for rel_path in agent_cfg.default_files:
        file_path = agent_dir / rel_path
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            ext = Path(rel_path).suffix.lstrip(".") or "text"
            lang_map = {"md": "markdown", "json": "json", "yaml": "yaml", "yml": "yaml"}
            lang = lang_map.get(ext, "text")
            file_syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
            console.print(Panel(file_syntax, title=f"파일: {rel_path}", style="cyan"))


@app.command("remove")
def agent_remove(
    agent_id: str = typer.Argument(..., help="에이전트 식별자"),
    app_name: str | None = typer.Option(None, "--app", "-a", help="앱 이름"),
    root: bool = typer.Option(False, "--root", "-r", help="루트 레벨"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 삭제"),
):
    """에이전트 설정을 삭제합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    # 에이전트 유효성 검사
    try:
        get_agent(agent_id)
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    try:
        scope, agent_dir = _resolve_scope_and_dir(registry, agent_id, app_name, root)
    except typer.Exit:
        raise

    if not agent_dir.exists():
        print_error(f"에이전트 '{agent_id}' 설정을 찾을 수 없습니다. ({agent_dir})")
        raise typer.Exit(1)

    if not force:
        confirmed = typer.confirm(f"에이전트 '{agent_id}' 설정을 삭제하시겠습니까?")
        if not confirmed:
            print_info("삭제가 취소되었습니다.")
            raise typer.Exit(0)

    try:
        shutil.rmtree(agent_dir)

        # app scope이면 app.config.yaml의 agents 리스트에서 제거
        if scope == "app" and app_name:
            try:
                app_config = registry.load_app_config(app_name)
                agents_list = app_config.get("agents", [])
                if agent_id in agents_list:
                    agents_list.remove(agent_id)
                    app_config["agents"] = agents_list
                    registry.save_app_config(app_name, app_config)
            except FileNotFoundError:
                pass

        print_success(f"에이전트 '{agent_id}' 설정 삭제 완료")

    except OSError as exc:
        print_error(f"파일 시스템 오류: {exc}")
        raise typer.Exit(1)
