"""nxs app 명령어 - 앱 관리"""
import shutil
from pathlib import Path
from typing import Optional

import typer
import yaml

from nexus.core.registry import Registry, RegistryNotFoundError
from nexus.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
    make_table,
)

app = typer.Typer(help="앱 관리")


# ── 템플릿 상수 ────────────────────────────────────────────────────────────────

def _build_app_config(name: str, description: str = "") -> dict:
    """app.config.yaml 템플릿 생성"""
    return {
        "name": name,
        "version": "1.0.0",
        "description": description,
        "inherits": "root",
        "agents": [],
        "metadata": {
            "team": "",
            "tech_stack": [],
        },
        "inheritance": {
            "strategy": "deep-merge",
        },
    }


# ── 유틸리티 ───────────────────────────────────────────────────────────────────

def _get_registry() -> Registry:
    """기본 Registry를 반환하고, 초기화 여부를 확인한다."""
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


# ── 명령어 ─────────────────────────────────────────────────────────────────────

@app.command("add")
def app_add(
    app_name: str = typer.Argument(..., help="앱 이름"),
    description: str = typer.Option("", "--description", "-d", help="앱 설명"),
):
    """새 앱을 추가합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if registry.app_exists(app_name):
        print_warning(f"앱 '{app_name}'이(가) 이미 존재합니다. (already exists)")
        raise typer.Exit(1)

    try:
        app_path = registry.get_app_path(app_name)

        # 디렉토리 생성
        app_path.mkdir(parents=True, exist_ok=True)
        (app_path / "agents").mkdir(exist_ok=True)

        # app.config.yaml 생성
        config = _build_app_config(app_name, description)
        with open(app_path / "app.config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print_success(f"앱 '{app_name}' 추가 완료")
    except OSError as exc:
        print_error(f"파일 시스템 오류: {exc}")
        raise typer.Exit(1)


@app.command("list")
def app_list():
    """등록된 앱 목록을 표시합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    apps = registry.list_apps()

    if not apps:
        print_info("등록된 앱이 없습니다. 'nxs app add <앱이름>'으로 추가하세요.")
        return

    table = make_table("앱 목록", ["Name", "Description", "Agents", "Inherited From"])

    for app_name in sorted(apps):
        try:
            config = registry.load_app_config(app_name)
        except FileNotFoundError:
            continue

        name = config.get("name", app_name)
        desc = config.get("description", "")
        agents = config.get("agents", [])
        agents_str = ", ".join(agents) if agents else "-"
        inherits = config.get("inherits", "root")

        table.add_row(name, desc, agents_str, inherits)

    console.print(table)


@app.command("show")
def app_show(
    app_name: str = typer.Argument(..., help="앱 이름"),
):
    """앱의 상세 정보를 표시합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if not registry.app_exists(app_name):
        print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다. (not found)")
        raise typer.Exit(1)

    try:
        config = registry.load_app_config(app_name)
    except FileNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    lines = []
    lines.append(f"[bold]이름:[/bold]        {config.get('name', app_name)}")
    lines.append(f"[bold]버전:[/bold]        {config.get('version', '')}")
    lines.append(f"[bold]설명:[/bold]        {config.get('description', '')}")
    lines.append(f"[bold]상속:[/bold]        {config.get('inherits', 'root')}")

    agents = config.get("agents", [])
    agents_str = ", ".join(agents) if agents else "(없음)"
    lines.append(f"[bold]에이전트:[/bold]    {agents_str}")

    metadata = config.get("metadata", {})
    team = metadata.get("team", "")
    tech_stack = metadata.get("tech_stack", [])
    lines.append(f"[bold]팀:[/bold]          {team or '(없음)'}")
    lines.append(f"[bold]기술 스택:[/bold]   {', '.join(tech_stack) if tech_stack else '(없음)'}")

    inheritance = config.get("inheritance", {})
    strategy = inheritance.get("strategy", "deep-merge")
    lines.append(f"[bold]병합 전략:[/bold]   {strategy}")

    from rich.panel import Panel
    console.print(Panel("\n".join(lines), title=f"앱: {app_name}", style="blue"))


@app.command("remove")
def app_remove(
    app_name: str = typer.Argument(..., help="앱 이름"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 삭제"),
):
    """앱을 삭제합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if not registry.app_exists(app_name):
        print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다. (not found)")
        raise typer.Exit(1)

    if not force:
        confirmed = typer.confirm(f"앱 '{app_name}'을(를) 삭제하시겠습니까?")
        if not confirmed:
            print_info("삭제가 취소되었습니다.")
            raise typer.Exit(0)

    try:
        app_path = registry.get_app_path(app_name)
        shutil.rmtree(app_path)
        print_success(f"앱 '{app_name}' 삭제 완료")
    except OSError as exc:
        print_error(f"파일 시스템 오류: {exc}")
        raise typer.Exit(1)


@app.command("rename")
def app_rename(
    old_name: str = typer.Argument(..., help="현재 앱 이름"),
    new_name: str = typer.Argument(..., help="새 앱 이름"),
):
    """앱 이름을 변경합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    if not registry.app_exists(old_name):
        print_error(f"앱 '{old_name}'을(를) 찾을 수 없습니다. (not found)")
        raise typer.Exit(1)

    if registry.app_exists(new_name):
        print_warning(f"앱 '{new_name}'이(가) 이미 존재합니다. (already exists)")
        raise typer.Exit(1)

    try:
        old_path = registry.get_app_path(old_name)
        new_path = registry.get_app_path(new_name)

        # 디렉토리 이름 변경
        old_path.rename(new_path)

        # app.config.yaml 내 name 필드 업데이트
        config = registry.load_app_config(new_name)
        config["name"] = new_name
        registry.save_app_config(new_name, config)

        print_success(f"앱 이름 변경 완료: '{old_name}' → '{new_name}'")
    except OSError as exc:
        print_error(f"파일 시스템 오류: {exc}")
        raise typer.Exit(1)
