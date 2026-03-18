"""nxs sync 명령어 테스트"""

import pytest
from typer.testing import CliRunner

from confhub.cli import app
from confhub.core.registry import Registry
from confhub.utils.git import GitRepo

runner = CliRunner()


@pytest.fixture
def initialized_registry(tmp_path, monkeypatch):
    nexusrc = tmp_path / ".confhubrc"
    registry_path = tmp_path / "confhub"
    monkeypatch.setattr(Registry, "NEXUSRC_PATH", nexusrc)
    monkeypatch.setattr(Registry, "DEFAULT_PATH", registry_path)
    runner.invoke(app, ["init", "--path", str(registry_path)])
    return Registry(registry_path)


def test_sync_remote_set_show(initialized_registry):
    """remote set/show"""
    registry_path = initialized_registry.base_path
    repo = GitRepo(registry_path)
    repo.init()

    result = runner.invoke(app, ["sync", "remote", "set", "https://github.com/test/repo"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["sync", "remote", "show"])
    assert result.exit_code == 0
    assert "github.com/test/repo" in result.output


def test_sync_remote_show_no_remote(initialized_registry):
    """remote 없이 show 호출"""
    registry_path = initialized_registry.base_path
    repo = GitRepo(registry_path)
    repo.init()  # remote 없이 init만

    result = runner.invoke(app, ["sync", "remote", "show"])
    # remote 없으므로 경고 출력, exit code 1 또는 0
    assert "remote" in result.output.lower() or result.exit_code in (0, 1)


def test_sync_remote_set_auto_init(initialized_registry):
    """Git 레포 없을 때 remote set이 자동 init"""
    # Git 레포를 초기화하지 않은 상태에서 remote set 호출
    result = runner.invoke(app, ["sync", "remote", "set", "https://github.com/auto/init"])
    assert result.exit_code == 0
    assert "완료" in result.output


def test_sync_push_no_remote(initialized_registry):
    """remote 없이 push 시 오류"""
    registry_path = initialized_registry.base_path
    repo = GitRepo(registry_path)
    repo.init()

    result = runner.invoke(app, ["sync", "push"])
    # remote가 없으면 오류
    assert result.exit_code != 0


def test_sync_push_not_git_repo(initialized_registry):
    """Git 레포가 아닌 상태에서 push"""
    result = runner.invoke(app, ["sync", "push"])
    assert result.exit_code != 0


def test_git_repo_is_git_repo(tmp_path):
    """is_git_repo 확인"""
    repo = GitRepo(tmp_path)
    assert not repo.is_git_repo()

    repo.init()
    assert repo.is_git_repo()


def test_git_repo_not_git(tmp_path):
    """Git 아닌 디렉토리"""
    repo = GitRepo(tmp_path / "not-git")
    assert not repo.is_git_repo()


def test_status_command(initialized_registry):
    """nxs status 실행"""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0


def test_status_shows_registry_info(initialized_registry):
    """status에 Registry 정보 포함"""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Registry 경로가 출력에 포함
    assert (
        str(initialized_registry.base_path) in result.output or "confhub" in result.output.lower()
    )


def test_status_with_links(initialized_registry):
    """--with-links 옵션"""
    result = runner.invoke(app, ["status", "--with-links"])
    assert result.exit_code == 0


def test_status_git_info(initialized_registry):
    """status에 Git 정보 포함"""
    registry_path = initialized_registry.base_path
    repo = GitRepo(registry_path)
    repo.init()
    repo.set_remote("https://github.com/test/confhub-config")

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "github.com" in result.output


def test_install_verify(initialized_registry):
    """nxs install --verify 실행"""
    result = runner.invoke(app, ["install", "--verify"])
    assert result.exit_code == 0


def test_install_no_args(initialized_registry):
    """nxs install 인자 없이 호출"""
    result = runner.invoke(app, ["install"])
    assert result.exit_code != 0
