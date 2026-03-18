"""에이전트별 설정 처리 모듈"""

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_AGENTS = ["claude", "gemini", "codex", "cursor", "copilot"]


@dataclass
class AgentConfig:
    """에이전트 메타데이터"""

    identifier: str  # "claude"
    display_name: str  # "Anthropic Claude"
    link_target: str  # ".claude"  (프로젝트 내 폴더/파일)
    config_dir: str  # ".claude"  (설정 디렉토리 이름)
    is_dir_link: bool  # True: 디렉토리 링크, False: 파일 링크
    default_files: dict  # {"CLAUDE.md": "# ...", "settings.json": "{}"}


# 에이전트별 설정 정의
AGENTS: dict = {
    "claude": AgentConfig(
        identifier="claude",
        display_name="Anthropic Claude",
        link_target=".claude",
        config_dir=".claude",
        is_dir_link=True,
        default_files={
            "CLAUDE.md": "# Claude 에이전트 설정\n\n",
            "settings.json": '{\n  "model": "claude-sonnet-4-6",\n  "permissions": {"allow": [], "deny": []}\n}\n',
        },
    ),
    "gemini": AgentConfig(
        identifier="gemini",
        display_name="Google Gemini",
        link_target=".gemini",
        config_dir=".gemini",
        is_dir_link=True,
        default_files={
            "GEMINI.md": "# Gemini 에이전트 설정\n\n",
        },
    ),
    "codex": AgentConfig(
        identifier="codex",
        display_name="OpenAI Codex",
        link_target="AGENTS.md",
        config_dir=".",  # 루트에 파일
        is_dir_link=False,
        default_files={
            "AGENTS.md": "# Codex 에이전트 설정\n\n",
        },
    ),
    "cursor": AgentConfig(
        identifier="cursor",
        display_name="Cursor AI",
        link_target=".cursorrules",
        config_dir=".",
        is_dir_link=False,
        default_files={
            ".cursorrules": "# Cursor 에이전트 설정\n\n",
        },
    ),
    "copilot": AgentConfig(
        identifier="copilot",
        display_name="GitHub Copilot",
        link_target=".github/copilot-instructions.md",
        config_dir=".github",
        is_dir_link=False,
        default_files={
            ".github/copilot-instructions.md": "# Copilot 에이전트 설정\n\n",
        },
    ),
}


def get_agent(identifier: str) -> AgentConfig:
    """에이전트 식별자로 AgentConfig 반환"""
    if identifier not in AGENTS:
        raise ValueError(
            f"지원하지 않는 에이전트: {identifier}. 지원 목록: {', '.join(SUPPORTED_AGENTS)}"
        )
    return AGENTS[identifier]


def get_agent_dir(registry_base: Path, scope: str, agent: str, app_name: str | None = None) -> Path:
    """에이전트 설정 파일이 저장되는 디렉토리 반환

    scope가 "root"이면: registry/root/agents/<agent>/
    scope가 "app"이면: registry/apps/<app_name>/agents/<agent>/
    """
    if scope == "root":
        return registry_base / "root" / "agents" / agent
    elif scope == "app":
        if app_name is None:
            raise ValueError("app scope에서는 app_name이 필요합니다")
        return registry_base / "apps" / app_name / "agents" / agent
    else:
        raise ValueError(f"알 수 없는 scope: {scope}")
