"""심볼릭 링크 관리"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from confhub.core.agents import SUPPORTED_AGENTS, get_agent
from confhub.core.merger import ConfigMerger


class LinkerError(Exception):
    """링크 관련 오류"""

    pass


class Linker:
    """심볼릭 링크 생성/해제 관리"""

    def __init__(self, registry_base: Path):
        self.registry_base = registry_base
        self._links_file = registry_base / "links" / "links.json"

    def _load_links(self) -> dict:
        if not self._links_file.exists():
            return {}
        with open(self._links_file, encoding="utf-8") as f:
            return json.load(f)

    def _save_links(self, links: dict) -> None:
        self._links_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._links_file, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)

    def _get_resolved_link_target(self, app_name: str, agent: str) -> Path:
        """에이전트별 resolved 경로 반환 (심볼릭 링크 대상)"""
        agent_cfg = get_agent(agent)
        resolved_base = self.registry_base / "resolved" / app_name / agent

        if agent_cfg.config_dir == ".":
            # 파일 링크: resolved/<app>/<agent>/<link_target>
            return resolved_base / agent_cfg.link_target
        else:
            # 디렉토리 링크: resolved/<app>/<agent>/<config_dir>
            return resolved_base / agent_cfg.config_dir

    def _get_project_link_path(self, project_path: Path, agent: str) -> Path:
        """프로젝트 내 링크 경로 반환"""
        agent_cfg = get_agent(agent)
        return project_path / agent_cfg.link_target

    def link(
        self,
        app_name: str,
        project_path: Path,
        agents: list[str] | None = None,
        auto_resolve: bool = True,
    ) -> list[str]:
        """앱 설정을 프로젝트에 링크.

        Returns:
            링크된 에이전트 목록
        """
        # 앱의 에이전트 목록
        if agents is None:
            agents = self._get_app_agents(app_name)

        # 유효성 검사
        for agent in agents:
            if agent not in SUPPORTED_AGENTS:
                raise LinkerError(f"지원하지 않는 에이전트: {agent}")

        linked = []

        for agent in agents:
            resolved_target = self._get_resolved_link_target(app_name, agent)

            # resolved가 없으면 자동 resolve
            if not resolved_target.exists() and auto_resolve:
                merger = ConfigMerger(self.registry_base)
                merger.resolve_agent(app_name, agent)

            if not resolved_target.exists():
                raise LinkerError(
                    f"resolved 경로가 없습니다: {resolved_target}\n"
                    f"'nxs resolve {app_name}'을 먼저 실행하세요."
                )

            link_path = self._get_project_link_path(project_path, agent)

            # 기존 파일/폴더 처리
            if link_path.exists() or link_path.is_symlink():
                if link_path.is_symlink():
                    # 이미 심볼릭 링크면 교체
                    link_path.unlink()
                else:
                    # 실제 파일/폴더면 백업
                    backup_dir = project_path / ".confhub-backup"
                    backup_dir.mkdir(exist_ok=True)
                    backup_path = backup_dir / link_path.name
                    shutil.move(str(link_path), str(backup_path))

            # 부모 디렉토리 생성
            link_path.parent.mkdir(parents=True, exist_ok=True)

            # 심볼릭 링크 생성
            link_path.symlink_to(resolved_target)
            linked.append(agent)

        # links.json 업데이트
        self._register_link(app_name, project_path, linked)

        return linked

    def unlink(
        self,
        app_name: str,
        project_path: Path,
        agents: list[str] | None = None,
    ) -> list[str]:
        """링크 해제.

        Returns:
            해제된 에이전트 목록
        """
        if agents is None:
            agents = self._get_app_agents(app_name)

        unlinked = []

        for agent in agents:
            link_path = self._get_project_link_path(project_path, agent)

            if link_path.is_symlink():
                link_path.unlink()
                unlinked.append(agent)

        # links.json 업데이트
        self._unregister_link(app_name, project_path, unlinked)

        return unlinked

    def list_links(self) -> dict:
        """모든 링크 목록 반환"""
        return self._load_links()

    def get_broken_links(self) -> list[dict]:
        """깨진 심볼릭 링크 목록"""
        links = self._load_links()
        broken = []

        for app_name, entries in links.items():
            for entry in entries:
                project_path = Path(entry["project_path"])
                for agent in entry.get("agents", []):
                    link_path = self._get_project_link_path(project_path, agent)
                    if link_path.is_symlink() and not link_path.exists():
                        broken.append(
                            {
                                "app": app_name,
                                "project": str(project_path),
                                "agent": agent,
                                "link_path": str(link_path),
                            }
                        )

        return broken

    def _get_app_agents(self, app_name: str) -> list[str]:
        """앱의 에이전트 목록"""
        agents_dir = self.registry_base / "apps" / app_name / "agents"
        if not agents_dir.exists():
            return []
        return [d.name for d in agents_dir.iterdir() if d.is_dir()]

    def _register_link(self, app_name: str, project_path: Path, agents: list[str]) -> None:
        links = self._load_links()
        if app_name not in links:
            links[app_name] = []

        # 기존 항목 제거 (같은 project_path)
        links[app_name] = [e for e in links[app_name] if e["project_path"] != str(project_path)]

        links[app_name].append(
            {
                "project_path": str(project_path),
                "agents": agents,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

        self._save_links(links)

    def _unregister_link(self, app_name: str, project_path: Path, agents: list[str]) -> None:
        links = self._load_links()
        if app_name not in links:
            return

        # 해당 project_path 항목에서 해제된 에이전트만 제거
        updated_entries = []
        for entry in links[app_name]:
            if entry["project_path"] != str(project_path):
                updated_entries.append(entry)
            else:
                remaining = [a for a in entry.get("agents", []) if a not in agents]
                if remaining:
                    updated_entries.append({**entry, "agents": remaining})
                # remaining이 비면 항목 자체를 제거

        links[app_name] = updated_entries
        if not links[app_name]:
            del links[app_name]

        self._save_links(links)
