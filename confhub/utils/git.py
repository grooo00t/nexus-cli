"""GitPython 래퍼 - Registry Git 조작"""

from pathlib import Path


class GitError(Exception):
    """Git 조작 오류"""

    pass


class GitRepo:
    """Registry Git 레포 관리"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._repo = None

    def _get_repo(self):
        """Lazy-load git.Repo"""
        if self._repo is None:
            try:
                import git

                self._repo = git.Repo(self.repo_path)
            except Exception as exc:
                raise GitError(f"Git 레포를 열 수 없습니다: {self.repo_path}\n{exc}")
        return self._repo

    def is_git_repo(self) -> bool:
        """Git 레포 여부 확인"""
        try:
            self._get_repo()
            return True
        except GitError:
            return False

    def init(self) -> None:
        """Git 레포 초기화"""
        import git

        git.Repo.init(self.repo_path)
        self._repo = None  # 캐시 초기화

    def get_remote_url(self) -> str | None:
        """origin remote URL"""
        try:
            repo = self._get_repo()
            if "origin" in repo.remotes:
                return repo.remotes["origin"].url
            return None
        except GitError:
            return None

    def set_remote(self, url: str, name: str = "origin") -> None:
        """remote 설정"""
        repo = self._get_repo()
        if name in repo.remotes:
            repo.remotes[name].set_url(url)
        else:
            repo.create_remote(name, url)

    def commit_all(self, message: str) -> str:
        """변경 사항 전체 커밋. SHA 반환."""
        repo = self._get_repo()
        # untracked + modified 모두 스테이징
        repo.git.add(A=True)

        # HEAD가 없는 경우(초기 커밋) 처리
        try:
            staged = repo.index.diff("HEAD")
        except Exception:
            staged = None

        has_changes = (staged is None) or bool(staged) or bool(repo.untracked_files)

        if not has_changes:
            return ""  # 변경 없음

        commit = repo.index.commit(message)
        return commit.hexsha

    def push(self, remote: str = "origin", branch: str | None = None) -> None:
        """push"""
        repo = self._get_repo()
        if not branch:
            branch = repo.active_branch.name
        try:
            repo.remotes[remote].push(f"{branch}:{branch}")
        except Exception as exc:
            raise GitError(f"push 실패: {exc}")

    def pull(self, remote: str = "origin", branch: str | None = None) -> None:
        """pull"""
        repo = self._get_repo()
        if not branch:
            branch = repo.active_branch.name
        try:
            repo.remotes[remote].pull(branch)
        except Exception as exc:
            raise GitError(f"pull 실패: {exc}")

    def clone(self, url: str, target: Path) -> None:
        """URL에서 클론"""
        import git

        try:
            git.Repo.clone_from(url, target)
        except Exception as exc:
            raise GitError(f"clone 실패: {exc}")

    def get_status(self) -> dict:
        """현재 repo 상태"""
        try:
            repo = self._get_repo()
            return {
                "branch": repo.active_branch.name,
                "remote_url": self.get_remote_url(),
                "is_dirty": repo.is_dirty(untracked_files=True),
                "untracked": len(repo.untracked_files),
                "modified": len(repo.index.diff(None)),
                "ahead": 0,  # 계산 복잡도로 기본값
            }
        except GitError:
            return {"error": "Git 레포 아님"}
