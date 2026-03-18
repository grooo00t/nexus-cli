"""nxs link/unlink 명령어 - 심볼릭 링크 관리"""

from pathlib import Path

import typer

from confhub.core.linker import Linker, LinkerError
from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import (
    console,
    make_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)

link_app = typer.Typer(help="심볼릭 링크 관리")


def _get_registry() -> Registry:
    """기본 Registry를 반환하고, 초기화 여부를 확인한다."""
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


def _parse_agents(agent_str: str | None) -> list[str] | None:
    """쉼표로 구분된 에이전트 문자열을 목록으로 변환"""
    if agent_str is None:
        return None
    return [a.strip() for a in agent_str.split(",") if a.strip()]


@link_app.callback(invoke_without_command=True)
def link_main(
    ctx: typer.Context,
    app_name: str | None = typer.Argument(None, help="앱 이름"),
    target: Path | None = typer.Option(
        None, "--target", "-t", help="링크할 프로젝트 경로 (기본: 현재 디렉토리)"
    ),
    agent: str | None = typer.Option(
        None, "--agent", help="특정 에이전트만 링크 (쉼표 구분: claude,gemini)"
    ),
):
    """앱 설정을 프로젝트에 심볼릭 링크로 연결합니다."""
    if ctx.invoked_subcommand is not None:
        return

    if app_name is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)

    do_link(app_name, target, agent)


@link_app.command("list")
def link_list():
    """등록된 링크 목록을 표시합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    linker = Linker(registry.base_path)
    links = linker.list_links()

    if not links:
        print_info("등록된 링크가 없습니다.")
        return

    table = make_table("링크 목록", ["App", "Project Path", "Agents", "Created At"])

    for app_name, entries in sorted(links.items()):
        for entry in entries:
            agents_str = ", ".join(entry.get("agents", []))
            created_at = entry.get("created_at", "")
            table.add_row(app_name, entry["project_path"], agents_str, created_at)

    console.print(table)


@link_app.command("status")
def link_status():
    """링크 상태를 확인합니다 (깨진 링크 탐지)."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    linker = Linker(registry.base_path)
    broken = linker.get_broken_links()

    if not broken:
        print_success("모든 링크가 정상입니다.")
        return

    print_warning(f"깨진 링크 {len(broken)}개 발견:")
    table = make_table("깨진 링크", ["App", "Project", "Agent", "Link Path"])
    for item in broken:
        table.add_row(item["app"], item["project"], item["agent"], item["link_path"])
    console.print(table)


def do_link(
    app_name: str,
    target: Path | None,
    agent: str | None,
) -> None:
    """link 핵심 로직"""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    project_path = (target or Path.cwd()).resolve()

    if not project_path.exists():
        print_error(f"프로젝트 경로가 존재하지 않습니다: {project_path}")
        raise typer.Exit(1)

    agents = _parse_agents(agent)

    linker = Linker(registry.base_path)

    try:
        linked = linker.link(app_name, project_path, agents=agents)
    except LinkerError as exc:
        print_error(str(exc))
        raise typer.Exit(1)
    except Exception as exc:
        print_error(f"링크 실패: {exc}")
        raise typer.Exit(1)

    if linked:
        print_success(f"앱 '{app_name}' → '{project_path}' 링크 완료 ({', '.join(linked)})")
    else:
        print_info(f"앱 '{app_name}': 링크할 에이전트가 없습니다.")


def do_unlink(
    app_name: str,
    target: Path | None,
    agent: str | None,
) -> None:
    """unlink 핵심 로직"""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    project_path = (target or Path.cwd()).resolve()

    agents = _parse_agents(agent)

    linker = Linker(registry.base_path)

    try:
        unlinked = linker.unlink(app_name, project_path, agents=agents)
    except Exception as exc:
        print_error(f"링크 해제 실패: {exc}")
        raise typer.Exit(1)

    if unlinked:
        print_success(f"앱 '{app_name}' 링크 해제 완료 ({', '.join(unlinked)})")
    else:
        print_info(f"앱 '{app_name}': 해제할 링크가 없습니다.")
