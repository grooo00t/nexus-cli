"""nxs app 명령어 테스트"""
import pytest
import yaml
import shutil
from pathlib import Path
from typer.testing import CliRunner

from nexus.cli import app
from nexus.core.registry import Registry


runner = CliRunner()


@pytest.fixture
def initialized_registry(tmp_path, monkeypatch):
    """초기화된 임시 Registry"""
    nexusrc = tmp_path / ".nexusrc"
    registry_path = tmp_path / "nexus"
    monkeypatch.setattr(Registry, "NEXUSRC_PATH", nexusrc)
    monkeypatch.setattr(Registry, "DEFAULT_PATH", registry_path)

    # init으로 초기화
    runner.invoke(app, ["init"])
    return Registry(registry_path)


def test_app_add(initialized_registry):
    """앱 추가"""
    result = runner.invoke(app, ["app", "add", "web-frontend"])
    assert result.exit_code == 0
    assert initialized_registry.app_exists("web-frontend")


def test_app_add_with_description(initialized_registry):
    """--description 옵션으로 앱 추가"""
    result = runner.invoke(app, ["app", "add", "my-app", "--description", "테스트 앱"])
    assert result.exit_code == 0
    config = initialized_registry.load_app_config("my-app")
    assert config["description"] == "테스트 앱"


def test_app_add_creates_structure(initialized_registry):
    """앱 추가 시 디렉토리 구조 생성"""
    runner.invoke(app, ["app", "add", "api-server"])
    app_path = initialized_registry.get_app_path("api-server")
    assert app_path.exists()
    assert (app_path / "app.config.yaml").exists()
    assert (app_path / "agents").exists()


def test_app_add_duplicate(initialized_registry):
    """중복 앱 추가 시 에러"""
    runner.invoke(app, ["app", "add", "duplicate-app"])
    result = runner.invoke(app, ["app", "add", "duplicate-app"])
    assert result.exit_code != 0 or "이미" in result.output or "already" in result.output.lower()


def test_app_list_empty(initialized_registry):
    """앱이 없을 때 목록 표시"""
    result = runner.invoke(app, ["app", "list"])
    assert result.exit_code == 0


def test_app_list_with_apps(initialized_registry):
    """앱이 있을 때 목록 표시"""
    runner.invoke(app, ["app", "add", "frontend"])
    runner.invoke(app, ["app", "add", "backend"])
    result = runner.invoke(app, ["app", "list"])
    assert result.exit_code == 0
    assert "frontend" in result.output
    assert "backend" in result.output


def test_app_show(initialized_registry):
    """앱 상세 정보"""
    runner.invoke(app, ["app", "add", "show-test", "--description", "테스트"])
    result = runner.invoke(app, ["app", "show", "show-test"])
    assert result.exit_code == 0
    assert "show-test" in result.output


def test_app_show_not_found(initialized_registry):
    """존재하지 않는 앱 show"""
    result = runner.invoke(app, ["app", "show", "nonexistent"])
    assert result.exit_code != 0 or "없" in result.output or "not found" in result.output.lower()


def test_app_remove(initialized_registry):
    """앱 삭제"""
    runner.invoke(app, ["app", "add", "to-remove"])
    assert initialized_registry.app_exists("to-remove")

    result = runner.invoke(app, ["app", "remove", "to-remove", "--force"])
    assert result.exit_code == 0
    assert not initialized_registry.app_exists("to-remove")


def test_app_rename(initialized_registry):
    """앱 이름 변경"""
    runner.invoke(app, ["app", "add", "old-name"])
    result = runner.invoke(app, ["app", "rename", "old-name", "new-name"])
    assert result.exit_code == 0
    assert not initialized_registry.app_exists("old-name")
    assert initialized_registry.app_exists("new-name")

    config = initialized_registry.load_app_config("new-name")
    assert config["name"] == "new-name"
