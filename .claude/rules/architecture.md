# 아키텍처 원칙

- **Registry 의존성 주입**: 모든 코어 클래스는 `Registry(base_path)` 또는 `base_path`를 주입받는다. 하드코딩된 `~/.confhub` 경로 사용 금지.
- **resolved/ 불변성**: `root/`와 `apps/` 원본은 절대 수정하지 않는다. 병합 결과는 반드시 `resolved/`에만 쓴다.
- **심볼릭 링크 단위**: 에이전트 폴더(`.claude/` 등) 전체를 단위로 링크한다. 개별 파일 링크 금지.
- **links.json이 링크 레지스트리**: 심볼릭 링크 상태는 `links/links.json`에서 추적한다. 파일시스템 탐색만으로 상태를 판단하지 않는다.
