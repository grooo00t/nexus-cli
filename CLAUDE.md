# Nexus CLI

AI 에이전트(Claude, Gemini, Codex, Cursor, Copilot) 설정을 중앙에서 관리하고 프로젝트별 심볼릭 링크로 적용하는 CLI 프레임워크. CLI 명령어: `nxs`.

## 개발 환경 설정

```bash
# 의존성 설치
uv sync
uv sync --extra dev   # 개발 의존성 포함

# 테스트 실행
uv run pytest
uv run pytest tests/test_registry.py  # 특정 파일
uv run pytest -v --cov=nexus           # 커버리지 포함

# CLI 실행
uv run nxs --help

# 린트/타입 검사
uv tool run ruff check .
uv tool run ty check nexus/
```

## 핵심 개념

| 개념 | 설명 |
|------|------|
| **Registry** | `~/.nexus` - 설정의 중앙 저장소. `Registry(base_path)`로 주입 |
| **Root Config** | `root/agents/<agent>/` - 모든 앱이 상속하는 기본 설정 |
| **App** | `apps/<app>/` - 프로젝트 단위 설정 묶음. Root를 상속·오버라이드 |
| **Resolved** | `resolved/<app>/<agent>/` - root + app 병합 결과 (자동 생성) |
| **Link** | 프로젝트의 `.claude/` 등을 `resolved/` 경로로 심볼릭 링크 |

## Registry 디렉토리 구조

```
~/.nexus/
├── nexus.config.yaml
├── root/agents/
│   └── claude/
│       ├── agent.config.yaml
│       └── .claude/
│           ├── CLAUDE.md
│           └── settings.json
├── apps/
│   └── web-frontend/
│       ├── app.config.yaml
│       └── agents/
│           └── claude/
│               ├── agent.config.yaml
│               └── .claude/
│                   ├── CLAUDE.md
│                   └── settings.json
├── resolved/          # nxs resolve로 자동 생성, 레포에 커밋 대상
│   └── web-frontend/
│       └── claude/
│           └── .claude/
└── links/
    └── links.json
```

## 지원 에이전트

| ID | 에이전트 | 링크 대상 |
|----|----------|-----------|
| `claude` | Anthropic Claude | `.claude/` |
| `gemini` | Google Gemini | `.gemini/` |
| `codex` | OpenAI Codex | `AGENTS.md` |
| `cursor` | Cursor AI | `.cursorrules` |
| `copilot` | GitHub Copilot | `.github/copilot-instructions.md` |

## CLI 명령어

```bash
nxs init [--path PATH] [--from-repo URL]
nxs app add <name> / list / show <name> / remove <name>
nxs agent add <agent> --app <app>|--root
nxs agent show/list/remove <agent> --app <app>|--root
nxs resolve <app> / --all / --dry-run
nxs link <app> [--target PATH] [--agent claude,gemini]
nxs unlink <app>
nxs submodule add <app> [--target PATH] [--agent claude,gemini]
nxs submodule remove <app> [--target PATH] [--agent claude,gemini] [--keep-submodule]
nxs sync push [--message MSG] / pull / remote set <url>
nxs status [--app NAME] [--with-links]
nxs install [--from-repo URL] [--verify] [--apps app1,app2]
```

## 병합 전략

| 전략 | 동작 | 기본 대상 |
|------|------|-----------|
| `append` | 루트 내용 + 구분선 + 앱 내용 | `.md` 파일 |
| `deep-merge` | JSON 필드 단위 재귀 병합, 스칼라는 앱이 오버라이드 | `.json` 파일 |
| `replace` | 앱 내용이 루트를 완전 대체 | 명시적 지정 시 |
| `prepend` | 앱 내용 앞에 루트 내용 추가 | 명시적 지정 시 |
