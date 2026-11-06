'use strict';
const $ = id => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]')?.content || (typeof TOKEN !== 'undefined' ? TOKEN : '');
const node = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
let sessionRows = [], detailId = '', detailBefore = null, detailMessages = [], detailVersion = 0;
let chatBefore = null, chatPages = [], chatExpanded = false, chatLatestEnd = null, sending = false, polling = false, chatLoading = false;
let draftRevision = 0;
async function api(path) { const r = await fetch(path, {cache: 'no-store'}); if (!r.ok) throw new Error('조회 실패 (' + r.status + ')'); return r.json(); }
function showError(e) { $('connection').textContent = '연결을 확인하세요 · ' + e.message; $('retry').hidden = false; }
function connected() { $('connection').textContent = '연결됨 · 세션 9초 / 채팅 3초 갱신'; $('retry').hidden = true; }
function message(m) {
  const e = node('article', undefined, 'message ' + (m.role || 'chat'));
  const h = node('header'); h.append(node('b', m.role === 'user' ? '사용자' : m.role === 'assistant' ? '어시스턴트' : m.from === 'codex:board-operator' ? '운영자 대시보드' : m.from || '메시지'), node('time', m.ts)); e.append(h);
  if (m.to) e.append(node('div', '→ ' + m.to, 'route'));
  if (m.reply_target) e.append(node('div', '답장 → ' + m.reply_target, 'route'));
  e.append(node('p', m.text)); return e;
}
function conversationNodes(messages) {
  const f = document.createDocumentFragment(); let tools = [];
  function flush() {
    if (!tools.length) return;
    const group = node('details', undefined, 'tool-group');
    group.append(node('summary', '도구 활동 ' + tools.length + '건 · ' + (tools[0].text.startsWith('호출: ') ? tools[0].text.split('\n')[0] : '출력 보기')));
    // Allocate the potentially large output DOM only after an explicit expansion.
    const items = tools;
    group.addEventListener('toggle', () => {
      if (group.open && group.childElementCount === 1) {
        const body = node('div', undefined, 'tool-output');
        for (const m of items) body.append(node('time', m.ts), node('pre', m.text));
        group.append(body);
      }
    });
    f.append(group); tools = [];
  }
  for (const m of messages) { if (m.role === 'tool') tools.push(m); else { flush(); f.append(message(m)); } } flush(); return f;
}
function drawSessions() {
  const active = document.activeElement;
  const focusedHref = $('sessions').contains(active) ? active.closest('.session-card')?.getAttribute('href') : null;
  const rows = $('session-filter').value === 'running' ? sessionRows.filter(r => r.running) : sessionRows;
  $('session-count').textContent = rows.length + '개'; $('sessions').replaceChildren(); $('sessions').setAttribute('aria-busy', 'false');
  for (const r of rows) {
    const a = node('a', undefined, 'session-card'); a.href = '#session=' + encodeURIComponent(r.id);
    const h = node('header'); h.append(node('span', r.client === 'codex' ? 'Codex' : 'Claude', 'client'), node('span', r.running ? '프로세스 확인' : '실행 미확인', 'badge ' + (r.running ? 'b-run' : 'b-idle')));
    a.append(h, node('code', r.id), node('div', r.model, 'model'), node('p', r.cards.length ? r.cards.map(c => c.id + ' · ' + c.title + ' (' + c.column + ')').join('\n') : '맡은 카드 없음', 'assignment'), node('p', r.preview || '대화를 열어 세션 기록을 확인하세요.'), node('time', r.last_activity_kst));
    a.title = r.basis; a.setAttribute('aria-label', r.client + ' ' + r.id + ' 대화 열기'); $('sessions').append(a);
  }
  if (focusedHref) { const replacement = [...$('sessions').querySelectorAll('.session-card')].find(a => a.getAttribute('href') === focusedHref); (replacement || $('session-filter')).focus({preventScroll: true}); }
  if (!rows.length) $('sessions').append(node('p', $('session-filter').value === 'running' ? '실행이 확인된 세션이 없습니다. 최근 기록 전체를 선택해 보세요.' : '최근 세션 기록이 없습니다. CLI에서 대화를 시작하면 여기에 나타납니다.', 'empty'));
}
async function refreshSessions() {
  sessionRows = (await api('/api/sessions')).sessions; drawSessions(); const old = $('recipient').value;
  const options = [node('option', '전체 · 방송')]; options[0].value = 'all';
  for (const r of sessionRows) { const o = node('option', r.client + ' · ' + (r.cards[0]?.id || r.id.slice(-12)) + ' · ' + (r.running ? '프로세스 확인' : '실행 미확인')); o.value = r.id; options.push(o); }
  if (old && !options.some(o => o.value === old)) { const o = node('option', '목록에서 미확인 · ' + old); o.value = old; options.push(o); }
  $('recipient').replaceChildren(...options); if (old) $('recipient').value = old;
}
async function loadDetail(older = false) {
  const id = detailId, version = ++detailVersion;
  $('older').disabled = true;
  try {
    const data = await api('/api/session?id=' + encodeURIComponent(id) + (older && detailBefore ? '&before=' + detailBefore : ''));
    if (id !== detailId || version !== detailVersion) return;
    detailBefore = data.before; $('older').hidden = !detailBefore; $('detail-note').textContent = data.note;
    detailMessages = older ? [...data.messages, ...detailMessages] : data.messages;
    $('messages').replaceChildren(conversationNodes(detailMessages));
    if (!detailMessages.length) $('messages').append(node('p', '이 구간에는 표시할 대화가 없습니다. 이전 기록을 확인하세요.', 'empty'));
  } catch (err) {
    if (version === detailVersion && id === detailId) {
      if (!older) {
        const retry = node('button', '대화 다시 불러오기'); retry.onclick = () => loadDetail().catch(showError);
        $('messages').replaceChildren(node('p', '대화 기록을 읽지 못했습니다.', 'empty'), retry);
      }
      throw err;
    }
  } finally { if (version === detailVersion) $('older').disabled = false; }
}
function mergeChatPages(pages) {
  const merged = [];
  for (const page of [...pages].sort((a, b) => a.start - b.start || a.end - b.end)) {
    const last = merged.at(-1);
    if (!last || page.start > last.end) { merged.push({...page, messages: [...page.messages]}); continue; }
    const seen = new Set(last.messages.map(m => m.id));
    last.messages.push(...page.messages.filter(m => !seen.has(m.id)));
    last.end = Math.max(last.end, page.end);
  }
  return merged;
}
function drawChat() {
  const box = $('chat-messages'), top = box.scrollTop, bottom = box.scrollHeight - top - box.clientHeight < 80;
  const focusedGap = box.contains(document.activeElement) && document.activeElement.classList.contains('chat-gap');
  const f = document.createDocumentFragment(), seen = new Set();
  for (let i = 0; i < chatPages.length; i++) {
    const page = chatPages[i];
    if (i && page.start > chatPages[i - 1].end) {
      const gap = node('button', '이 사이의 메시지 더 보기', 'chat-gap');
      gap.onclick = () => refreshChat(true, page.start).catch(showError); f.append(gap);
    }
    for (const m of page.messages) { if (seen.has(m.id)) continue; seen.add(m.id); f.append(message(m)); }
  }
  if (!seen.size) f.append(node('p', '아직 메시지가 없습니다. 첫 메시지를 남겨보세요.', 'empty'));
  box.replaceChildren(f); box.scrollTop = bottom ? box.scrollHeight : top;
  if (focusedGap) (box.querySelector('.chat-gap') || box).focus({preventScroll: true});
}
async function refreshChat(older = false, gapBefore = null) {
  if (chatLoading) return false; chatLoading = true; $('chat-older').disabled = true;
  const box = $('chat-messages'), height = box.scrollHeight, top = box.scrollTop;
  try {
    const before = gapBefore ?? (older ? chatBefore : null);
    const data = await api('/api/chat' + (before !== null ? '?before=' + before : ''));
    const page = {start: data.before || 0, end: data.end, messages: data.messages};
    if (!older && chatLatestEnd === data.end && chatPages.length) return true;
    if (older) chatExpanded = true;
    else {
      if (chatLatestEnd !== null && data.end < chatLatestEnd) { chatPages = []; chatExpanded = false; }
      chatLatestEnd = data.end;
    }
    chatPages = chatExpanded ? mergeChatPages([...chatPages, page]) : [page];
    chatBefore = chatPages[0].start || null;
    $('chat-older').hidden = !chatBefore; drawChat();
    if (older && gapBefore === null) box.scrollTop = top + box.scrollHeight - height;
    return true;
  } finally { chatLoading = false; $('chat-older').disabled = false; }
}
async function refreshBoard() {
  const board = $('board-view');
  const interacting = () => board.contains(document.activeElement) && document.activeElement.matches('button,input,textarea,select,a,summary,[contenteditable=true]');
  if (interacting()) return false;
  const r = await fetch('/', {cache: 'no-store'}); if (!r.ok) throw new Error('보드 조회 실패 (' + r.status + ')');
  const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
  const fresh = doc.getElementById('board-view'); if (!fresh) throw new Error('보드를 읽지 못했습니다.');
  if (interacting()) return false;
  const focused = board.contains(document.activeElement) && document.activeElement.tagName === 'H2';
  const regionFocused = document.activeElement === board.querySelector('.kanban');
  const scroll = board.querySelector('.kanban')?.scrollLeft || 0;
  board.replaceChildren(...fresh.childNodes);
  const region = board.querySelector('.kanban'); if (region) region.scrollLeft = scroll;
  if (focused) board.querySelector('h2')?.focus({preventScroll: true});
  if (regionFocused) region?.focus({preventScroll: true});
  return true;
}
function route(moveFocus = false) {
  const hash = location.hash.slice(1), detail = hash.startsWith('session='), previousId = detailId;
  try { detailId = detail ? decodeURIComponent(hash.slice(8)) : ''; } catch { detailId = ''; showError(new Error('잘못된 세션 주소')); return; }
  if (detail && detailId !== previousId) { detailMessages = []; detailBefore = null; $('older').hidden = true; }
  const tab = detail ? 'detail' : ['sessions', 'chat', 'board'].includes(hash) ? hash : 'sessions';
  for (const id of ['sessions', 'detail', 'chat', 'board']) $(id + '-view').hidden = id !== tab;
  for (const a of document.querySelectorAll('[data-tab]')) { if (a.dataset.tab === (detail ? 'sessions' : tab)) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
  if (detail) { $('detail-title').textContent = detailId; $('messages').replaceChildren(node('p', '대화를 불러오는 중…', 'empty')); loadDetail().catch(showError); }
  if (tab === 'chat') refreshChat().catch(showError);
  if (moveFocus) $(tab + '-view').querySelector('h2')?.focus({preventScroll: true});
}
// Also works with the previous local server while its existing listener drains.
if (!$('retry')) { const b = node('button', '다시 연결'); b.id = 'retry'; b.hidden = true; $('connection').after(b); }
if (!$('theme')) { const b = node('button', '테마: 자동'); b.id = 'theme'; document.querySelector('.dashboard-head').append(b); }
let theme = 'auto'; try { theme = localStorage.getItem('agent-workspace-theme') || 'auto'; } catch {}
function applyTheme() { if (!['auto', 'light', 'dark'].includes(theme)) theme = 'auto'; document.documentElement.dataset.theme = theme; $('theme').textContent = '테마: ' + ({auto: '자동', light: '밝게', dark: '어둡게'}[theme]); }
$('theme').onclick = () => { theme = {auto: 'light', light: 'dark', dark: 'auto'}[theme]; applyTheme(); try { localStorage.setItem('agent-workspace-theme', theme); } catch {} }; applyTheme();
$('session-filter').addEventListener('change', drawSessions);
$('older').onclick = () => loadDetail(true).catch(showError);
$('chat-older').onclick = () => refreshChat(true).catch(showError);
$('detail-chat').onclick = () => { const id = detailId; location.hash = 'chat'; if (![...$('recipient').options].some(o => o.value === id)) { const o = node('option', '목록에서 미확인 · ' + id); o.value = id; $('recipient').append(o); } $('recipient').value = id; setTimeout(() => $('chat-text').focus(), 0); };
$('retry').onclick = () => { refreshSessions().then(connected).catch(showError); if (!$('detail-view').hidden) loadDetail().catch(showError); if (!$('chat-view').hidden) refreshChat().catch(showError); };
$('chat-form').onsubmit = async e => {
  e.preventDefault(); if (sending) return; sending = true; const submittedText = $('chat-text').value, submittedRevision = draftRevision; const button = e.target.querySelector('button'); button.disabled = true; $('send-status').textContent = '전송 확인 중…';
  try {
    const r = await fetch('/api/chat/send', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: csrf, to: $('recipient').value, text: submittedText})});
    const j = await r.json(), delivery = Array.isArray(j.receipt?.delivery) ? j.receipt.delivery : [], reasons = delivery.map(d => d?.reason).filter(Boolean).join(' · ');
    $('send-status').textContent = j.stored ? '채팅방에 저장했습니다. 모델 수신 여부는 미확인입니다.' + (reasons ? ' ' + reasons : '') : j.error || reasons || '전송을 거부했습니다.';
    if (j.stored && $('chat-text').value === submittedText && draftRevision === submittedRevision) $('chat-text').value = ''; await refreshChat();
  } catch { $('send-status').textContent = '결과를 확인하지 못했습니다. 중복 전송 전에 내역을 확인하세요.'; }
  finally { sending = false; button.disabled = false; }
};
$('chat-text').addEventListener('input', () => { draftRevision++; });
document.addEventListener('click', async e => {
  const b = e.target.closest('button.done'); if (!b) return; e.stopImmediatePropagation();
  if (!confirm((b.dataset.label || b.dataset.key) + ' 을(를) 완료로 옮길까요?')) return; b.disabled = true;
  try {
    const r = await fetch('/api/done', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({kind: b.dataset.kind, id: b.dataset.key, title: b.dataset.key, approval_id: b.dataset.kind === 'approval' ? b.dataset.key : undefined, token: csrf})});
    const j = await r.json(); if (!r.ok) throw new Error(j.error || '저장 실패 (' + r.status + ')');
    // Move focus outside the replaced board, then restore it to its heading.
    document.querySelector('[data-tab="board"]').focus(); await refreshBoard(); $('board-view').querySelector('h2')?.focus();
  } catch (err) { showError(err); b.disabled = false; }
}, true);
window.addEventListener('hashchange', () => route(true));
if (document.querySelector('meta[name=workspace-mode]')?.content === 'demo') { $('session-filter').value = 'recent'; document.querySelector('.local-indicator').textContent = '데모 · 가상 프로젝트'; }
route(); refreshSessions().then(connected).catch(showError);
let tick = 0;
setInterval(async () => {
  if (polling || document.hidden) return; polling = true;
  try {
    let refreshed = false;
    if (++tick % 3 === 0) { await refreshSessions(); refreshed = true; }
    if (!$('chat-view').hidden) refreshed = await refreshChat() || refreshed;
    if (!$('board-view').hidden && tick % 10 === 0) refreshed = await refreshBoard() || refreshed;
    if (refreshed) connected();
  }
  catch (e) { showError(e); } finally { polling = false; }
}, 3000);
