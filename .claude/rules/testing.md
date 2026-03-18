# 테스트 규칙

- 모든 테스트는 `tmp_path` fixture를 사용해 임시 디렉토리에서 실행한다. 실제 `~/.confhub` 경로를 건드리지 않는다.
- `Registry.DEFAULT_PATH`와 `Registry.NEXUSRC_PATH`는 `monkeypatch`로 패치한다.
- 새 기능 추가 시 대응하는 단위 테스트를 `tests/`에 추가한다.
- 테스트 실행: `uv run pytest` (전체), `uv run pytest tests/<file>.py` (개별)
