"""Nexus CLI - 진입점 모듈"""
from pathlib import Path
from typing import Optional
import typer
from nexus import __version__

app = typer.Typer(
    name="nxs",
    help="Nexus CLI - AI 에이전트 설정 관리",
    add_completion=False,
)


def version_callback(value: bool):
    """버전 정보 출력 콜백"""
    if value:
        typer.echo(f"nexus-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="현재 버전을 출력합니다.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Nexus CLI - AI 에이전트 설정 중앙 관리 프레임워크"""


@app.command("init")
def init_command(
    path: Optional[Path] = typer.Option(
        None, "--path", "-p", help="Registry 경로"
    ),
    from_repo: Optional[str] = typer.Option(
        None, "--from-repo", help="Git 레포 URL에서 초기화"
    ),
):
    """Nexus Registry를 초기화합니다."""
    from nexus.commands.init import do_init
    do_init(path, from_repo)


if __name__ == "__main__":
    app()
