"""Synthetic, reproducible examples; no real session data is imported."""
from datetime import datetime, timezone
import json
from pathlib import Path
from .config import Config

CODEX_ID = '11111111-2222-4333-8444-555555555555'
CLAUDE_ID = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'


def create(root, port=8766, timezone='Asia/Seoul', turns=24):
    root.mkdir(parents=True, exist_ok=True)
    (root / '.workspace-demo').touch()
    data = root / 'board'
    codex = root / 'codex/2026/01/01'
    claude = root / 'claude/demo-project'
    for folder in (data, codex, claude):
        folder.mkdir(parents=True, exist_ok=True)
    (root / 'BOARD.md').write_text('''# 작업 보드 · 데모

## 진행

### B-1 [website] 검색 화면 접근성 개선
담당: codex:''' + CODEX_ID + '''
키보드로 검색하고 결과를 확인할 수 있도록 입력 흐름을 다듬습니다.

## 검토 대기

### B-2 [docs] 첫 실행 안내 검토
담당: claude:''' + CLAUDE_ID + '''
요약:
- 설치 안내와 예제를 작성했습니다.
- 격리된 환경에서 확인했습니다.
- 검토 후 다음 작업을 정합니다.

## 할 일

### B-3 [website] 오류 화면 문구 정리
빈 결과와 연결 실패를 구분합니다.

## 완료

### B-4 [docs] 데모 데이터 준비
이 화면은 가상의 프로젝트와 대화만 보여줍니다.

## 기각

### B-5 [website] 불필요한 자동 새로고침
입력 중인 내용을 보존하는 방향을 택했습니다.
''', encoding='utf-8')
    (data / 'approvals.json').write_text(json.dumps([dict(title='검색 화면 확인', detail='키보드 이동과 빈 결과 화면을 확인해주세요.')], ensure_ascii=False), encoding='utf-8')
    (data / 'schedule.json').write_text(json.dumps([dict(date='2099-01-01', time='10:00', what='다음 작업 검토')], ensure_ascii=False), encoding='utf-8')
    stamp = '2026-01-01T03:00:00Z'
    records = [dict(type='turn_context', timestamp=stamp, payload=dict(model='Codex · demo'))]
    def message(role, text):
        return dict(type='response_item', timestamp=stamp, payload=dict(type='message', role=role, content=[dict(type='text', text=text)]))
    records += [message('user', '검색 화면에서 키보드로 결과를 선택할 수 있게 해주세요.')]
    for i in range(turns):
        records += [dict(type='response_item', timestamp=stamp, payload=dict(type='function_call', name='check_accessibility')),
                    dict(type='response_item', timestamp=stamp, payload=dict(type='function_call_output', output=f'검사 {i + 1}: 초점 순서와 레이블 확인'))]
    records += [message('assistant', '검색 결과를 방향키로 선택하고 Enter로 열 수 있게 했습니다.\n\n빈 결과에서는 다음 검색을 안내합니다. 키보드 검증도 통과했습니다.'),
                message('user', '좋아요. 연결 실패 화면도 같은 방식으로 확인해주세요.'),
                message('assistant', '연결이 끊기면 다시 시도 버튼을 표시하고 입력한 검색어를 유지하겠습니다.')]
    (codex / ('rollout-demo-' + CODEX_ID + '.jsonl')).write_text(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in records), encoding='utf-8')
    (claude / (CLAUDE_ID + '.jsonl')).write_text(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in [
        dict(type='user', timestamp=stamp, message=dict(content='첫 실행 안내를 확인해주세요.')),
        dict(type='assistant', timestamp=stamp, message=dict(model='Claude · demo', content=[dict(type='text', text='추가 설치 없이 한 명령으로 시작하는 흐름을 확인했습니다. 데모는 실제 세션을 읽지 않습니다.')]))]), encoding='utf-8')
    (root / 'chat.jsonl').write_text(json.dumps(dict(id='demo-message', ts=stamp, **{'from': 'claude:' + CLAUDE_ID, 'to': 'all'}, text='첫 실행 안내 검토가 끝났습니다. 작업 보드에서 확인해주세요.'), ensure_ascii=False) + '\n', encoding='utf-8')
    return Config(data, root / 'BOARD.md', root / 'codex', root / 'claude', root / 'chat.jsonl', Path(__file__).with_name('demo_chat.py'), port, timezone)
