"""ConfHub CLI - AI 에이전트 설정 중앙 관리 프레임워크"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("agent-confhub-cli")
except PackageNotFoundError:
    __version__ = "unknown"
