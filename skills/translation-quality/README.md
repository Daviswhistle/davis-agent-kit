# Translation Quality Skill

긴 비즈니스 문서, 연차보고서, 재무보고서, 실적발표 컨퍼런스콜을 자연스러운 한국어로 번역하기 위한 Codex 스킬입니다.
이 레포만 새로 받아 설치해도 동작하도록 품질 기준, 검수 프롬프트, HTML QA helper, 벤치마크 reference를 함께 포함합니다.

이 스킬은 특히 다음 문제를 막기 위해 만들었습니다.

- 영어 문장 구조를 그대로 따라간 어색한 직역
- 화자 전환 누락
- 문단 간격이 너무 빽빽하거나 복사하면 줄바꿈이 사라지는 문제
- 링크, 의미 있는 이태릭체, 설명 주석 누락 또는 남용
- 긴 문서를 한 번에 생성하다가 중간에 멈추거나 일부가 빠지는 문제
- 근거가 부족한 거버넌스/이벤트 주석
- 실적 가이던스와 숫자 지표 오역
- 연차보고서/재무보고서의 페이지 구조, 표 정렬, 주석, 링크, 법정 용어가 무너지는 문제
- 같은 숫자 가이던스가 여러 번 나올 때 한 곳만 맞고 다른 곳이 틀리는 문제
- 통역이 포함된 컨퍼런스콜에서 원 발언자와 통역자 라벨이 뒤섞이는 문제
- RMB/CNY, billion, 억 단위가 한국어 독자에게 잘못된 규모로 읽히는 문제
- 개별 표현만 고치고 그 지적의 상위 실패 원칙을 반영하지 못하는 문제

## 이 스킬이 강제하는 기준

- 영어 직역투를 피하고 자연스러운 한국어 비즈니스 문체로 번역
- 독자용 최종 문서에 추출 라벨, 내부 메타데이터, 비영어 발언 placeholder를 노출하지 않음
- 화자는 바뀔 때에만 표시
- 통역된 발언은 가능한 경우 원 발언자에게 귀속
- 문장마다 줄을 나누지 않고 문단 기준으로 구성
- 서식이 필요한 경우 복사-붙여넣기에 안전한 HTML 사용
- 화자명 굵게, 링크 유지, 이태릭체와 주석의 의미 구분
- 설명 주석은 용어의 첫 등장 위치에만 삽입
- 긴 문서는 청크 단위로 번역
- 중간 번역 파일, 진행표, QA 리포트 생성
- 긴 보고서는 페이지/섹션 단위 구조와 표 inventory를 유지
- 레포에 포함된 품질 벤치마크를 기준으로 사전 맥락 없이도 결과물을 검수
- 작업 목표와 완료 조건을 QA 리포트에 명시
- 별도 개념 검수 패스로 화자, 문체, 재무 단위, 주석, 보고서 표/구조의 목적을 점검
- sub-agent나 별도 Codex 프로세스가 가능하면 prose/source fidelity, report/table 구조, HTML publication 검수를 분리
- 구조 오류, source artifact, 숫자/단위 drift, 명백한 직역 템플릿은 기계 검색으로 확인
- `말씀`, `측면에서`, `비교됩니다` 같은 일반 표현의 적절성은 금칙어가 아니라 개념 검수에서 문맥별 판단
- `GAAP`, `SG&A`, `EPS`, `SKU` 같은 일반 약어를 자동으로 이태릭 처리하지 않고, 주석과 source term의 시각적 의미를 구분
- 실적 가이던스와 재무 숫자를 source unit과 최종 HTML `data-unit` 단위로 대조
- 실행한 검증, 생략한 검증, 남은 리스크를 구분해 기록
- 기존 레퍼런스와 동등한 품질을 주장할 때는 실제 candidate 산출물을 만들고, 구조 메트릭뿐 아니라 Lululemon/PDD/YesAsia 레퍼런스 축에 맞춘 개념 검수와 source-fidelity 증거를 남김
- 최종 HTML 구조와 파일 상태 검증

## 설치

스킬 폴더 전체를 Codex 사용자 스킬 디렉터리에 복사하세요. `agents/`, `scripts/`, `tests/`도 스킬의 일부입니다.

```bash
mkdir -p ~/.codex/skills/translation-quality
rsync -a ./ ~/.codex/skills/translation-quality/
```

복사한 뒤 Codex를 재시작하거나 새 세션을 시작해 스킬 목록이 다시 로드되도록 하세요.

설치 여부를 확인하려면 새 Codex 세션에서 번역 관련 요청을 해보면 됩니다. 요청이 스킬 설명과 맞으면 Codex가 자동으로 이 스킬을 선택합니다.

## 언제 사용되나

다음과 같은 요청에서 사용하도록 설계했습니다.

- 긴 문서 번역
- 실적발표 컨퍼런스콜 번역
- 금융/비즈니스 문서 번역
- 연차보고서, 감사보고서, 사업보고서, 투자설명서 번역
- 블로그에 붙여넣을 한국어 번역
- 기존 한국어 번역본 검토와 수정
- 화자, 문단, 링크, 의미 있는 이태릭체, 주석을 보존해야 하는 번역

자동 선택에 맡길 수도 있습니다.

```text
이 실적발표 컨퍼런스콜 전문을 자연스러운 한국어로 번역하고, 블로그에 붙여넣기 좋게 만들어줘.
```

스킬 이름을 직접 적어도 됩니다.

```text
translation-quality 스킬을 사용해. 이 PDF 컨퍼런스콜을 한국어 HTML로 번역해줘.
```

## 기대 작업 흐름

긴 transcript를 처리할 때 이 스킬은 Codex가 다음 절차를 따르도록 요구합니다.

1. 원문을 추출하고 번역 단위로 정리합니다.
2. 한 줄에 여러 화자가 붙어 있으면 번역 전에 분리합니다.
3. 전체 문서를 한 번에 생성하지 않고 청크 단위로 번역합니다.
4. 중간 번역 파일과 진행표를 저장합니다.
5. 서식이 필요한 경우 복사-붙여넣기에 안전한 HTML로 조립합니다.
6. 화자 전환, 링크, 의미 있는 이태릭체, 설명 주석을 보존합니다.
7. 보고서형 문서는 페이지/섹션, 표, 주석, 법정 명칭, 재무제표 구조를 보존합니다.
8. 개념 검수 에이전트, 보고서 검수 에이전트, 또는 같은 프롬프트의 별도 패스로 독자 관점의 실패 유형을 찾습니다.
9. 어색한 직역 표현, 반복 숫자 가이던스, HTML 구조, 표 alignment, 최종 파일 상태를 검수합니다.
10. 검증 명령, 생략한 검사와 사유, 남은 리스크를 QA 리포트에 분리해 남깁니다.

이 스킬이 엄격한 이유는 긴 transcript 번역에서 누락, 직역투, 숫자 오역, 서식 깨짐이 쉽게 발생하기 때문입니다.

## 검증 기준

HTML 결과물은 helper로 구조, source artifact, 숫자/단위, 명백한 반복 실패 템플릿을 검사합니다. 일반 표현의 적절성은 helper가 아니라 개념 검수에서 판단합니다. 긴 실적발표 transcript에서는 `--source-units`를 함께 넘겨 source unit과 최종 HTML의 `data-unit` 문단을 직접 대조해야 합니다.

```bash
python3 scripts/qa_html_translation.py \
  --output outputs/<document>_ko.html \
  --chunks work/translation_chunks \
  --source-units work/source_units.tsv \
  --expect-title "<정확한 제목>" \
  --expect-date "YYYY.MM.DD." \
  --strict-style
```

이 검사는 반복되는 성장률 범위까지 확인합니다. 예를 들어 `mid-to-high teens`가 한 문단에서는 맞고 다른 문단에서는 낮게 번역되는 경우 실패해야 합니다.

연차보고서나 재무보고서처럼 transcript용 기계 검사 기준이 그대로 적용되지 않는 문서는 report profile을 사용합니다.

```bash
python3 scripts/qa_html_translation.py \
  --output outputs/<document>_ko.html \
  --expect-title "<정확한 제목>" \
  --profile report \
  --strict-style
```

청크 Markdown을 긴 보고서 HTML로 조립할 때는 bundled renderer를 사용합니다.

```bash
python3 scripts/merge_chunks.py \
  --input-dir work/translation_chunks \
  --output work/combined_translation.md \
  --title "<문서 제목>"

python3 scripts/md_to_html.py \
  --input work/combined_translation.md \
  --output outputs/<document>_ko.html \
  --title "<정확한 제목>" \
  --date "YYYY.MM.DD." \
  --strip-line-regex "repeated footer pattern"
```

기존 레퍼런스와 동등한 품질을 목표로 할 때는 candidate HTML을 실제로 만든 뒤 equivalence evaluator를 돌립니다. 단순 unit test 통과나 구조 메트릭만으로 동등 품질을 주장하지 않습니다. `examples/translation/good/reference-quality-suite.md`에 기록된 Lululemon, PDD Holdings, YesAsia 기준 중 어떤 축을 만족했는지도 QA에 남겨야 합니다.

```bash
python3 scripts/evaluate_report_equivalence.py \
  --candidate outputs/<candidate>_ko.html \
  --reference /path/to/accepted_reference.html \
  --expect-title "<정확한 제목>" \
  --expect-pages <페이지수> \
  --require-core-counts-match
```

## 파일

- `SKILL.md`: Codex 스킬 정의와 작업 절차
- `agents/korean_translation_reviewer.md`: 독자 관점의 한국어 번역 개념 검수 프롬프트
- `agents/korean_report_reviewer.md`: 연차보고서/재무보고서 구조, 표, 법정 문구 검수 프롬프트
- `references/quality_benchmark.md`: 새 설치 환경에서도 같은 기준을 적용하기 위한 품질 벤치마크
- `scripts/qa_html_translation.py`: 최종 HTML 구조, source artifact, 숫자/단위, 명백한 반복 실패 템플릿을 검사하는 helper
- `scripts/evaluate_report_equivalence.py`: 레퍼런스 HTML과 candidate HTML의 보고서 구조/표/링크/artifact 동등성을 비교하는 helper
- `scripts/merge_chunks.py`, `scripts/md_to_html.py`: 청크 번역을 긴 보고서 HTML로 조립하는 helper
- `tests/`: 스킬 계약과 HTML QA helper 회귀 테스트
