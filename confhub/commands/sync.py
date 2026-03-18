"""nxs sync 명령어 - Registry Git 동기화"""

import typer

from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from confhub.utils.git import GitError, GitRepo

sync_app = typer.Typer(help="Git 동기화")
remote_app = typer.Typer(help="remote 설정")
sync_app.add_typer(remote_app, name="remote")


def _get_registry() -> Registry:
    """기본 Registry를 반환하고, 초기화 여부를 확인한다."""
    registry = Registry.get_default()
    registry.require_initialized()
    return registry


@sync_app.command("push")
def sync_push(
    message: str = typer.Option(
        "chore: sync registry",
        "--message",
        "-m",
        help="커밋 메시지",
    ),
):
    """Registry를 원격 레포에 push합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    repo = GitRepo(registry.base_path)

    if not repo.is_git_repo():
        print_error(
            "Registry가 Git 레포가 아닙니다. 'nxs sync remote set <url>'로 remote를 설정하거나 "
            "'git init'으로 초기화하세요."
        )
        raise typer.Exit(1)

    remote_url = repo.get_remote_url()
    if not remote_url:
        print_error(
            "원격 레포가 설정되지 않았습니다. 'nxs sync remote set <git-url>'로 설정하세요."
        )
        raise typer.Exit(1)

    try:
        sha = repo.commit_all(message)
        if sha:
            print_info(f"커밋: {sha[:8]} - {message}")
        else:
            print_info("변경 사항이 없습니다. push만 진행합니다.")

        repo.push()
        print_success(f"Registry push 완료 → {remote_url}")
    except GitError as exc:
        print_error(str(exc))
        raise typer.Exit(1)


@sync_app.command("pull")
def sync_pull():
    """원격 레포에서 최신 설정을 pull합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    repo = GitRepo(registry.base_path)

    if not repo.is_git_repo():
        print_error(
            "Registry가 Git 레포가 아닙니다. 'nxs sync remote set <url>'로 remote를 설정하거나 "
            "'git init'으로 초기화하세요."
        )
        raise typer.Exit(1)

    remote_url = repo.get_remote_url()
    if not remote_url:
        print_error(
            "원격 레포가 설정되지 않았습니다. 'nxs sync remote set <git-url>'로 설정하세요."
        )
        raise typer.Exit(1)

    try:
        repo.pull()
        print_success(f"Registry pull 완료 ← {remote_url}")
    except GitError as exc:
        print_error(str(exc))
        raise typer.Exit(1)


@remote_app.command("set")
def remote_set(
    url: str = typer.Argument(..., help="Git 레포 URL"),
):
    """원격 레포 URL을 설정합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    repo = GitRepo(registry.base_path)

    # Git 레포가 아니면 초기화
    if not repo.is_git_repo():
        print_info("Git 레포를 초기화합니다...")
        try:
            repo.init()
        except Exception as exc:
            print_error(f"Git 초기화 실패: {exc}")
            raise typer.Exit(1)

    try:
        repo.set_remote(url)
        print_success(f"원격 레포 설정 완료: {url}")
    except Exception as exc:
        print_error(f"remote 설정 실패: {exc}")
        raise typer.Exit(1)


@remote_app.command("show")
def remote_show():
    """설정된 원격 레포 URL을 확인합니다."""
    try:
        registry = _get_registry()
    except RegistryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(1)

    repo = GitRepo(registry.base_path)

    if not repo.is_git_repo():
        print_warning("Registry가 Git 레포가 아닙니다.")
        raise typer.Exit(1)

    remote_url = repo.get_remote_url()
    if remote_url:
        console.print(f"origin: [bold]{remote_url}[/bold]")
    else:
        print_warning("원격 레포가 설정되지 않았습니다.")
