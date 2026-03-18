"""nxs status 명령어 - Registry 상태 확인"""

import typer

from confhub.core.linker import Linker
from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import console, print_error
from confhub.utils.git import GitRepo


def _get_registry() -> Registry:
    """기본 Registry를 반환하고, 초기화 여부를 확인한다."""
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


def _get_app_status_line(registry: Registry, app_name: str) -> tuple[str, str]:
    """앱 하나의 상태 아이콘과 상세 정보를 반환."""
    try:
        app_config = registry.load_app_config(app_name)
    except FileNotFoundError:
        return "❓", f"{app_name}  - config 없음"

    agents = app_config.get("agents", [])
    agents_str = ", ".join(agents) if agents else "-"

    # resolved 여부 확인
    is_resolved = True
    for agent in agents:
        resolved_dir = registry.resolved_path / app_name / agent
        if not resolved_dir.exists():
            is_resolved = False
            break

    if not agents:
        is_resolved = False

    icon = "✅" if is_resolved else "⚠️ "
    state = "resolved" if is_resolved else "not resolved"
    detail = f"{app_name}  ({agents_str})  - {state}"
    return icon, detail


def do_status(
    app_name: str | None = None,
    with_links: bool = False,
) -> None:
    """status 핵심 로직."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    # Git 정보
    repo = GitRepo(registry.base_path)
    git_info = "Git 없음"
    if repo.is_git_repo():
        git_status = repo.get_status()
        branch = git_status.get("branch", "?")
        remote_url = git_status.get("remote_url")
        if remote_url:
            # URL 단축 표시
            short_url = remote_url.replace("https://", "").replace("http://", "")
            git_info = f"{branch} (origin: {short_url})"
        else:
            git_info = f"{branch} (remote 없음)"

    # 앱 목록
    if app_name:
        apps = [app_name] if registry.app_exists(app_name) else []
        if not apps:
            print_error(f"앱 '{app_name}'을 찾을 수 없습니다.")
            raise typer.Exit(1)
    else:
        apps = registry.list_apps()

    # 링크 정보
    linker = Linker(registry.base_path)
    all_links = linker.list_links()
    total_links = sum(len(entries) for entries in all_links.values())
    broken_links = linker.get_broken_links()

    # ── 출력 구성 ────────────────────────────────────────────────────────────
    lines = []
    lines.append(f"  Registry: {registry.base_path}")
    lines.append(f"  Git: {git_info}")
    lines.append("")

    if apps:
        lines.append("  앱 목록:")
        for name in sorted(apps):
            icon, detail = _get_app_status_line(registry, name)
            lines.append(f"    {icon}  {detail}")
    else:
        lines.append("  앱 없음 (nxs app add <name>으로 등록)")

    lines.append("")
    broken_count = len(broken_links)
    broken_label = f"깨진 링크: {broken_count}개" if broken_count else "깨진 링크: 0개"
    lines.append(f"  링크: {total_links}개 ({broken_label})")

    # 링크 상세 출력
    if with_links and all_links:
        lines.append("")
        lines.append("  링크 상세:")
        for lapp, entries in sorted(all_links.items()):
            for entry in entries:
                proj = entry.get("project_path", "?")
                agents = ", ".join(entry.get("agents", []))
                lines.append(f"    {lapp} → {proj}  [{agents}]")

    content = "\n".join(lines)

    from rich.panel import Panel

    console.print(
        Panel(
            content,
            title="ConfHub Registry Status",
            border_style="blue",
        )
    )
