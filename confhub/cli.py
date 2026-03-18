"""ConfHub CLI - 진입점 모듈"""

from pathlib import Path

import typer

from confhub import __version__
from confhub.commands import agent as agent_cmd
from confhub.commands import app as app_cmd
from confhub.commands.link import link_app
from confhub.commands.submodule import submodule_app
from confhub.commands.sync import sync_app

app = typer.Typer(
    name="confhub",
    help="ConfHub CLI - AI 에이전트 설정 관리",
    add_completion=False,
)

app.add_typer(app_cmd.app, name="app")
app.add_typer(agent_cmd.app, name="agent")
app.add_typer(link_app, name="link")
app.add_typer(submodule_app, name="submodule")
app.add_typer(sync_app, name="sync")


def version_callback(value: bool):
    """버전 정보 출력 콜백"""
    if value:
        typer.echo(f"confhub-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="현재 버전을 출력합니다.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """ConfHub CLI - AI 에이전트 설정 중앙 관리 프레임워크"""


@app.command("init")
def init_command(
    path: Path | None = typer.Option(None, "--path", "-p", help="Registry 경로 (기본: 현재 디렉토리)"),
    from_repo: str | None = typer.Option(None, "--from-repo", help="Git 레포 URL에서 초기화"),
):
    """ConfHub Registry를 초기화합니다."""
    from confhub.commands.init import do_init

    do_init(path, from_repo)


@app.command("resolve")
def resolve_command(
    app_name: str | None = typer.Argument(None, help="앱 이름 (생략시 --all 필요)"),
    all_apps: bool = typer.Option(False, "--all", "-a", help="모든 앱 빌드"),
    dry_run: bool = typer.Option(False, "--dry-run", help="결과 미리보기 (파일 미생성)"),
):
    """설정을 병합하여 resolved 디렉토리에 저장합니다."""
    from confhub.commands.resolve import do_resolve

    do_resolve(app_name, all_apps, dry_run)


@app.command("unlink")
def unlink_command(
    app_name: str = typer.Argument(..., help="앱 이름"),
    target: Path | None = typer.Option(
        None, "--target", "-t", help="링크 해제할 프로젝트 경로 (기본: 현재 디렉토리)"
    ),
    agent: str | None = typer.Option(
        None, "--agent", help="특정 에이전트만 해제 (쉼표 구분: claude,gemini)"
    ),
):
    """프로젝트의 심볼릭 링크를 해제합니다."""
    from confhub.commands.link import do_unlink

    do_unlink(app_name, target, agent)


@app.command("status")
def status_command(
    app_name: str | None = typer.Option(None, "--app", help="특정 앱 이름"),
    with_links: bool = typer.Option(False, "--with-links", help="링크 상태 포함"),
):
    """Registry 상태를 표시합니다."""
    from confhub.commands.status import do_status

    do_status(app_name, with_links)


@app.command("install")
def install_command(
    from_repo: str | None = typer.Option(None, "--from-repo", help="Git 레포 URL에서 설치"),
    verify: bool = typer.Option(False, "--verify", help="설치 상태 확인"),
    apps: str | None = typer.Option(
        None, "--apps", help="특정 앱만 설치 (쉼표 구분: web-frontend,api-server)"
    ),
):
    """Git 레포에서 Registry를 설치합니다."""
    from confhub.commands.install import do_install

    do_install(from_repo, verify, apps)


if __name__ == "__main__":
    app()
