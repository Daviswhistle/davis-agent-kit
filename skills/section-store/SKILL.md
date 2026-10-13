---
name: section-store
description: Use as the default project-context retrieval workflow when a project has a section-store PROJECT.md, or when the user requests a single indexed project knowledge source. Read and update relevant sections by stable ID, and verify decision-critical facts against current evidence. Not a code capability map or an instruction-precedence mechanism.
---

# Section Store

프로젝트 지식·규칙·결정·작업 상태를 **하나의 UTF-8 Markdown 원본**에 두고, 자동 생성 색인으로 필요한 섹션만 읽고 수정한다. Python 3.10+ 표준 라이브러리만 사용한다. 임베딩, 모델 호출, 별도 서버는 없다.

## 적용 범위

사용자가 지정한 원본을 사용한다. 지정하지 않았다면 현재 프로젝트 루트의 `PROJECT.md`만 확인하며, 원본을 찾으려고 저장소 전체를 순회하지 않는다. 원본이 없다면 사용자가 지식 통합·생성을 요청한 범위의 확인된 내용으로만 만든다. 예시를 프로젝트 사실로 복사하거나 과거 개인 맥락을 공개 저장소에 넣지 않는다.

기존 코드, `AGENTS.md`, 다른 skill의 원본을 무조건 병합하지 않는다. 이 파일은 프로젝트 자료이며 상위 지침·권한을 대체하지 않는다. 색인과 본문 모두 같은 정보 공개 경계를 따른다. 서로 다른 접근 권한의 자료는 하나로 합치지 않는다.

## 근거와 현재성

기존 원본이 있으면 프로젝트 맥락은 색인에서 필요한 섹션을 고르는 것으로 시작한다. 없으면 일반적인 코드·문서 탐색을 사용하며, 사용자의 지식 통합 요청 없이 새 원본을 만들지 않는다. 반복 확인할 가치가 있는 목적·제약·계약·결정과 검증 근거만 유지한다. 원래 코드·규범 문서·결과물은 각자의 원본으로 남기고, 실행 로그·raw 평가 trace·과거 작업 기록을 통째로 복제하지 않는다.

결정을 바꾸는 핵심 사실에는 본문에 근거 위치, 확인한 commit/hash 또는 결과 시점, 적용 범위를 기록한다. 현재 상태로 사용할 때는 해당 근거가 여전히 맞는지 확인한다. 근거가 바뀌었거나 확보되지 않으면 현재 사실로 단정하지 않고 재검증 필요 또는 미확인으로 표시한다. 관련 구현·결정 변경 작업에서는 영향을 받는 사실과 검색 메타데이터도 함께 갱신한다.

`check`는 Markdown 원본과 색인의 일치만 검사한다. 코드·설정·운영 결과와 문서 내용이 맞는지는 검증하지 않으며, 원본 해시가 그대로라는 사실로 핵심 주장의 최신성을 대신하지 않는다.

## 원본 형식

각 섹션은 열 0의 한 줄 JSON 주석으로 시작하고 다음 마커 직전 또는 EOF에서 끝난다. 공백 외의 모든 내용은 섹션 안에 둔다.

```markdown
<!-- section: {"id":"purpose","title":"프로젝트 목적","summary":"대상 사용자와 성공 조건","tags":["목표"],"related":[]} -->
# 프로젝트 목적
확인된 프로젝트 목적과 성공 조건을 여기에 기록한다.

<!-- section: {"id":"validation","title":"검증","summary":"완료 판정에 필요한 검사","tags":["테스트"],"related":["purpose"]} -->
# 검증
실제로 사용하는 검사와 확인된 결과를 기록한다.
```

`id`, `title`, `summary`는 필수다. `tags`, `related`는 생략하면 빈 목록이다. ID는 영문자로 시작하고 영문자·숫자·`.`·`_`·`-`로 구성하며 최대 128자다. 제목이나 위치가 바뀌어도 ID를 유지한다. `related`에는 존재하는 ID를 넣는다.

제목·요약·태그는 작성자가 의미를 명시하는 부분이다. helper는 경계·위치를 자동 계산하지, 자유로운 본문의 의미를 자동 추론하지 않는다. 본문 의미가 바뀌면 요약·태그도 검토하고, 검색 표현이 달라졌다면 원본 마커를 직접 편집한 뒤 `build`한다. 중복 ID, 깨진 메타데이터, 끊어진 참조는 거부한다.

열 0~3의 backtick/tilde fenced code block 안의 마커 예시는 무시한다. 닫히지 않은 fence는 거부한다. 일반 Markdown 전체를 해석하는 parser는 아니므로 마커 예시를 목록·인용문·HTML 주석으로 숨기지 말고 top-level fence로 감싼다.

## 사용 절차

helper는 이 skill 디렉터리의 `scripts/store.py`다. 아래는 기본 설치 위치 기준이며 사용자 지정 skills-home을 사용했다면 실제 skill 위치로 바꾼다.

```bash
STORE="$HOME/.agents/skills/section-store/scripts/store.py"
```

**최초 생성.** 첫 섹션 본문을 UTF-8 파일에 작성한 뒤 실행한다. 기존 원본은 덮어쓰지 않는다. 이미 마커를 작성한 원본이 있으면 `init` 대신 `build`를 쓴다.

```bash
python3 "$STORE" init --source PROJECT.md --id purpose \
  --title "프로젝트 목적" --summary "대상 사용자와 성공 조건" \
  --body-file purpose.txt
python3 "$STORE" build --source PROJECT.md
```

**탐색.** 먼저 색인의 제목·요약·태그를 읽어 범위를 고른다. `--query`는 대소문자를 무시하는 공백 구분 AND 부분문자열 검색이며 본문·의미 검색은 아니다. 기본 50개 단위이고 `next_offset`이 있으면 필요한 만큼만 다음 페이지를 읽는다. 색인에서 찾지 못했다는 이유로 내용 자체가 없다고 단정하지 말고, 다른 태그·상위 섹션 또는 해당 원본 안의 좁은 본문 검색으로 확인한다.

```bash
python3 "$STORE" list --source PROJECT.md --query "검증" --limit 10
python3 "$STORE" read --source PROJECT.md --id validation --related
```

`read`는 선택된 본문과 메타데이터만 JSON으로 반환한다. `--id`를 반복할 수 있으며 `--related`는 직접 참조하는 섹션 한 단계만 추가한다. 기본 선택 크기 한도는 마커를 포함한 원본 65,536 bytes다. 초과하면 자르지 않고 거부하므로 섹션을 좁히거나 필요한 경우 `--max-bytes`를 명시한다.

**수정.** 직전 `read`/`list`의 실제 `source_sha256`을 `--expect-source`에 넣는다. 아래 `SHA256_FROM_LAST_READ`는 설명용 자리표시자다. 충돌하면 현재 내용을 다시 읽고 양쪽 변경을 조정한다. 새 해시만 받아 무조건 재시도하지 않는다.

```bash
python3 "$STORE" replace --source PROJECT.md --id validation \
  --body-file updated-validation.txt --expect-source SHA256_FROM_LAST_READ
python3 "$STORE" append --source PROJECT.md --id deployment \
  --title "배포" --summary "배포 순서와 확인 항목" --related validation \
  --body-file deployment.txt --expect-source SHA256_FROM_LAST_READ
```

각 쓰기 뒤 해시가 바뀌므로 연속 쓰기는 새 응답의 해시와 현재 내용을 사용한다. `replace`는 본문만 바꾸고 마커·ID를 유지하며 다른 섹션의 마커·본문이 그대로인지도 검사한다. 다음 섹션 앞의 마지막 개행은 필요하면 보충한다. `append`는 새 ID만 허용한다. 본문으로 다른 섹션을 주입하거나 숨기는 변경은 거부한다.

제목·요약·태그 변경, 섹션 재배치·삭제는 다른 writer가 없는 상태에서 원본을 직접 편집한 뒤 즉시 `build`한다. 직접 편집에 helper의 버전 충돌 보호가 적용된다고 가정하지 않는다. 삭제 전 참조도 함께 정리한다.

## 색인과 일관성

원본 `PROJECT.md` 옆에 `PROJECT.md.index.json`을 생성한다. 원본이 유일한 관리 대상이고 색인은 언제든 재생성할 수 있는 cache다. 손으로 색인을 수정하지 않는다.

색인은 스키마 버전, 원본 SHA-256, 크기, ID·제목·요약·태그·연관 ID, 1-based inclusive 줄 범위, 0-based half-open byte 범위, 섹션 체크섬을 담는다. 빈 본문은 body-start가 end-line보다 클 수 있다. 줄 번호가 밀리면 다시 계산하고 다른 섹션의 참조는 ID로 유지한다.

`init`/`replace`/`append`는 색인도 갱신한다. 직접 편집 후에는 `build`가 필요하다. 읽기·검색은 색인이 없거나 오래되었으면 오류를 반환하며 자동 쓰기나 조용한 구버전 사용을 하지 않는다.

```bash
python3 "$STORE" check --source PROJECT.md
```

대상 프로젝트 CI에서도 이 명령으로 원본·색인 drift를 검사할 수 있다. 외부 편집기에 대한 watcher나 자동 저장 hook은 설치하지 않는다. Git으로 공유한다면 원본과 해당 버전의 색인을 함께 커밋하거나, 원본만 공유하고 사용 전에 색인을 재생성한다. lock과 임시 본문 파일은 커밋하지 않는다.

매 읽기는 원본 해시를 **streaming으로 전체 확인**한 뒤 선택 구간으로 seek한다. 모델에 원본 전체를 전달하지 않지만 전체 파일 I/O가 사라지는 것은 아니다. 색인에도 체크섬이 있으나 이는 손상 탐지이며 악의적인 작성자에 대한 인증 수단은 아니다.

## 쓰기·복구 경계

helper writer는 원본 옆의 `.lock`으로 직렬화하고 원본 전체의 기대 해시를 비교한다. 서로 다른 섹션을 수정하더라도 오래된 버전이면 거부한다. 파일별 임시 저장 후 교체하며, **원본과 색인 두 파일을 묶은 데이터베이스 트랜잭션은 아니다.** 원본 저장 뒤 색인 저장에 실패하면 `SOURCE SAVED` 오류가 나오고 이후 읽기는 실패한다. 원본을 되돌리거나 같은 수정을 반복하지 말고 `build`로 복구한다.

프로세스 강제 종료 후 남은 lock은 다른 writer가 살아 있지 않은지 확인한 뒤에만 제거한다. helper 밖의 편집기, 다른 worktree/복제본, hard-link alias, 네트워크 파일시스템까지 동시 쓰기를 조정한다고 주장하지 않는다. 민감한 동시 편집이나 트랜잭션 요구가 커지면 별도 저장소 설계가 필요하다.

성공은 exit 0과 JSON stdout, 거부·파일 오류는 exit 2와 stderr다. 최종 보고에는 실제 색인/부분 읽기/수정 검증 결과와 남은 제한을 구분한다. helper 테스트 통과를 모델의 검색 정확도나 판단 품질 향상으로 표현하지 않는다.
