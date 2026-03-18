"""Linker 단위 테스트"""

import shutil

import pytest

from confhub.core.linker import Linker, LinkerError


@pytest.fixture
def registry_with_resolved(tmp_path):
    """resolved 폴더가 있는 Registry"""
    base = tmp_path / "confhub"

    # resolved/web-frontend/claude/.claude/
    resolved_claude = base / "resolved" / "web-frontend" / "claude" / ".claude"
    resolved_claude.mkdir(parents=True)
    (resolved_claude / "CLAUDE.md").write_text("# Resolved", encoding="utf-8")

    # apps/web-frontend/agents/claude/
    app_agents = base / "apps" / "web-frontend" / "agents" / "claude"
    app_agents.mkdir(parents=True)

    # links/links.json
    links_dir = base / "links"
    links_dir.mkdir(parents=True)
    (links_dir / "links.json").write_text("{}", encoding="utf-8")

    return base


def test_link_creates_symlink(registry_with_resolved, tmp_path):
    """심볼릭 링크 생성"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linked = linker.link("web-frontend", project, agents=["claude"])

    assert "claude" in linked
    link_path = project / ".claude"
    assert link_path.is_symlink()
    assert link_path.exists()


def test_link_target_correct(registry_with_resolved, tmp_path):
    """심볼릭 링크 대상이 resolved 경로"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])

    link_path = project / ".claude"
    expected = registry_with_resolved / "resolved" / "web-frontend" / "claude" / ".claude"
    assert link_path.resolve() == expected.resolve()


def test_link_registers_in_links_json(registry_with_resolved, tmp_path):
    """links.json에 링크 등록"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])

    links = linker.list_links()
    assert "web-frontend" in links
    entries = links["web-frontend"]
    assert any(e["project_path"] == str(project) for e in entries)


def test_link_backs_up_existing(registry_with_resolved, tmp_path):
    """기존 실제 파일/폴더 백업"""
    project = tmp_path / "my-project"
    project.mkdir()

    # 기존 .claude 폴더 생성
    existing = project / ".claude"
    existing.mkdir()
    (existing / "old-file.md").write_text("old content")

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])

    # 백업 존재 확인
    backup = project / ".confhub-backup" / ".claude"
    assert backup.exists()


def test_unlink_removes_symlink(registry_with_resolved, tmp_path):
    """심볼릭 링크 해제"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])
    linker.unlink("web-frontend", project, agents=["claude"])

    link_path = project / ".claude"
    assert not link_path.exists()
    assert not link_path.is_symlink()


def test_link_replaces_existing_symlink(registry_with_resolved, tmp_path):
    """기존 심볼릭 링크 교체"""
    project = tmp_path / "my-project"
    project.mkdir()

    # 기존 심볼릭 링크 생성
    old_target = tmp_path / "old_target"
    old_target.mkdir()
    link_path = project / ".claude"
    link_path.symlink_to(old_target)

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])

    # 새 링크로 교체됨
    assert link_path.is_symlink()
    expected = registry_with_resolved / "resolved" / "web-frontend" / "claude" / ".claude"
    assert link_path.resolve() == expected.resolve()


def test_get_broken_links(registry_with_resolved, tmp_path):
    """깨진 링크 탐지"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])

    # resolved 폴더 삭제하여 링크 깨뜨리기
    shutil.rmtree(registry_with_resolved / "resolved")

    broken = linker.get_broken_links()
    assert len(broken) > 0
    assert broken[0]["agent"] == "claude"


def test_link_invalid_agent(registry_with_resolved, tmp_path):
    """지원하지 않는 에이전트 오류"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    with pytest.raises(LinkerError, match="지원하지 않는 에이전트"):
        linker.link("web-frontend", project, agents=["unknown-agent"])


def test_link_no_resolved_no_auto(registry_with_resolved, tmp_path):
    """resolved 없고 auto_resolve=False이면 오류"""
    project = tmp_path / "my-project"
    project.mkdir()

    # resolved 폴더 삭제
    shutil.rmtree(registry_with_resolved / "resolved")

    linker = Linker(registry_with_resolved)
    with pytest.raises(LinkerError, match="resolved 경로가 없습니다"):
        linker.link("web-frontend", project, agents=["claude"], auto_resolve=False)


def test_unlink_updates_links_json(registry_with_resolved, tmp_path):
    """unlink 후 links.json에서 제거"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])
    linker.unlink("web-frontend", project, agents=["claude"])

    links = linker.list_links()
    # 항목이 없거나 해당 project_path가 없어야 함
    if "web-frontend" in links:
        entries = links["web-frontend"]
        assert not any(e["project_path"] == str(project) for e in entries)


def test_list_links_empty(registry_with_resolved):
    """links.json이 비어 있을 때"""
    linker = Linker(registry_with_resolved)
    links = linker.list_links()
    assert links == {}


def test_link_records_created_at(registry_with_resolved, tmp_path):
    """created_at 필드가 기록됨"""
    project = tmp_path / "my-project"
    project.mkdir()

    linker = Linker(registry_with_resolved)
    linker.link("web-frontend", project, agents=["claude"])

    links = linker.list_links()
    entry = links["web-frontend"][0]
    assert "created_at" in entry
    assert entry["created_at"].endswith("Z")
