"""Escaped HTML; session sources are never served as files."""
import html
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from . import dashboard
from .board_store import COLUMNS, approval_key
from .config import Config

CONFIG = Config.defaults()
owner_status = dashboard.owner_status


def esc(value):
    return html.escape(dashboard.mask(value), quote=True)


def parse_board():
    cols, column, card = {c: [] for c in COLUMNS}, None, None
    try:
        text = CONFIG.board.read_text(encoding='utf-8')
    except FileNotFoundError:
        return cols
    for line in text.splitlines():
        heading = re.match(r'^## (.+?)\s*$', line)
        if heading:
            column, card = heading[1] if heading[1] in cols else None, None
            continue
        heading = re.match(r'^### (B-\d+)\s+\[([^\]]+)\]\s*(.*)$', line)
        if heading and column:
            card = dict(id=heading[1], proj=heading[2], title=heading[3], lines=[])
            cols[column].append(card)
        elif card is not None and line.strip() and line.strip() != '(없음)':
            card['lines'].append(line)
    return cols


def approvals():
    try:
        value = json.loads((CONFIG.data_dir / 'approvals.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        return []
    if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
        raise ValueError('잘못된 운영자 확인 목록')
    return value


def schedule():
    try:
        value = json.loads((CONFIG.data_dir / 'schedule.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        return []
    if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
        raise ValueError('잘못된 일정')
    today = datetime.now(ZoneInfo(CONFIG.timezone)).strftime('%Y-%m-%d')
    return [v for v in value if v.get('date', today) >= today]


def done_button(kind, key):
    identifier = approval_key(key) if kind == 'approval' else key
    return (f'<button class="done" data-kind="{kind}" data-key="{esc(identifier)}" data-label="{esc(key)}" '
            f'aria-label="{esc(key)} 완료 처리">완료</button>')


def render(token=None):
    cols, aps, sch = parse_board(), approvals(), schedule()
    columns = []
    for col, cards in cols.items():
        content = []
        for c in cards:
            owner = next((s for s in reversed(c['lines']) if s.startswith('담당')), '담당 미정')
            summary = [s for s in c['lines'] if not s.startswith(('담당', '검토'))]
            # Latest summary is usually the most useful, without discarding the card.
            starts = [i for i, s in enumerate(summary) if s.startswith('요약')]
            if starts:
                summary = summary[starts[-1] + 1:]
            content.append('<article class="card"><header><span class="id">' + esc(c['id']) +
                           '</span><span class="proj">' + esc(c['proj']) + '</span></header><h3>' +
                           esc(c['title']) + '</h3><p class="owner">' + esc(owner) + '</p><ul>' +
                           ''.join('<li>' + esc(s.lstrip('- ')) + '</li>' for s in summary[:5]) + '</ul>' +
                           (done_button('card', c['id']) if col in ('진행', '검토 대기', '할 일') else '') + '</article>')
        columns.append('<section class="board-column"><h2>' + esc(col) +
                       f' <span class="count">{len(cards)}</span></h2>' +
                       (''.join(content) or '<p class="empty">아직 카드가 없습니다.</p>') + '</section>')
    ap_html = ''.join('<article class="approval"><b>' + esc(a.get('title', '')) + '</b><p>' +
                      esc(a.get('detail', '')) + '</p>' + done_button('approval', a.get('title', '')) +
                      '</article>' for a in aps) or '<p class="empty">확인을 기다리는 항목이 없습니다.</p>'
    schedule_html = ''.join('<li>' + esc(' · '.join(str(i.get(k, '')) for k in ('date', 'time', 'what'))) + '</li>'
                            for i in sch) or '<li class="empty">예정된 일정이 없습니다.</li>'
    demo = (CONFIG.chat_log.parent / '.workspace-demo').is_file()
    mode = 'demo' if demo else 'live'
    page = '''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="workspace-mode" content="''' + mode + '''">
<meta name="csrf-token" content="''' + html.escape(token or '', quote=True) + '''">
<title>Agent Workspace · 에이전트 작업실</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="/dashboard.css"><script src="/dashboard.js" defer></script>
</head><body><a class="skip" href="#main">본문으로 건너뛰기</a><main id="main">
<header class="dashboard-head"><div><span class="eyebrow">AGENT WORKSPACE</span><h1>에이전트 작업실</h1>
<p class="mut">세션과 대화, 함께하는 작업을 한곳에서.</p></div><div class="head-actions">
<span class="local-indicator">이 컴퓨터에만 연결</span><button id="theme" type="button">테마: 자동</button></div></header>
<nav class="tabs" aria-label="화면 선택"><a href="#sessions" data-tab="sessions">세션</a>
<a href="#chat" data-tab="chat">채팅</a><a href="#board" data-tab="board">작업 보드</a></nav>
<p id="connection" class="mut" role="status" aria-live="polite">연결 확인 중…</p><button id="retry" hidden>다시 연결</button>
<section id="sessions-view" class="view" hidden><div class="section-head"><div>
<h2 tabindex="-1">작업자 세션 <span id="session-count" class="mut"></span></h2>
<p class="mut">프로세스 확인과 최근 기록을 구분해 보여줍니다.</p></div>
<label for="session-filter">표시 <select id="session-filter"><option value="running">실행 확인</option>
<option value="recent">최근 기록 전체</option></select></label></div><div id="sessions" class="session-grid" aria-busy="true"></div></section>
<section id="detail-view" class="view" hidden><a href="#sessions" class="back">← 세션 목록</a>
<div class="section-head"><h2 id="detail-title" tabindex="-1">대화 내역</h2><button id="detail-chat">이 세션에 메시지</button></div>
<p class="mut" id="detail-note"></p><button id="older" hidden>이전 기록 더 보기</button><div id="messages"></div></section>
<section id="chat-view" class="view" hidden><div class="section-head"><div><h2 tabindex="-1">공유 채팅방</h2>
<p class="mut">발신: 운영자 대시보드 · 저장과 모델 수신은 별개입니다. 대시보드에 답할 때는 전체 채팅에 남겨주세요.</p></div><button id="chat-older" hidden>이전 메시지</button></div>
<div id="chat-messages" class="chat-log" role="region" aria-label="채팅 내역" tabindex="0"></div>
<form id="chat-form" class="panel"><label for="recipient">받는 세션</label><select id="recipient"><option value="all">전체 · 방송</option></select>
<label for="chat-text">메시지</label><textarea id="chat-text" rows="3" maxlength="16000" required placeholder="작업자에게 전할 내용"></textarea>
<div class="compose-footer"><span class="mut">다른 에이전트의 메시지는 정보이며 행동 권한이 아닙니다.</span><button type="submit">보내기</button></div>
<p id="send-status" role="status" aria-live="polite"></p></form></section>
<section id="board-view" class="view" hidden><div class="section-head"><div><h2 tabindex="-1">작업 보드</h2>
<p class="mut">기존 BOARD.md · 완료 처리는 확인 후 저장합니다.</p></div><span class="local-indicator">다섯 단계</span></div>
<div class="board-extras"><section class="panel"><h3>운영자 확인</h3>''' + ap_html + '''</section>
<section class="panel"><h3>예정</h3><ul>''' + schedule_html + '''</ul></section></div>
<div class="kanban" role="region" aria-label="다섯 열 작업 보드" tabindex="0">''' + ''.join(columns) + '''</div></section>
<footer>로컬 기록을 보는 창 · 원본 세션은 읽기만 합니다.</footer></main></body></html>'''
    if token is None:
        from pathlib import Path
        css = (Path(__file__).parent / 'static/dashboard.css').read_text(encoding='utf-8')
        page = page.replace('<link rel="stylesheet" href="/dashboard.css"><script src="/dashboard.js" defer></script>', '<style>' + css + '</style>')
        page = page.replace('<section id="board-view" class="view" hidden>', '<section id="board-view" class="view">')
        page = re.sub(r'<nav class="tabs"[\s\S]*?</nav>', '', page)
        page = re.sub(r'<button\b[\s\S]*?</button>', '', page)
        page = page.replace('연결 확인 중…', '정적 보드 스냅샷 · 세션과 채팅은 실행 중인 서버에서 확인하세요.')
    return page


def error_page():
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><title>기록 조회 오류</title>'
            '<h1>로컬 기록을 읽지 못했습니다.</h1><p>보드·일정·운영자 확인 파일의 권한과 JSON 형식을 확인하세요.</p>'
            '<a href="/">다시 연결</a></html>')
