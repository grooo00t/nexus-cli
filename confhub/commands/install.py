"""nxs install 명령어 - Git URL에서 Registry 설치"""

from confhub.core.registry import Registry, RegistryNotFoundError
from confhub.utils.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from confhub.utils.git import GitError, GitRepo


def do_install(
    from_repo: str | None = None,
    verify: bool = False,
    apps: str | None = None,
) -> None:
    """install 핵심 로직.

    Args:
        from_repo: Git 레포 URL.
        verify: 설치 상태 확인 모드.
        apps: 쉼표 구분 앱 이름 목록 (특정 앱만 resolve).
    """
    import typer

    # ── verify 모드 ───────────────────────────────────────────────────────────
    if verify:
        try:
            registry = Registry.get_default()
            registry.require_initialized()
        except RegistryNotFoundError as exc:
            print_error(str(exc))
            raise typer.Exit(1)

        console.print(f"[bold]Registry 경로:[/bold] {registry.base_path}")

        if registry.is_initialized():
            print_success("Registry 설치 상태: 정상")
        else:
            print_warning("Registry가 초기화되지 않았습니다.")

        app_list = registry.list_apps()
        if app_list:
            console.print(f"등록된 앱: {', '.join(sorted(app_list))}")
        else:
            console.print("등록된 앱 없음")
        return

    # ── --from-repo 없이 호출 ────────────────────────────────────────────────
    if not from_repo:
        print_error("설치할 Git URL을 지정하세요.\n사용법: nxs install --from-repo <git-url>")
        raise typer.Exit(1)

    # ── [1] 클론 대상 경로 결정 ───────────────────────────────────────────────
    target_path = Registry.DEFAULT_PATH

    if target_path.exists() and any(target_path.iterdir()):
        print_warning(f"대상 경로가 비어 있지 않습니다: {target_path}")
        print_info("기존 디렉토리를 사용합니다.")
    else:
        target_path.mkdir(parents=True, exist_ok=True)

    # ── [2] Git 클론 ──────────────────────────────────────────────────────────
    print_info(f"[1/4] Git 레포 클론: {from_repo}")
    git_repo = GitRepo(target_path)

    if not git_repo.is_git_repo():
        temp_clone = target_path.parent / "_confhub_clone_tmp"
        try:
            temp_git = GitRepo(temp_clone)
            temp_git.clone(from_repo, temp_clone)
        except GitError as exc:
            print_error(str(exc))
            raise typer.Exit(1)

        # 클론된 내용을 target_path로 이동
        import shutil

        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.move(str(temp_clone), str(target_path))
    else:
        print_info("이미 Git 레포가 존재합니다. pull을 시도합니다.")
        try:
            git_repo.pull()
        except GitError as exc:
            print_error(str(exc))
            raise typer.Exit(1)

    # ── [3] confhub.config.yaml 확인 ────────────────────────────────────────────
    print_info("[2/4] confhub.config.yaml 확인...")
    registry = Registry(target_path)
    if not registry.is_initialized():
        print_error(
            f"클론된 레포에 confhub.config.yaml이 없습니다: {target_path}\n"
            "올바른 ConfHub Registry 레포인지 확인하세요."
        )
        raise typer.Exit(1)

    # ── [4] ~/.confhubrc 등록 ───────────────────────────────────────────────────
    print_info("[3/4] ~/.confhubrc에 경로 등록...")
    Registry.save_nexusrc(target_path)

    # ── [5] resolve 실행 ──────────────────────────────────────────────────────
    print_info("[4/4] 설정 resolve 중...")
    app_list = registry.list_apps()

    if apps:
        target_apps = [a.strip() for a in apps.split(",") if a.strip()]
    else:
        target_apps = app_list

    if target_apps:
        from confhub.core.merger import ConfigMerger

        merger = ConfigMerger(registry.base_path)
        for app_name in target_apps:
            try:
                merger.resolve_app(app_name)
                print_info(f"  resolved: {app_name}")
            except Exception as exc:
                print_warning(f"  resolve 실패 ({app_name}): {exc}")
    else:
        print_info("resolve할 앱이 없습니다.")

    print_success(f"Registry 설치 완료: {target_path}")
    console.print(f"  원본: {from_repo}")
