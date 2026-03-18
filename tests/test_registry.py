"""Registry 클래스 단위 테스트"""
import pytest
from pathlib import Path
import yaml

from nexus.core.registry import Registry, RegistryNotFoundError


@pytest.fixture
def tmp_registry(tmp_path):
    """임시 디렉토리에 Registry 생성"""
    return Registry(tmp_path / "nexus")


def test_registry_paths(tmp_registry):
    """경로 프로퍼티 검증"""
    base = tmp_registry.base_path
    assert tmp_registry.config_path == base / "nexus.config.yaml"
    assert tmp_registry.root_path == base / "root"
    assert tmp_registry.apps_path == base / "apps"
    assert tmp_registry.resolved_path == base / "resolved"


def test_registry_not_initialized(tmp_registry):
    """초기화 전 상태 확인"""
    assert not tmp_registry.is_initialized()


def test_require_initialized_raises(tmp_registry):
    """초기화 전 require_initialized() 호출 시 예외"""
    with pytest.raises(RegistryNotFoundError):
        tmp_registry.require_initialized()


def test_registry_initialized_after_config(tmp_registry):
    """config 파일 생성 후 초기화 상태"""
    tmp_registry.base_path.mkdir(parents=True)
    tmp_registry.config_path.write_text("version: '1.0.0'\n")
    assert tmp_registry.is_initialized()


def test_load_save_config(tmp_registry):
    """설정 파일 저장/로드"""
    tmp_registry.base_path.mkdir(parents=True)
    config = {"version": "1.0.0", "registry": {"name": "test"}}
    tmp_registry.save_config(config)
    loaded = tmp_registry.load_config()
    assert loaded["version"] == "1.0.0"
    assert loaded["registry"]["name"] == "test"


def test_list_apps_empty(tmp_registry):
    """앱 없을 때 빈 리스트"""
    tmp_registry.apps_path.mkdir(parents=True)
    assert tmp_registry.list_apps() == []


def test_list_apps_with_apps(tmp_registry):
    """앱이 있을 때 목록 반환"""
    app_dir = tmp_registry.apps_path / "my-app"
    app_dir.mkdir(parents=True)
    (app_dir / "app.config.yaml").write_text("name: my-app\n")

    apps = tmp_registry.list_apps()
    assert "my-app" in apps


def test_app_exists(tmp_registry):
    """앱 존재 여부 확인"""
    app_dir = tmp_registry.apps_path / "test-app"
    app_dir.mkdir(parents=True)
    (app_dir / "app.config.yaml").write_text("name: test-app\n")

    assert tmp_registry.app_exists("test-app")
    assert not tmp_registry.app_exists("nonexistent")
