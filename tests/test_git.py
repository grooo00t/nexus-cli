"""GitRepo 단위 테스트"""

from confhub.utils.git import GitRepo


def test_init_and_is_git_repo(tmp_path):
    repo = GitRepo(tmp_path)
    assert not repo.is_git_repo()
    repo.init()
    assert repo.is_git_repo()


def test_get_remote_url_none(tmp_path):
    repo = GitRepo(tmp_path)
    repo.init()
    assert repo.get_remote_url() is None


def test_set_remote(tmp_path):
    repo = GitRepo(tmp_path)
    repo.init()
    repo.set_remote("https://github.com/test/repo")
    assert repo.get_remote_url() == "https://github.com/test/repo"


def test_get_status(tmp_path):
    repo = GitRepo(tmp_path)
    repo.init()
    status = repo.get_status()
    assert "branch" in status
    assert "is_dirty" in status


def test_commit_all(tmp_path):
    repo = GitRepo(tmp_path)
    repo.init()

    # 파일 생성 후 커밋
    (tmp_path / "test.txt").write_text("hello", encoding="utf-8")
    sha = repo.commit_all("test commit")
    assert sha  # 빈 문자열이 아님


def test_commit_nothing_to_commit(tmp_path):
    repo = GitRepo(tmp_path)
    repo.init()
    # 변경 없음
    (tmp_path / "test.txt").write_text("hello", encoding="utf-8")
    repo.commit_all("first")
    sha = repo.commit_all("second - empty")
    # 변경 없으므로 빈 문자열
    assert sha == ""


def test_is_git_repo_nonexistent_path(tmp_path):
    """존재하지 않는 경로"""
    repo = GitRepo(tmp_path / "not-git")
    assert not repo.is_git_repo()


def test_get_status_not_git(tmp_path):
    """Git 아닌 디렉토리의 status"""
    repo = GitRepo(tmp_path / "no-git")
    status = repo.get_status()
    assert "error" in status


def test_set_remote_updates_existing(tmp_path):
    """이미 있는 remote URL 업데이트"""
    repo = GitRepo(tmp_path)
    repo.init()
    repo.set_remote("https://github.com/first/repo")
    repo.set_remote("https://github.com/second/repo")
    assert repo.get_remote_url() == "https://github.com/second/repo"
