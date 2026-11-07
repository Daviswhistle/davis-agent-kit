param(
    [string]$BaseUrl = 'http://localhost:8766',
    [string]$FixtureUrl = 'http://localhost:8767',
    [string]$OutputDirectory = (Join-Path $env:TEMP 'agent-workspace-browser'),
    [int]$DebugPort = 9241,
    [string]$StaticSnapshotPath = '',
    [string]$ChromePath = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
)
$ErrorActionPreference = 'Stop'
$out = $OutputDirectory
New-Item -ItemType Directory -Force $out | Out-Null
$profile = Join-Path $out ('profile-' + [Guid]::NewGuid().ToString())
$chrome = Start-Process -FilePath $ChromePath -ArgumentList @('--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-extensions','--disable-sync',"--remote-debugging-port=$DebugPort", "--user-data-dir=$profile",'about:blank') -PassThru
$ws = $null
$checks = @{}
try {
    $targets = $null
    for($i=0;$i -lt 50;$i++) {
        try { $targets = Invoke-RestMethod "http://127.0.0.1:$DebugPort/json/list"; break } catch { Start-Sleep -Milliseconds 200 }
    }
    $target = $targets | Where-Object {$_.type -eq 'page'} | Select-Object -First 1
    if(-not $target) {throw 'Chrome target unavailable'}
    $ws = New-Object System.Net.WebSockets.ClientWebSocket
    $ws.ConnectAsync([Uri]$target.webSocketDebuggerUrl,[Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $script:seq = 0
    function Rpc($method,$params) {
        $script:seq++
        $id = $script:seq
        $raw = [Text.Encoding]::UTF8.GetBytes((@{id=$id;method=$method;params=$params} | ConvertTo-Json -Depth 40 -Compress))
        $ws.SendAsync([ArraySegment[byte]]::new($raw),[Net.WebSockets.WebSocketMessageType]::Text,$true,[Threading.CancellationToken]::None).GetAwaiter().GetResult()
        while($true) {
            $stream = New-Object IO.MemoryStream
            do {
                $buffer = New-Object byte[] 65536
                $pending = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer),[Threading.CancellationToken]::None)
                if(-not $pending.Wait(20000)){throw 'CDP receive timed out'}
                $part = $pending.Result
                $stream.Write($buffer,0,$part.Count)
            } while(-not $part.EndOfMessage)
            $reply = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
            $stream.Dispose()
            if($reply.id -eq $id) {
                if($reply.error){throw ('CDP error: ' + $method)}
                return $reply.result
            }
        }
    }
    function Js($expression) {
        $r = Rpc 'Runtime.evaluate' @{expression=$expression;returnByValue=$true;awaitPromise=$true}
        if($r.exceptionDetails){throw ('Browser JavaScript exception: ' + $expression + ' : ' + $r.exceptionDetails.exception.description)}
        return $r.result.value
    }
    function Wait-Js($expression) {
        for($j=0;$j -lt 100;$j++) {if(Js $expression){return}; Start-Sleep -Milliseconds 200}
        throw ('Browser condition timed out: ' + $expression)
    }
    function Viewport($width,$height) {Rpc 'Emulation.setDeviceMetricsOverride' @{width=$width;height=$height;deviceScaleFactor=1;mobile=$false} | Out-Null}
    function Navigate($url,$condition) {Rpc 'Page.navigate' @{url=$url} | Out-Null; Wait-Js $condition}
    function Shot($name) {
        if(-not (Js "document.querySelector('meta[name=workspace-mode]')?.content==='demo'")){throw 'Refusing screenshot: the page must be an isolated demo.'}
        $r = Rpc 'Page.captureScreenshot' @{format='png';captureBeyondViewport=$false}
        [IO.File]::WriteAllBytes((Join-Path $out $name),[Convert]::FromBase64String($r.data))
    }
    Rpc 'Page.enable' @{} | Out-Null
    Viewport 1400 1000
    Navigate "$BaseUrl/#sessions" "!!document.querySelector('meta[name=workspace-mode]')"
    $checks.demo_only = Js "document.querySelector('meta[name=workspace-mode]').content==='demo' && document.querySelector('.local-indicator').textContent.includes('가상')"
    if(-not $checks.demo_only){throw 'Refusing screenshots: BaseUrl must be an isolated demo.'}
    Wait-Js "document.querySelectorAll('.session-card').length===2"
    foreach($width in @(390,768,1400,1920)) {
        Viewport $width 1000
        $checks["no_overflow_$width"] = Js "document.documentElement.scrollWidth <= $width"
        Shot "sessions-$width.png"
    }
    Viewport 1400 1000
    Js "document.getElementById('theme').click();document.getElementById('theme').click()" | Out-Null
    $checks.dark_mode = Js "document.documentElement.dataset.theme==='dark'"
    Shot 'sessions-dark.png'
    Navigate "$BaseUrl/#sessions" "document.querySelectorAll('.session-card').length===2"
    $checks.theme_persists = Js "document.documentElement.dataset.theme==='dark'"
    Js "document.getElementById('theme').click();document.getElementById('theme').click()" | Out-Null
    $checks.light_mode = Js "document.documentElement.dataset.theme==='light'"
    Js "document.querySelector('.skip').focus()" | Out-Null
    Rpc 'Input.dispatchKeyEvent' @{type='keyDown';key='Tab';code='Tab';windowsVirtualKeyCode=9} | Out-Null
    Rpc 'Input.dispatchKeyEvent' @{type='keyUp';key='Tab';code='Tab';windowsVirtualKeyCode=9} | Out-Null
    $checks.keyboard_tab = Js "document.activeElement.id==='theme'"
    $checks.labels = Js "[...document.querySelectorAll('select,textarea')].every(e=>document.querySelector('label[for='+e.id+']'))"
    Js "(async()=>{document.querySelector('.session-card').focus();window.focusedSessionHref=document.activeElement.getAttribute('href');await refreshSessions()})()" | Out-Null
    $checks.session_card_focus_survives_poll = Js "document.activeElement.classList.contains('session-card') && document.activeElement.getAttribute('href')===window.focusedSessionHref"
    Rpc 'Input.dispatchKeyEvent' @{type='keyDown';key='Enter';code='Enter';windowsVirtualKeyCode=13} | Out-Null
    Rpc 'Input.dispatchKeyEvent' @{type='keyUp';key='Enter';code='Enter';windowsVirtualKeyCode=13} | Out-Null
    Wait-Js "!document.getElementById('detail-view').hidden"
    $checks.enter_opens_focused_session = $true
    Js "location.hash='session=codex%3A11111111-2222-4333-8444-555555555555'" | Out-Null
    Wait-Js "document.querySelectorAll('#messages .message').length===4"
    $checks.grouped_tools = Js "document.querySelectorAll('#messages .tool-group').length===1 && document.querySelectorAll('#messages pre').length===0"
    Shot 'conversation.png'
    Js "document.querySelector('#messages summary').click()" | Out-Null
    Wait-Js "document.querySelectorAll('#messages pre').length>0"
    $checks.tools_expand_lazily = Js "document.querySelector('#messages details').open && document.querySelectorAll('#messages pre').length===48"
    Js "document.getElementById('detail-chat').click()" | Out-Null
    Wait-Js "!document.getElementById('chat-view').hidden"
    $checks.recipient_selected = Js "document.getElementById('recipient').value==='codex:11111111-2222-4333-8444-555555555555'"
    Js "(async()=>{window.inventoryFetch=window.fetch;window.fetch=async(path,opts)=>path==='/api/sessions'?new Response(JSON.stringify({sessions:[]}),{status:200}):window.inventoryFetch(path,opts);await refreshSessions()})()" | Out-Null
    $checks.recipient_preserved_when_missing = Js "document.getElementById('recipient').value==='codex:11111111-2222-4333-8444-555555555555'"
    Js "(async()=>{window.fetch=window.inventoryFetch;await refreshSessions()})()" | Out-Null
    Viewport 1400 1300
    Shot 'chat.png'
    Viewport 1400 1000
    Js "location.hash='board'" | Out-Null
    Wait-Js "!document.getElementById('board-view').hidden"
    $checks.five_columns = Js "document.querySelectorAll('.board-column').length===5"
    Js "(async()=>{window.boardFetch=window.fetch;window.boardRequests=0;window.fetch=(path,opts)=>{if(path==='/')window.boardRequests++;return window.boardFetch(path,opts)};await refreshBoard()})()" | Out-Null
    $checks.board_updates_with_heading_focus = Js "window.boardRequests===1 && document.activeElement.tagName==='H2'"
    Js "window.fetch=window.boardFetch" | Out-Null
    Shot 'board.png'
    Viewport 390 1000
    $checks.board_mobile_no_overflow = Js "document.documentElement.scrollWidth<=390"
    Shot 'board-mobile.png'
    Viewport 1400 1000
    Navigate "$FixtureUrl/#session=codex%3A11111111-2222-4333-8444-555555555555" "!!document.querySelector('meta[name=workspace-mode]')"
    $checks.fixture_demo_only = Js "document.querySelector('meta[name=workspace-mode]').content==='demo'"
    if(-not $checks.fixture_demo_only){throw 'Refusing writes: FixtureUrl must be an isolated demo.'}
    Wait-Js "document.querySelectorAll('#messages .message').length>=3"
    $checks.redacted_dom = Js "!document.getElementById('messages').textContent.includes('exampleCredential') && document.getElementById('messages').textContent.includes('[가림]')"
    $checks.authorization_header_fully_redacted = Js "!document.getElementById('messages').textContent.includes('z'.repeat(24))"
    $checks.xss_as_text = Js "document.querySelectorAll('#messages img').length===0 && document.getElementById('messages').textContent.includes('<img')"
    $checks.large_page_bounded = Js "document.querySelectorAll('#messages .message').length<=120 && document.querySelectorAll('#messages details').length<=3 && document.querySelectorAll('#messages pre').length===0 && !document.getElementById('older').hidden"
    $checks.detail_dom_nodes = Js "document.getElementById('messages').querySelectorAll('*').length"
    Js "document.getElementById('older').click()" | Out-Null
    Wait-Js "!document.getElementById('older').disabled"
    $checks.older_still_grouped = Js "document.querySelectorAll('#messages details').length<=3"
    Js "document.getElementById('detail-chat').click()" | Out-Null
    Wait-Js "!document.getElementById('chat-view').hidden"
    Js "document.getElementById('recipient').value='all';document.getElementById('chat-text').value='token=exampleCredential';document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "document.getElementById('send-status').textContent.includes('거부')"
    $checks.secret_rejected = Js "!document.getElementById('chat-messages').textContent.includes('exampleCredential') && document.getElementById('chat-text').value==='token=exampleCredential'"
    $marker = 'browser demo ' + [Guid]::NewGuid().ToString()
    $markerJson = $marker | ConvertTo-Json -Compress
    Js "document.getElementById('chat-text').value=$markerJson;document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "document.getElementById('chat-messages').textContent.includes($markerJson) && document.getElementById('chat-text').value===''"
    $checks.chat_send_poll = $true
    $checks.reply_route_in_room = Js "chatPages.flatMap(p=>p.messages).some(m=>m.text===$markerJson && m.reply_target==='all')"
    Js "document.getElementById('chat-text').value='Report: /workspace/research-20261107/output/REPORT.md';document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "!sending && document.getElementById('chat-text').value==='' && chatPages.flatMap(p=>p.messages).some(m=>m.text==='Report: [가림].md')"
    $checks.normal_report_path_sent = $true
    Js "window.optionalReceiptFetch=window.fetch;window.optionalReceiptDelivery={ignored:'optional metadata'};window.fetch=(path,opts)=>path==='/api/chat/send'?Promise.resolve(new Response(JSON.stringify({ok:true,stored:true,receipt:{stored:true,delivery:window.optionalReceiptDelivery}}),{status:200})):window.optionalReceiptFetch(path,opts);document.getElementById('chat-text').value='optional receipt object';document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "!sending && document.getElementById('chat-text').value===''"
    $optionalObjectStored = Js "document.getElementById('send-status').textContent.includes('저장했습니다')"
    Js "window.optionalReceiptDelivery=[null,{reason:'custom receipt'}];document.getElementById('chat-text').value='optional receipt null row';document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "!sending && document.getElementById('chat-text').value===''"
    $checks.optional_delivery_metadata_keeps_stored_confirmation = $optionalObjectStored -and (Js "document.getElementById('send-status').textContent.includes('custom receipt')")
    Js "window.fetch=window.optionalReceiptFetch" | Out-Null
    Js "window.draftFetch=window.fetch;window.fetch=(path,opts)=>path==='/api/chat/send'?new Promise(resolve=>{window.finishPendingSend=()=>window.draftFetch(path,opts).then(resolve)}):window.draftFetch(path,opts);document.getElementById('chat-text').value='first isolated draft';document.getElementById('chat-form').requestSubmit();document.getElementById('chat-text').value='second unsent draft';window.finishPendingSend()" | Out-Null
    Wait-Js "!sending && document.getElementById('chat-messages').textContent.includes('first isolated draft')"
    $checks.unsent_draft_survives_receipt = Js "document.getElementById('chat-text').value==='second unsent draft'"
    Js "window.fetch=window.draftFetch;document.getElementById('chat-text').value=''" | Out-Null
    Js "window.sameDraftFetch=window.fetch;window.fetch=(path,opts)=>path==='/api/chat/send'?new Promise(resolve=>{window.finishSameDraft=()=>window.sameDraftFetch(path,opts).then(resolve)}):window.sameDraftFetch(path,opts);document.getElementById('chat-text').value='identical isolated draft';document.getElementById('chat-form').requestSubmit();document.getElementById('chat-text').value='';document.getElementById('chat-text').dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('chat-text').value='identical isolated draft';document.getElementById('chat-text').dispatchEvent(new Event('input',{bubbles:true}));window.finishSameDraft()" | Out-Null
    Wait-Js "!sending && document.getElementById('chat-messages').textContent.includes('identical isolated draft')"
    $checks.retyped_identical_draft_survives_receipt = Js "document.getElementById('chat-text').value==='identical isolated draft'"
    Js "window.fetch=window.sameDraftFetch;document.getElementById('chat-text').value=''" | Out-Null
    Js "window.csrfFetch=window.fetch;window.csrfPosts=0;window.fetch=(path,opts)=>{if(path==='/api/chat/send')window.csrfPosts++;return window.csrfFetch(path,opts)};csrf='expired-fixture';document.getElementById('chat-text').value='restart preserved draft';document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "!sending && document.getElementById('send-status').textContent.includes('다시 시도')"
    $checks.expired_chat_preserves_draft_without_replay = Js "window.csrfPosts===1 && csrf!=='expired-fixture' && document.getElementById('chat-text').value==='restart preserved draft' && !chatPages.flatMap(p=>p.messages).some(m=>m.text==='restart preserved draft')"
    Js "document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "!sending && document.getElementById('chat-text').value===''"
    $checks.expired_chat_explicit_retry_once = Js "window.csrfPosts===2 && chatPages.flatMap(p=>p.messages).filter(m=>m.text==='restart preserved draft').length===1"
    Js "(async()=>{window.foreignCalls=[];window.fetch=async(path)=>{window.foreignCalls.push(path);return new Response(JSON.stringify({error:'foreign origin'}),{status:403})};await post('/api/done',{});window.fetch=window.csrfFetch})()" | Out-Null
    $checks.foreign_403_never_refreshes_token = Js "window.foreignCalls.length===1"
    Js "window.workingCsrf=csrf;csrf='expired-fixture';window.fetch=async(path,opts)=>path==='/'?new Response('',{status:503}):window.csrfFetch(path,opts);document.getElementById('chat-text').value='offline preserved draft';document.getElementById('chat-form').requestSubmit()" | Out-Null
    Wait-Js "!sending && document.getElementById('send-status').textContent.includes('입력을 복사')"
    $checks.failed_token_refresh_preserves_draft = Js "document.getElementById('chat-text').value==='offline preserved draft'"
    Js "window.fetch=window.csrfFetch;csrf=window.workingCsrf;document.getElementById('chat-text').value=''" | Out-Null
    Js "(async()=>{window.gapFetch=window.fetch;window.gapMessage=i=>({id:'gap-'+i,from:'claude:demo',to:'all',text:'gap-message-'+i,ts:'demo'});chatPages=[{start:0,end:240,messages:Array.from({length:240},(_,i)=>window.gapMessage(i+1))}];chatExpanded=true;chatLatestEnd=240;window.fetch=async(path,opts)=>{if(!path.startsWith('/api/chat'))return window.gapFetch(path,opts);const end=Number(new URL(path,location.origin).searchParams.get('before')||480),start=Math.max(0,end-120);return new Response(JSON.stringify({before:start||null,end,messages:Array.from({length:end-start},(_,i)=>window.gapMessage(start+i+1))}),{status:200})};await refreshChat()})()" | Out-Null
    $checks.chat_gap_is_recoverable = Js "document.querySelectorAll('.chat-gap').length===1"
    Js "document.querySelector('.chat-gap').scrollIntoView({block:'start'});document.querySelector('.chat-gap').click()" | Out-Null
    Wait-Js "document.getElementById('chat-messages').textContent.includes('gap-message-300') && !chatLoading"
    $checks.chat_gap_recovered = Js "document.querySelectorAll('.chat-gap').length===0 && document.querySelectorAll('#chat-messages .message').length===480"
    $checks.chat_gap_keeps_reading_position = Js "(()=>{const box=document.getElementById('chat-messages').getBoundingClientRect(),row=[...document.querySelectorAll('#chat-messages .message')].find(e=>e.textContent.includes('gap-message-241')).getBoundingClientRect();return row.top>=box.top-5 && row.top<box.bottom})()"
    Js "(async()=>{window.fetch=window.gapFetch;chatPages=[];chatExpanded=false;chatLatestEnd=null;await refreshChat()})()" | Out-Null
    Js "location.hash='board';window.confirm=()=>false" | Out-Null
    Wait-Js "!document.getElementById('board-view').hidden"
    Js "document.querySelector('button.done[data-kind=card]').click()" | Out-Null
    $checks.cancel_preserves_card = Js "document.querySelector('.board-column').textContent.includes('B-1')"
    Js "window.confirm=()=>true;csrf='expired-fixture';document.querySelector('button.done[data-kind=card]').click()" | Out-Null
    Wait-Js "document.getElementById('connection').textContent.includes('다시 시도') && !document.querySelector('button.done[data-kind=card]').disabled"
    $checks.expired_done_preserves_card = Js "document.querySelector('.board-column').textContent.includes('B-1') && csrf!=='expired-fixture'"
    Js "window.confirm=()=>true;document.querySelector('button.done[data-kind=card]').click()" | Out-Null
    Wait-Js "document.querySelectorAll('.board-column')[3].textContent.includes('B-1')"
    $checks.complete_card = $true
    Js "document.querySelector('button.done[data-kind=approval]').click()" | Out-Null
    Wait-Js "document.querySelectorAll('button.done[data-kind=approval]').length===1"
    $checks.masked_approval_not_in_dom = Js "!document.getElementById('board-view').textContent.includes('123456789012')"
    Js "document.querySelector('button.done[data-kind=approval]').click()" | Out-Null
    Wait-Js "!document.querySelector('button.done[data-kind=approval]')"
    $checks.complete_approval = $true
    $checks.complete_masked_approval = $true
    Js "location.hash='sessions';document.getElementById('session-filter').value='running';document.getElementById('session-filter').dispatchEvent(new Event('change'))" | Out-Null
    Wait-Js "document.getElementById('sessions').textContent.includes('없습니다')"
    $checks.empty_state = $true
    Js "window.originalFetch=window.fetch;window.fetch=()=>Promise.reject(new Error('fixture offline'));document.getElementById('retry').click()" | Out-Null
    Wait-Js "!document.getElementById('retry').hidden"
    $checks.error_retry_visible = Js "document.getElementById('connection').textContent.includes('연결을 확인')"
    Js "tick=2" | Out-Null
    Start-Sleep -Milliseconds 6500
    $checks.error_retained_without_request = Js "!document.getElementById('retry').hidden && document.getElementById('connection').textContent.includes('연결을 확인')"
    Js "window.fetch=window.originalFetch;document.getElementById('retry').click()" | Out-Null
    Wait-Js "document.getElementById('retry').hidden"
    $checks.error_recovers = $true
    Navigate "$FixtureUrl/#session=codex%3Abbbbbbbb-cccc-4ddd-8eee-ffffffffffff" "document.querySelectorAll('#messages .assistant').length===1"
    Js "document.getElementById('older').click()" | Out-Null
    Wait-Js "document.getElementById('older').hidden && !document.getElementById('older').disabled"
    $checks.page_boundary_answer_not_duplicated = Js "document.querySelectorAll('#messages .assistant').length===1 && document.getElementById('messages').textContent.split('페이지 경계 답변').length===2"
    Js "window.transitionFetch=window.fetch;window.transitionA='codex:11111111-2222-4333-8444-555555555555';window.transitionB='codex:bbbbbbbb-cccc-4ddd-8eee-ffffffffffff';window.transitionCalls=[];window.allowTransitionB=false;window.failTransitionOlder=true;window.fetch=async(path,opts)=>{if(!path.startsWith('/api/session?'))return window.transitionFetch(path,opts);const u=new URL(path,location.origin),id=u.searchParams.get('id'),before=u.searchParams.get('before');window.transitionCalls.push({id,before});if(id===window.transitionB && ((!before && !window.allowTransitionB)||(before && window.failTransitionOlder)))throw new Error('temporary fixture failure');return new Response(JSON.stringify({messages:[{role:'assistant',text:id===window.transitionA?'transition-A':before?'transition-B-older':'transition-B-first',ts:'demo'}],before:id===window.transitionA?100:before?null:200,note:'transition fixture'}),{status:200})};location.hash='session='+encodeURIComponent(window.transitionA)" | Out-Null
    Wait-Js "document.getElementById('messages').textContent.includes('transition-A') && detailBefore===100"
    Js "location.hash='session='+encodeURIComponent(window.transitionB)" | Out-Null
    Wait-Js "document.querySelector('#messages button') && !document.getElementById('older').disabled"
    $checks.failed_switch_clears_other_session = Js "detailMessages.length===0 && detailBefore===null && document.getElementById('older').hidden && !document.getElementById('messages').textContent.includes('transition-A')"
    Js "window.allowTransitionB=true;document.querySelector('#messages button').click()" | Out-Null
    Wait-Js "document.getElementById('messages').textContent.includes('transition-B-first') && detailBefore===200"
    Js "document.getElementById('older').click()" | Out-Null
    Wait-Js "!document.getElementById('older').disabled && !document.getElementById('retry').hidden"
    $checks.failed_older_keeps_same_session = Js "detailBefore===200 && detailMessages.length===1 && document.getElementById('messages').textContent.includes('transition-B-first')"
    Js "window.failTransitionOlder=false;document.getElementById('older').click()" | Out-Null
    Wait-Js "document.getElementById('messages').textContent.includes('transition-B-older') && detailBefore===null"
    $checks.switch_retry_never_uses_other_cursor = Js "!document.getElementById('messages').textContent.includes('transition-A') && window.transitionCalls.filter(c=>c.id===window.transitionB).every(c=>c.before!=='100')"
    Js "window.fetch=window.transitionFetch" | Out-Null
    Navigate "$FixtureUrl/#session=claude%3Aaaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee" "document.getElementById('messages').textContent.includes('order-after')"
    $checks.claude_content_order_preserved = Js "(()=>{const rows=[...document.getElementById('messages').children],a=rows.findIndex(el=>el.textContent.includes('order-before')),b=rows.findIndex(el=>el.tagName==='DETAILS' && el.textContent.includes('order_probe')),c=rows.findIndex(el=>el.textContent.includes('order-after'));return a>=0 && a<b && b<c})()"
    if($StaticSnapshotPath) {
        $fileUrl = ([Uri]$StaticSnapshotPath).AbsoluteUri
        Navigate $fileUrl "document.getElementById('board-view') && !document.getElementById('board-view').hidden"
        $checks.static_board_visible = Js "!document.getElementById('board-view').hidden && document.getElementById('board-view').textContent.includes('B-1')"
        $checks.static_has_no_scripts_or_controls = Js "document.scripts.length===0 && document.querySelectorAll('button').length===0"
    }
    $checks.chrome = (Invoke-RestMethod "http://127.0.0.1:$DebugPort/json/version").Browser
    $failed = @($checks.Keys | Where-Object {($checks[$_] -is [bool]) -and -not $checks[$_]})
    if($failed.Count){throw ('Browser checks failed: ' + ($failed -join ', '))}
    $checks | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 (Join-Path $out 'browser-checks.json')
    $checks | ConvertTo-Json -Depth 10
} finally {
    $checks | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 (Join-Path $out 'browser-checks-partial.json')
    if($ws){$ws.Dispose()}
    if(-not $chrome.HasExited){Stop-Process -Id $chrome.Id -ErrorAction SilentlyContinue}
}
