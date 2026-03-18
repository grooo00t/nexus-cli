"""nxs resolve 명령어 테스트"""

import pytest
from typer.testing import CliRunner

from confhub.cli import app
from confhub.core.registry import Registry

runner = CliRunner()


@pytest.fixture
def registry_with_app(tmp_path, monkeypatch):
    """앱과 에이전트가 있는 Registry"""
    nexusrc = tmp_path / ".confhubrc"
    registry_path = tmp_path / "confhub"
    monkeypatch.setattr(Registry, "NEXUSRC_PATH", nexusrc)
    monkeypatch.setattr(Registry, "DEFAULT_PATH", registry_path)

    runner.invoke(app, ["init"])
    runner.invoke(app, ["app", "add", "web-frontend"])
    runner.invoke(app, ["agent", "add", "claude", "--app", "web-frontend"])

    return Registry(registry_path)


def test_resolve_app(registry_with_app):
    """앱 resolve"""
    result = runner.invoke(app, ["resolve", "web-frontend"])
    assert result.exit_code == 0

    resolved = registry_with_app.get_resolved_agent_path("web-frontend", "claude")
    assert resolved.exists()


def test_resolve_dry_run(registry_with_app):
    """dry-run: 파일 미생성"""
    result = runner.invoke(app, ["resolve", "web-frontend", "--dry-run"])
    assert result.exit_code == 0

    resolved = registry_with_app.get_resolved_agent_path("web-frontend", "claude")
    assert not resolved.exists()


def test_resolve_all(registry_with_app):
    """--all 플래그"""
    runner.invoke(app, ["app", "add", "api-server"])
    runner.invoke(app, ["agent", "add", "gemini", "--app", "api-server"])

    result = runner.invoke(app, ["resolve", "--all"])
    assert result.exit_code == 0


def test_resolve_unknown_app(registry_with_app):
    """존재하지 않는 앱 resolve 시 에러"""
    result = runner.invoke(app, ["resolve", "nonexistent-app"])
    assert result.exit_code != 0


def test_resolve_no_args(registry_with_app):
    """인수 없이 호출 시 에러"""
    result = runner.invoke(app, ["resolve"])
    assert result.exit_code != 0


def test_resolve_dry_run_output(registry_with_app):
    """dry-run 출력에 web-frontend / claude 포함"""
    result = runner.invoke(app, ["resolve", "web-frontend", "--dry-run"])
    assert result.exit_code == 0
    # Rich는 [bold cyan][dry-run]...를 렌더링할 때 마크업 태그를 제거하므로
    # "web-frontend" 텍스트가 출력에 포함되는지 확인
    assert "web-frontend" in result.output
    assert "claude" in result.output
