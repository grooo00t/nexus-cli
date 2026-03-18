"""ConfHub Registry - 파일 경로 및 설정 접근 핵심 모듈"""

from pathlib import Path

import yaml


class RegistryNotFoundError(Exception):
    """Registry가 초기화되지 않은 경우 발생하는 예외"""

    pass


class Registry:
    """ConfHub Registry 관리 클래스

    base_path를 주입받아 테스트 용이성을 확보합니다.
    모든 파일 경로와 설정 접근을 중앙에서 관리합니다.
    """

    DEFAULT_PATH = Path.home() / ".confhub"
    NEXUSRC_PATH = Path.home() / ".confhubrc"
    CONFIG_FILE = "confhub.config.yaml"

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    # 경로 프로퍼티들

    @property
    def config_path(self) -> Path:
        """Registry 설정 파일 경로"""
        return self.base_path / self.CONFIG_FILE

    @property
    def root_path(self) -> Path:
        """루트 설정 디렉토리 경로"""
        return self.base_path / "root"

    @property
    def root_agents_path(self) -> Path:
        """루트 에이전트 설정 디렉토리 경로"""
        return self.root_path / "agents"

    @property
    def apps_path(self) -> Path:
        """앱 설정 디렉토리 경로"""
        return self.base_path / "apps"

    @property
    def resolved_path(self) -> Path:
        """병합된 설정 출력 디렉토리 경로"""
        return self.base_path / "resolved"

    @property
    def links_path(self) -> Path:
        """심볼릭 링크 관리 디렉토리 경로"""
        return self.base_path / "links"

    @property
    def links_file(self) -> Path:
        """심볼릭 링크 정보 파일 경로"""
        return self.links_path / "links.json"

    def is_initialized(self) -> bool:
        """Registry가 초기화되었는지 확인"""
        return self.config_path.exists()

    def require_initialized(self):
        """초기화 여부 확인, 초기화되지 않은 경우 예외 발생"""
        if not self.is_initialized():
            raise RegistryNotFoundError(
                f"ConfHub Registry가 초기화되지 않았습니다: {self.base_path}\n"
                "'nxs init' 명령어로 초기화하세요."
            )

    def load_config(self) -> dict:
        """confhub.config.yaml 로드"""
        self.require_initialized()
        with open(self.config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_config(self, config: dict) -> None:
        """confhub.config.yaml 저장"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def get_app_path(self, app_name: str) -> Path:
        """특정 앱의 설정 디렉토리 경로 반환"""
        return self.apps_path / app_name

    def get_root_agent_path(self, agent: str) -> Path:
        """루트 에이전트 설정 경로 반환"""
        return self.root_agents_path / agent

    def get_app_agent_path(self, app_name: str, agent: str) -> Path:
        """특정 앱의 에이전트 설정 경로 반환"""
        return self.get_app_path(app_name) / "agents" / agent

    def get_resolved_agent_path(self, app_name: str, agent: str) -> Path:
        """특정 앱의 병합된 에이전트 설정 경로 반환"""
        return self.resolved_path / app_name / agent

    def list_apps(self) -> list[str]:
        """등록된 앱 목록 반환"""
        if not self.apps_path.exists():
            return []
        return [
            d.name
            for d in self.apps_path.iterdir()
            if d.is_dir() and (d / "app.config.yaml").exists()
        ]

    def app_exists(self, app_name: str) -> bool:
        """앱 존재 여부 확인"""
        return (self.get_app_path(app_name) / "app.config.yaml").exists()

    def load_app_config(self, app_name: str) -> dict:
        """앱 설정 파일 로드"""
        config_file = self.get_app_path(app_name) / "app.config.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"앱 '{app_name}'을 찾을 수 없습니다")
        with open(config_file, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_app_config(self, app_name: str, config: dict) -> None:
        """앱 설정 파일 저장"""
        config_file = self.get_app_path(app_name) / "app.config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    @classmethod
    def get_default(cls) -> "Registry":
        """~/.confhubrc에서 경로를 읽어 기본 Registry 반환"""
        if cls.NEXUSRC_PATH.exists():
            with open(cls.NEXUSRC_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                path = data.get("registry_path")
                if path:
                    return cls(Path(path))
        return cls(cls.DEFAULT_PATH)

    @classmethod
    def save_nexusrc(cls, registry_path: Path) -> None:
        """~/.confhubrc에 Registry 경로 저장"""
        with open(cls.NEXUSRC_PATH, "w", encoding="utf-8") as f:
            yaml.dump({"registry_path": str(registry_path)}, f)
