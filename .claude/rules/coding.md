# 코딩 규칙

## 타입 안전성

- `str | None` 파라미터를 `str`을 받는 함수에 전달하기 전에 반드시 `assert param is not None`으로 타입을 좁힌다.
- `Optional[X]` 대신 `X | None` 문법을 사용한다 (Python 3.10+).

## 파일 입출력

- 모든 파일 열기에 `encoding="utf-8"`을 명시한다.
- 설정 파일 포맷: Registry 메타 → YAML, 링크 정보 → JSON, 에이전트 설정 → YAML.

## CLI 패턴

- 오류 발생 시 `print_error()`로 메시지를 출력하고 `raise typer.Exit(1)`로 종료한다.
- Registry 미초기화 상태는 `RegistryNotFoundError`로 처리하고 `nxs init` 실행을 안내한다.
- 성공/경고/오류는 `print_success()` / `print_warning()` / `print_error()` 헬퍼로 구분 출력한다.

## 린트/타입 검사

```bash
uv tool run ruff check . --fix   # import 정렬, 미사용 import 등 자동 수정
uv tool run ruff format .        # 포맷 적용
uv tool run ty check confhub/      # 타입 오류 확인
```

커밋 전 위 세 명령이 오류 없이 통과해야 한다.
