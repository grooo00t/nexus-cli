"""nxs init 명령어 테스트"""

import json

import pytest
import yaml
from typer.testing import CliRunner

from confhub.cli import app
from confhub.core.registry import Registry

runner = CliRunner()


@pytest.fixture
def tmp_nexusrc(tmp_path, monkeypatch):
    """~/.confhubrc를 임시 경로로 패치"""
    nexusrc = tmp_path / ".confhubrc"
    monkeypatch.setattr(Registry, "NEXUSRC_PATH", nexusrc)
    return nexusrc


def test_init_default_path(tmp_path, monkeypatch, tmp_nexusrc):
    """기본 경로 초기화"""
    registry_path = tmp_path / "confhub"
    monkeypatch.setattr(Registry, "DEFAULT_PATH", registry_path)

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (registry_path / "confhub.config.yaml").exists()
    assert (registry_path / "apps").exists()
    assert (registry_path / "root" / "agents").exists()
    assert (registry_path / "resolved").exists()
    assert (registry_path / "links").exists()


def test_init_custom_path(tmp_path, tmp_nexusrc):
    """--path 옵션으로 특정 경로 초기화"""
    registry_path = tmp_path / "my-confhub"
    result = runner.invoke(app, ["init", "--path", str(registry_path)])
    assert result.exit_code == 0
    assert (registry_path / "confhub.config.yaml").exists()


def test_init_creates_config(tmp_path, tmp_nexusrc):
    """confhub.config.yaml 내용 검증"""
    registry_path = tmp_path / "confhub"
    runner.invoke(app, ["init", "--path", str(registry_path)])

    config_file = registry_path / "confhub.config.yaml"
    with open(config_file) as f:
        config = yaml.safe_load(f)

    assert config["version"] == "1.0.0"
    assert "registry" in config
    assert "defaults" in config


def test_init_creates_claude_template(tmp_path, tmp_nexusrc):
    """Claude 기본 템플릿 생성 검증"""
    registry_path = tmp_path / "confhub"
    runner.invoke(app, ["init", "--path", str(registry_path)])

    claude_dir = registry_path / "root" / "agents" / "claude" / ".claude"
    assert claude_dir.exists()
    assert (claude_dir / "CLAUDE.md").exists()
    assert (claude_dir / "settings.json").exists()

    with open(claude_dir / "settings.json") as f:
        settings = json.load(f)
    assert "model" in settings


def test_init_creates_links_json(tmp_path, tmp_nexusrc):
    """links.json 생성 검증"""
    registry_path = tmp_path / "confhub"
    runner.invoke(app, ["init", "--path", str(registry_path)])

    links_file = registry_path / "links" / "links.json"
    assert links_file.exists()
    with open(links_file) as f:
        assert json.load(f) == {}


def test_init_already_initialized(tmp_path, tmp_nexusrc):
    """이미 초기화된 경우 경고"""
    registry_path = tmp_path / "confhub"
    runner.invoke(app, ["init", "--path", str(registry_path)])
    result = runner.invoke(app, ["init", "--path", str(registry_path)])
    assert result.exit_code == 0
    # 두 번째 실행 시 경고 메시지 포함
    assert "already" in result.output.lower() or "이미" in result.output


def test_init_registers_nexusrc(tmp_path, tmp_nexusrc):
    """~/.confhubrc에 경로 등록"""
    registry_path = tmp_path / "confhub"
    runner.invoke(app, ["init", "--path", str(registry_path)])

    assert tmp_nexusrc.exists()
    with open(tmp_nexusrc) as f:
        data = yaml.safe_load(f)
    assert str(registry_path) in data.get("registry_path", "")
