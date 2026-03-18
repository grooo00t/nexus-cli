"""nxs agent 명령어 테스트"""

import pytest
import yaml
from typer.testing import CliRunner

from confhub.cli import app
from confhub.core.agents import SUPPORTED_AGENTS, get_agent
from confhub.core.registry import Registry

runner = CliRunner()


@pytest.fixture
def initialized_registry(tmp_path, monkeypatch):
    """초기화된 임시 Registry"""
    nexusrc = tmp_path / ".confhubrc"
    registry_path = tmp_path / "confhub"
    monkeypatch.setattr(Registry, "NEXUSRC_PATH", nexusrc)
    monkeypatch.setattr(Registry, "DEFAULT_PATH", registry_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["app", "add", "test-app"])
    return Registry(registry_path)


def test_agent_add_to_root(initialized_registry):
    """루트 레벨에 에이전트 추가"""
    result = runner.invoke(app, ["agent", "add", "gemini", "--root"])
    assert result.exit_code == 0
    agent_dir = initialized_registry.get_root_agent_path("gemini")
    assert (agent_dir / "agent.config.yaml").exists()


def test_agent_add_to_app(initialized_registry):
    """앱 레벨에 에이전트 추가"""
    result = runner.invoke(app, ["agent", "add", "claude", "--app", "test-app"])
    assert result.exit_code == 0
    agent_dir = initialized_registry.get_app_agent_path("test-app", "claude")
    assert (agent_dir / "agent.config.yaml").exists()


def test_agent_add_invalid(initialized_registry):
    """지원하지 않는 에이전트 추가 시 에러"""
    result = runner.invoke(app, ["agent", "add", "unknown-agent", "--root"])
    assert result.exit_code != 0 or "지원" in result.output or "invalid" in result.output.lower()


def test_agent_add_updates_app_config(initialized_registry):
    """에이전트 추가 시 app.config.yaml agents 리스트 업데이트"""
    runner.invoke(app, ["agent", "add", "claude", "--app", "test-app"])
    config = initialized_registry.load_app_config("test-app")
    assert "claude" in config.get("agents", [])


def test_agent_add_creates_default_files(initialized_registry):
    """에이전트 추가 시 기본 파일들 생성"""
    runner.invoke(app, ["agent", "add", "gemini", "--root"])
    agent_dir = initialized_registry.get_root_agent_path("gemini")
    assert (agent_dir / "GEMINI.md").exists()


def test_agent_add_config_content(initialized_registry):
    """에이전트 config.yaml 내용 확인"""
    runner.invoke(app, ["agent", "add", "cursor", "--app", "test-app"])
    agent_dir = initialized_registry.get_app_agent_path("test-app", "cursor")
    with open(agent_dir / "agent.config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert config["agent"] == "cursor"
    assert config["scope"] == "app"
    assert config["version"] == "1.0.0"


def test_agent_add_no_scope_error(initialized_registry):
    """--app 또는 --root 없이 추가 시 에러"""
    result = runner.invoke(app, ["agent", "add", "claude"])
    assert result.exit_code != 0 or "지정" in result.output or "error" in result.output.lower()


def test_agent_add_duplicate(initialized_registry):
    """중복 에이전트 추가 시 경고"""
    runner.invoke(app, ["agent", "add", "gemini", "--root"])
    result = runner.invoke(app, ["agent", "add", "gemini", "--root"])
    assert result.exit_code != 0 or "이미" in result.output or "already" in result.output.lower()


def test_agent_list_root(initialized_registry):
    """루트 에이전트 목록"""
    result = runner.invoke(app, ["agent", "list", "--root"])
    assert result.exit_code == 0
    assert "claude" in result.output  # init으로 이미 생성됨


def test_agent_list_app(initialized_registry):
    """앱 에이전트 목록"""
    runner.invoke(app, ["agent", "add", "gemini", "--app", "test-app"])
    result = runner.invoke(app, ["agent", "list", "--app", "test-app"])
    assert result.exit_code == 0
    assert "gemini" in result.output


def test_agent_list_no_scope_error(initialized_registry):
    """--app 또는 --root 없이 목록 조회 시 에러"""
    result = runner.invoke(app, ["agent", "list"])
    assert result.exit_code != 0 or "지정" in result.output or "error" in result.output.lower()


def test_agent_show(initialized_registry):
    """에이전트 설정 표시"""
    result = runner.invoke(app, ["agent", "show", "claude", "--root"])
    assert result.exit_code == 0
    assert "claude" in result.output


def test_agent_show_resolved_phase5(initialized_registry):
    """--resolved 플래그는 Phase 5 예정 메시지"""
    result = runner.invoke(app, ["agent", "show", "claude", "--root", "--resolved"])
    assert result.exit_code == 0
    assert "Phase 5" in result.output


def test_agent_show_not_found(initialized_registry):
    """존재하지 않는 에이전트 show"""
    result = runner.invoke(app, ["agent", "show", "copilot", "--root"])
    assert result.exit_code != 0 or "없" in result.output or "not found" in result.output.lower()


def test_agent_remove(initialized_registry):
    """에이전트 설정 삭제"""
    runner.invoke(app, ["agent", "add", "cursor", "--app", "test-app"])
    result = runner.invoke(app, ["agent", "remove", "cursor", "--app", "test-app", "--force"])
    assert result.exit_code == 0
    agent_dir = initialized_registry.get_app_agent_path("test-app", "cursor")
    assert not agent_dir.exists()


def test_agent_remove_updates_app_config(initialized_registry):
    """에이전트 삭제 시 app.config.yaml agents 리스트에서 제거"""
    runner.invoke(app, ["agent", "add", "gemini", "--app", "test-app"])
    runner.invoke(app, ["agent", "remove", "gemini", "--app", "test-app", "--force"])
    config = initialized_registry.load_app_config("test-app")
    assert "gemini" not in config.get("agents", [])


def test_agent_remove_not_found(initialized_registry):
    """존재하지 않는 에이전트 삭제 시 에러"""
    result = runner.invoke(app, ["agent", "remove", "copilot", "--root", "--force"])
    assert result.exit_code != 0 or "없" in result.output or "not found" in result.output.lower()


def test_get_agent_valid():
    """유효한 에이전트 식별자"""
    from confhub.core.agents import get_agent

    agent = get_agent("claude")
    assert agent.identifier == "claude"
    assert agent.display_name == "Anthropic Claude"


def test_get_agent_invalid():
    """유효하지 않은 에이전트 식별자"""
    with pytest.raises(ValueError):
        get_agent("unknown")


def test_get_agent_all_supported():
    """모든 지원 에이전트 식별자 확인"""
    for agent_id in SUPPORTED_AGENTS:
        agent = get_agent(agent_id)
        assert agent.identifier == agent_id
        assert agent.display_name
        assert agent.link_target
        assert agent.default_files


def test_agent_add_copilot_creates_github_dir(initialized_registry):
    """copilot 에이전트 추가 시 .github 디렉토리 내 파일 생성"""
    runner.invoke(app, ["agent", "add", "copilot", "--app", "test-app"])
    agent_dir = initialized_registry.get_app_agent_path("test-app", "copilot")
    assert (agent_dir / ".github" / "copilot-instructions.md").exists()


def test_agent_add_codex_creates_agents_md(initialized_registry):
    """codex 에이전트 추가 시 AGENTS.md 파일 생성"""
    runner.invoke(app, ["agent", "add", "codex", "--root"])
    agent_dir = initialized_registry.get_root_agent_path("codex")
    assert (agent_dir / "AGENTS.md").exists()
