"""ConfigMerger 단위 테스트"""

import json

import pytest

from confhub.core.merger import (
    ConfigMerger,
    deep_merge,
    get_merge_strategy,
    merge_json_files,
    merge_text_files,
)

# ── deep_merge 테스트 ──────────────────────────────────────────────────────────


def test_deep_merge_simple():
    """스칼라 오버라이드"""
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested():
    """중첩 dict 재귀 병합"""
    base = {"permissions": {"allow": [], "deny": []}}
    override = {"permissions": {"allow": ["npm run *"]}}
    result = deep_merge(base, override)
    assert result == {"permissions": {"allow": ["npm run *"], "deny": []}}


def test_deep_merge_list_replace():
    """리스트는 override로 완전 대체"""
    base = {"items": [1, 2, 3]}
    override = {"items": [4, 5]}
    result = deep_merge(base, override)
    assert result["items"] == [4, 5]


def test_deep_merge_does_not_mutate():
    """원본 dict 불변 보장"""
    base = {"a": {"b": 1}}
    override = {"a": {"c": 2}}
    result = deep_merge(base, override)
    assert base == {"a": {"b": 1}}  # 원본 변경 없음
    assert result == {"a": {"b": 1, "c": 2}}


# ── merge_text_files 테스트 ───────────────────────────────────────────────────


def test_merge_text_append():
    """append: 루트 + 구분선 + 앱"""
    result = merge_text_files("root content", "app content", "append", "my-app")
    assert result.startswith("root content")
    assert "app content" in result
    assert "---" in result


def test_merge_text_prepend():
    """prepend: 앱 + 구분선 + 루트"""
    result = merge_text_files("root content", "app content", "prepend", "my-app")
    assert result.startswith("app content")
    assert "root content" in result


def test_merge_text_replace():
    """replace: 앱 내용만"""
    result = merge_text_files("root content", "app content", "replace", "my-app")
    assert result == "app content"
    assert "root" not in result


def test_merge_text_no_root():
    """루트 없을 때 앱 내용만"""
    result = merge_text_files(None, "app content", "append", "my-app")
    assert result == "app content"


def test_merge_text_no_app():
    """앱 없을 때 루트 내용만"""
    result = merge_text_files("root content", None, "append", "my-app")
    assert result == "root content"


# ── merge_json_files 테스트 ───────────────────────────────────────────────────


def test_merge_json_deep_merge():
    """JSON deep-merge"""
    root = '{"model": "sonnet", "permissions": {"allow": [], "deny": []}}'
    app = '{"model": "opus", "permissions": {"allow": ["npm run *"]}}'
    result = merge_json_files(root, app, "deep-merge")
    data = json.loads(result)
    assert data["model"] == "opus"
    assert data["permissions"]["allow"] == ["npm run *"]
    assert data["permissions"]["deny"] == []


def test_merge_json_replace():
    """JSON replace"""
    root = '{"model": "sonnet"}'
    app = '{"model": "opus"}'
    result = merge_json_files(root, app, "replace")
    data = json.loads(result)
    assert data == {"model": "opus"}


# ── get_merge_strategy 테스트 ─────────────────────────────────────────────────


def test_get_merge_strategy_md_default():
    """md 파일 기본 전략: append"""
    assert get_merge_strategy("CLAUDE.md", {}) == "append"


def test_get_merge_strategy_json_default():
    """json 파일 기본 전략: deep-merge"""
    assert get_merge_strategy("settings.json", {}) == "deep-merge"


def test_get_merge_strategy_explicit():
    """명시적 설정 우선"""
    config = {"CLAUDE.md": "replace"}
    assert get_merge_strategy("CLAUDE.md", config) == "replace"


# ── ConfigMerger 통합 테스트 ──────────────────────────────────────────────────


@pytest.fixture
def registry_with_data(tmp_path):
    """테스트용 Registry 데이터 구성"""
    base = tmp_path / "confhub"

    # root/agents/claude/.claude/
    root_claude = base / "root" / "agents" / "claude" / ".claude"
    root_claude.mkdir(parents=True)
    (root_claude / "CLAUDE.md").write_text("# Root Rules\n\n- rule 1", encoding="utf-8")
    (root_claude / "settings.json").write_text(
        '{"model": "sonnet", "permissions": {"allow": [], "deny": []}}', encoding="utf-8"
    )
    (base / "root" / "agents" / "claude" / "agent.config.yaml").write_text(
        "agent: claude\nmerge:\n  CLAUDE.md: append\n  settings.json: deep-merge\n",
        encoding="utf-8",
    )

    # apps/web-frontend/agents/claude/.claude/
    app_claude = base / "apps" / "web-frontend" / "agents" / "claude" / ".claude"
    app_claude.mkdir(parents=True)
    (app_claude / "CLAUDE.md").write_text("# App Rules\n\n- app rule 1", encoding="utf-8")
    (app_claude / "settings.json").write_text(
        '{"model": "opus", "permissions": {"allow": ["npm run *"]}}', encoding="utf-8"
    )

    return base


def test_resolver_resolve_agent(registry_with_data):
    """단일 에이전트 병합"""
    merger = ConfigMerger(registry_with_data)
    results = merger.resolve_agent("web-frontend", "claude")

    assert "CLAUDE.md" in results
    assert "settings.json" in results

    # CLAUDE.md: append 전략
    assert "Root Rules" in results["CLAUDE.md"]
    assert "App Rules" in results["CLAUDE.md"]

    # settings.json: deep-merge
    data = json.loads(results["settings.json"])
    assert data["model"] == "opus"
    assert data["permissions"]["deny"] == []


def test_resolver_dry_run(registry_with_data):
    """dry-run: 파일 미생성"""
    merger = ConfigMerger(registry_with_data)
    results = merger.resolve_agent("web-frontend", "claude", dry_run=True)

    # 결과는 반환되지만 파일 미생성
    assert "CLAUDE.md" in results
    resolved_dir = registry_with_data / "resolved" / "web-frontend" / "claude"
    assert not resolved_dir.exists()


def test_resolver_creates_files(registry_with_data):
    """파일 생성 확인"""
    merger = ConfigMerger(registry_with_data)
    merger.resolve_agent("web-frontend", "claude")

    resolved_claude = registry_with_data / "resolved" / "web-frontend" / "claude" / ".claude"
    assert resolved_claude.exists()
    assert (resolved_claude / "CLAUDE.md").exists()
    assert (resolved_claude / "settings.json").exists()


def test_resolver_header_in_md(registry_with_data):
    """MD 파일에 자동 생성 헤더 포함"""
    merger = ConfigMerger(registry_with_data)
    results = merger.resolve_agent("web-frontend", "claude")
    assert "AUTO-GENERATED" in results["CLAUDE.md"]


def test_resolver_replace_strategy(registry_with_data):
    """replace 전략: 앱 내용만"""
    # agent.config.yaml에 replace 전략 설정
    config_file = (
        registry_with_data / "apps" / "web-frontend" / "agents" / "claude" / "agent.config.yaml"
    )
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("agent: claude\nmerge:\n  CLAUDE.md: replace\n", encoding="utf-8")

    merger = ConfigMerger(registry_with_data)
    results = merger.resolve_agent("web-frontend", "claude")

    assert "Root Rules" not in results["CLAUDE.md"]
    assert "App Rules" in results["CLAUDE.md"]
