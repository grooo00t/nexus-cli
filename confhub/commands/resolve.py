"""nxs resolve 명령어 - 설정 병합 빌드"""

import json
from pathlib import Path

import typer

from confhub.core.merger import ConfigMerger
from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import console, print_error, print_info, print_success

# resolve 하위 서브커맨드가 없으므로 app 객체는 유지하되 실제 로직은 do_resolve로 분리
app = typer.Typer(help="설정 병합 빌드")


def _get_registry() -> Registry:
    """기본 Registry를 반환하고, 초기화 여부를 확인한다."""
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


def _print_dry_run_results(app_name: str, agent: str, results: dict[str, str]) -> None:
    """dry-run 결과를 출력한다."""
    console.print(f"\n[bold cyan][dry-run] {app_name} / {agent}[/bold cyan]")
    for filename, content in sorted(results.items()):
        suffix = Path(filename).suffix.lower()
        if suffix == ".json":
            try:
                parsed = json.loads(content)
                preview = json.dumps(parsed, indent=2, ensure_ascii=False)
                strategy = "deep-merge"
            except json.JSONDecodeError:
                preview = content
                strategy = "replace"
        else:
            preview = content
            strategy = "append"

        console.print(f"  [bold]{filename}[/bold] ({strategy}):")
        # 미리보기: 최대 20줄
        lines = preview.splitlines()
        max_lines = 20
        for line in lines[:max_lines]:
            console.print(f"    {line}")
        if len(lines) > max_lines:
            console.print(f"    [dim]... ({len(lines) - max_lines}줄 더)[/dim]")


def do_resolve(
    app_name: str | None,
    all_apps: bool,
    dry_run: bool,
) -> None:
    """resolve 핵심 로직 (cli.py에서 직접 호출)"""
    # 인수 검증
    if not app_name and not all_apps:
        print_error("앱 이름을 지정하거나 --all 플래그를 사용하세요.")
        raise typer.Exit(1)

    if app_name and all_apps:
        print_error("앱 이름과 --all 플래그를 동시에 사용할 수 없습니다.")
        raise typer.Exit(1)

    # Registry 로드
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    merger = ConfigMerger(registry.base_path)

    if all_apps:
        # 모든 앱 빌드
        apps = registry.list_apps()
        if not apps:
            print_info("등록된 앱이 없습니다.")
            raise typer.Exit(0)

        total_agents = 0
        for name in sorted(apps):
            try:
                results = merger.resolve_app(name, dry_run=dry_run)
                total_agents += len(results)
                if dry_run:
                    for agent, agent_results in results.items():
                        _print_dry_run_results(name, agent, agent_results)
                else:
                    if results:
                        print_success(f"앱 '{name}' 병합 완료 ({len(results)}개 에이전트)")
                    else:
                        print_info(f"앱 '{name}': 에이전트 없음")
            except Exception as exc:
                print_error(f"앱 '{name}' 병합 실패: {exc}")
                raise typer.Exit(1)

        if not dry_run:
            print_success(f"전체 병합 완료: {len(apps)}개 앱, {total_agents}개 에이전트")

    else:
        # 단일 앱 빌드
        assert app_name is not None
        if not registry.app_exists(app_name):
            print_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다. (not found)")
            raise typer.Exit(1)

        try:
            results = merger.resolve_app(app_name, dry_run=dry_run)
        except Exception as exc:
            print_error(f"병합 실패: {exc}")
            raise typer.Exit(1)

        if dry_run:
            for agent, agent_results in results.items():
                _print_dry_run_results(app_name, agent, agent_results)
            if not results:
                print_info(f"앱 '{app_name}': 병합할 에이전트가 없습니다.")
        else:
            if results:
                print_success(f"앱 '{app_name}' 병합 완료 ({len(results)}개 에이전트)")
                resolved_base = registry.resolved_path / app_name
                print_info(f"결과 위치: {resolved_base}")
            else:
                print_info(f"앱 '{app_name}': 에이전트 없음")
