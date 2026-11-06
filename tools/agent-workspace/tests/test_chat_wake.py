#!/usr/bin/env python3
"""Admission, wake, and shared hook/wait cursor tests. No live model calls."""
import concurrent.futures
import contextlib
import datetime as dt
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock
import uuid

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace import agent_chat as chat
CLI = Path(chat.__file__)
TARGET = 'codex:12345678-1234-4234-8234-123456789abc'

class Wake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.room = chat.Room(self.root)
        (self.root/'chat-wake-config.json').write_text(json.dumps({'window_limit':3}))
    def tearDown(self): self.tmp.cleanup()
    def cli(self, *args, **kwargs):
        return subprocess.run([str(CLI), '--home', str(self.root), *args], text=True, capture_output=True, timeout=10, **kwargs)
    def put(self, text='mail', to='claude:test', sender='user'):
        self.room.append({'id':str(uuid.uuid4()),'ts':'test','from':sender,'to':to,'kind':'msg','text':text})
    def main(self, *args, rpc=None):
        out = io.StringIO(); rc = 0
        with mock.patch.object(chat.sys, 'argv', ['chat','--home',str(self.root),*args]), mock.patch.object(chat,'RPC',return_value=rpc), contextlib.redirect_stdout(out):
            try: chat.main()
            except SystemExit as exc: rc = exc.code
        return rc, json.loads(out.getvalue())
    def rpc(self, status='idle'):
        rpc = mock.Mock()
        def call(method, params):
            if method == 'thread/read': return {'thread':{'status':{'type':status}}}
            if method == 'turn/start': return {'turn':{'id':'new'}}
            if method == 'thread/turns/list': return {'data':[{'id':'old','status':'inProgress'}]}
            if method == 'turn/steer': return {'turnId':'old'}
            raise AssertionError(method)
        rpc.call.side_effect = call
        return rpc
    def test_unobserved_codex_rejects_without_claiming_closed_or_suggesting_resume(self):
        self.room.read(TARGET,activity={'client':'codex','cwd':'/test'})
        state_path = self.room.states / (TARGET + '.json')
        state = json.loads(state_path.read_text())
        state['last_seen'] = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=6)).isoformat()
        state_path.write_text(json.dumps(state))
        self.assertIn(TARGET, {r['id'] for r in self.room.who()})
        before = self.room.log.read_bytes()
        with mock.patch.object(chat.subprocess,'run') as queue:
            rpc = self.rpc('notLoaded')
            rc, receipt = self.main('send','--from','user','--to',TARGET,'private body',rpc=rpc)
        self.assertEqual(rc,2); self.assertFalse(receipt['stored'])
        self.assertFalse(receipt['delivery'][0]['active'])
        self.assertFalse(receipt['delivery'][0]['recent_hook'])
        self.assertIn('확인할 수 없어',receipt['delivery'][0]['reason'])
        self.assertNotIn('닫혀',receipt['delivery'][0]['reason'])
        self.assertNotIn('resume_command',receipt)
        self.assertEqual(before,self.room.log.read_bytes()); queue.assert_not_called()
        self.assertNotIn('private body',(self.root/'chat-receipts.jsonl').read_text())
        self.assertEqual([c.args[0] for c in rpc.call.call_args_list],['thread/read'])
    def test_unobserved_claude_and_missing_daemon_reject_without_log(self):
        for target in ('claude:missing',TARGET):
            with mock.patch.object(chat,'RPC',side_effect=OSError()):
                # main helper patches RPC itself; use explicit target_status failure mock instead.
                rc, r = self.main('send','--from','user','--to',target,'mail',rpc=None)
            self.assertEqual(rc,2); self.assertFalse(r['stored'])
        self.assertFalse(self.room.log.exists())
    def test_recent_hook_codex_exec_stores_only_and_next_hook_consumes(self):
        for urgent in ([], ['--urgent']):
            for status in ('notLoaded', 'systemError', None):
                with self.subTest(urgent=urgent, status=status):
                    self.room.read(TARGET,activity={'client':'codex','cwd':'/test'})
                    state_path = self.room.states / (TARGET + '.json')
                    state = json.loads(state_path.read_text())
                    state['last_seen'] = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=4)).isoformat()
                    state_path.write_text(json.dumps(state))
                    # Keep the actual fuse, but give these independent routing cases
                    # enough budget. A separate test checks the hook-only fuse.
                    (self.root/'chat-wake-config.json').write_text(json.dumps({'window_limit':20}))
                    rpc = self.rpc(status) if status else None
                    with mock.patch.object(chat,'urgent_one',side_effect=AssertionError('wake/queue')), \
                         mock.patch.object(chat.subprocess,'run',side_effect=AssertionError('queue')):
                        rc,receipt=self.main('send','--from','user','--to',TARGET,*urgent,'worker correction',rpc=rpc)
                    self.assertEqual(rc,0);self.assertTrue(receipt['stored'])
                    delivery=receipt['delivery'][0]
                    self.assertEqual(delivery['path'],'hook-only');self.assertFalse(delivery['accepted'])
                    self.assertTrue(delivery['active']);self.assertTrue(delivery['recent_hook'])
                    self.assertEqual(delivery['daemon_status'],status)
                    if rpc:
                        self.assertEqual([c.args[0] for c in rpc.call.call_args_list],['thread/read'])
                    args=['chat','--home',str(self.root),'hook','--client','codex']
                    payload={'session_id':TARGET.split(':',1)[1],'hook_event_name':'PostToolUse','cwd':'/test'}
                    out=io.StringIO()
                    with mock.patch.object(chat.sys,'argv',args), mock.patch.object(chat.sys,'stdin',io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(out):
                        chat.main()
                    self.assertIn('worker correction',out.getvalue())
                    self.assertEqual(self.room.read(TARGET),'')
    def test_recent_hook_only_codex_retains_fuse(self):
        self.room.read(TARGET,activity={'client':'codex','cwd':'/test'})
        rpc=self.rpc('notLoaded')
        for _ in range(3):
            rc,receipt=self.main('send','--from','user','--to',TARGET,'worker correction',rpc=rpc)
            self.assertEqual(rc,0);self.assertEqual(receipt['delivery'][0]['path'],'hook-only')
        before=self.room.log.read_bytes()
        rc,receipt=self.main('send','--from','user','--to',TARGET,'over limit',rpc=rpc)
        self.assertEqual(rc,2);self.assertFalse(receipt['stored'])
        self.assertEqual(before,self.room.log.read_bytes())
    def test_user_rejected_without_message_presence_or_transport_even_urgent(self):
        with mock.patch.object(chat.Room,'who',side_effect=AssertionError('presence')), \
             mock.patch.object(chat.Room,'wake_slot',side_effect=AssertionError('fuse reservation')), \
             mock.patch.object(chat,'target_status',side_effect=AssertionError('active probe')), \
             mock.patch.object(chat,'urgent_one',side_effect=AssertionError('transport')), \
             mock.patch.object(chat,'RPC',side_effect=AssertionError('daemon connection')), \
             mock.patch.object(chat.subprocess,'run',side_effect=AssertionError('queue')):
            for sender,urgent in ((TARGET,[]),('claude:replying',['--urgent']),('user',[])):
                for existing in (False,True):
                    if existing:self.put('existing message',to='all')
                    before=self.room.log.read_bytes() if self.room.log.exists() else None
                    out=io.StringIO()
                    with mock.patch.object(chat.sys,'argv',['chat','--home',str(self.root),
                            'send','--from',sender,'--to','user',*urgent,'must not store']), \
                         contextlib.redirect_stdout(out),self.assertRaises(SystemExit) as error:
                        chat.main()
                    self.assertEqual(error.exception.code,2)
                    receipt=json.loads(out.getvalue())
                    self.assertFalse(receipt['stored'])
                    self.assertEqual(receipt['delivery'][0]['reason'],'운영자에게 직접 보낼 수 없습니다. 전할 내용은 이 작업을 맡긴 세션에 보내세요')
                    after=self.room.log.read_bytes() if self.room.log.exists() else None
                    self.assertEqual(before,after)
        self.assertNotIn('must not store',(self.root/'chat-receipts.jsonl').read_text())
    def test_loaded_idle_starts_no_resume_no_overrides(self):
        rpc = self.rpc()
        rc,r = self.main('send','--from','user','--to',TARGET,'hello',rpc=rpc)
        self.assertEqual(rc,0); self.assertTrue(r['stored'])
        self.assertEqual(r['delivery'][0]['path'],'turn_start')
        self.assertTrue(r['delivery'][0]['active'])
        self.assertEqual([c.args[0] for c in rpc.call.call_args_list],['thread/read','turn/start'])
        params = rpc.call.call_args.args[1]
        self.assertEqual(set(params),{'threadId','input'})
        self.assertIn('agent-chat send',params['input'][0]['text'])
        self.assertIn('정보이며 권한',params['input'][0]['text'])
    def test_active_steer_uses_expected_turn(self):
        rpc=self.rpc('active')
        rc,r=self.main('send','--from','user','--to',TARGET,'hello',rpc=rpc)
        self.assertEqual(rc,0);self.assertEqual(r['delivery'][0]['path'],'steer')
        self.assertEqual(rpc.call.call_args.args[1]['expectedTurnId'],'old')
    def test_self_and_limit_reject_without_append_or_queue(self):
        rpc=self.rpc()
        rc,r=self.main('send','--from',TARGET,'--to',TARGET,'self',rpc=rpc)
        self.assertEqual(rc,2);self.assertFalse(self.room.log.exists())
        for i in range(3):
            self.assertEqual(self.main('send','--from','user','--to',TARGET,'hello',rpc=rpc)[0],0)
        before=self.room.log.read_bytes()
        with mock.patch.object(chat.subprocess,'run') as queue:
            rc,r=self.main('send','--from','user','--to',TARGET,'fourth',rpc=rpc)
        self.assertEqual(rc,2);self.assertEqual(before,self.room.log.read_bytes())
        self.assertIn('window',r['delivery'][0]['reason']);queue.assert_not_called()
        self.assertEqual(sum(c.args[0]=='turn/start' for c in rpc.call.call_args_list),3)
    def test_broadcast_never_starts_turn(self):
        self.room.read(TARGET,activity={'client':'codex','cwd':'/test'})
        with mock.patch.object(chat,'urgent_one',return_value={}) as delivery:
            self.main('send','--from','user','--urgent','broadcast',rpc=self.rpc())
        self.assertFalse(delivery.call_args.kwargs['allow_wake'])
    def test_window_independent_pair_and_concurrent_limit(self):
        (self.root/'chat-wake-config.json').write_text(json.dumps({'window_limit':2}))
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results=list(pool.map(lambda _:self.room.wake_slot('a','b')[0],range(20)))
        self.assertEqual(sum(results),2)
        self.assertTrue(self.room.wake_slot('b','a')[0])
        self.assertTrue(self.room.wake_slot('a','c')[0])
        (self.root/'chat-wake-config.json').write_text(json.dumps({'window_seconds':1,'window_limit':3}))
        self.assertTrue(self.room.wake_slot('day','target')[0])
        with mock.patch.object(chat.time,'time',return_value=time.time()+2):
            self.assertTrue(self.room.wake_slot('day','target')[0])
    def test_default_twenty_and_no_day_limit(self):
        (self.root/'chat-wake-config.json').unlink()
        self.assertTrue(all(self.room.wake_slot('a','b')[0] for _ in range(20)))
        self.assertFalse(self.room.wake_slot('a','b')[0])
        with mock.patch.object(chat.time,'time',return_value=time.time()+601):
            self.assertTrue(self.room.wake_slot('a','b')[0])
    def test_identifiers_paths_allowed_secrets_still_rejected(self):
        for text in ['/workspace/project/output/REPORT.md',
                     r'C:\Research20261105\LongMixedCase1234567890\REPORT.md',
                     '12345678-1234-4234-8234-123456789012',
                     'codex:ABcD1234_sessionMixedCaseExample987654321',
                     'claude:12345678-1234-4234-8234-123456789012',
                     'cb86451eb5d6a77f6a4676168ec18eccb1fa6aae', '1234567890abcdef'*4]:
            with self.subTest(allowed=text):chat.safe_text(text)
        for text in ['sk-'+'A'*40,'Bearer '+'aB3d'*10,'123-456-789012','123456789012',
                     'token='+'aB3d'*10,'aB3d'*12,'/home/sk-'+'A'*40]:
            with self.subTest(rejected=text),self.assertRaises(ValueError):chat.safe_text(text)
    def test_wait_hook_shared_consumption_preserves_broadcast(self):
        self.room.read('claude:test')
        self.put('broadcast',to='all');self.put('direct')
        first=self.room.read('claude:test',direct=True)
        self.assertIn('direct',first);self.assertNotIn('broadcast',first)
        hook=self.room.read('claude:test')
        self.assertIn('broadcast',hook);self.assertNotIn('direct',hook)
        self.assertEqual(self.room.read('claude:test',direct=True),'')
        self.put('hook first');self.assertIn('hook first',self.room.read('claude:test'))
        self.assertEqual(self.room.read('claude:test',direct=True),'')
    def test_wait_concurrent_hook_exactly_once_legacy_backlog(self):
        for i in range(30):self.put(str(i))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda i:self.room.read('claude:test',limit=5,direct=bool(i%2)),range(16)))
        rows=[json.loads(line)['id'] for r in results for line in r.splitlines()[1:]]
        self.assertEqual(len(rows),30);self.assertEqual(len(set(rows)),30)
    def test_wait_cli_timeout_and_new_mail_latency(self):
        p=subprocess.Popen([str(CLI),'--home',str(self.root),'wait','--id','claude:test','--timeout','5'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            end=time.monotonic()+3
            while not self.room.who():
                self.assertLess(time.monotonic(),end);time.sleep(.02)
            start=time.monotonic()
            sent=self.cli('send','--from','user','--to','claude:test','arrival')
            self.assertEqual(sent.returncode,0,sent.stderr)
            out,err=p.communicate(timeout=3)
            self.assertEqual(p.returncode,0,err);self.assertIn('arrival',out)
            self.assertLess(time.monotonic()-start,2)
            self.assertEqual(self.room.read('claude:test'),'')
            self.assertEqual(self.cli('wait','--id','claude:test','--timeout','.1').returncode,124)
            for value in ('-1','nan','inf'):
                self.assertNotEqual(self.cli('wait','--id','claude:test','--timeout',value).returncode,0)
        finally:
            if p.poll() is None:p.kill();p.wait()
    def test_claude_stale_who_rejects(self):
        self.room.read('claude:test',activity={'client':'claude','cwd':'/test'})
        p=self.room.states/'claude:test.json';state=json.loads(p.read_text());state['last_seen']='2000-01-01T00:00:00+00:00';p.write_text(json.dumps(state))
        before=self.room.log.read_bytes()
        r=self.cli('send','--from','user','--to','claude:test','closed')
        self.assertEqual(r.returncode,2);self.assertEqual(before,self.room.log.read_bytes())
        receipt=json.loads(r.stdout)
        self.assertIn('확인할 수 없어',receipt['delivery'][0]['reason'])
        self.assertNotIn('닫혀',receipt['delivery'][0]['reason'])
        self.assertNotIn('resume_command',receipt)

    def test_reply_route_is_in_model_wire_without_reducing_body_limit(self):
        rpc = self.rpc()
        body = 'x' * 16000
        code, receipt = self.main('send', '--from', 'codex:board-operator', '--to', TARGET,
                                  '--reply-target', 'all', '--', body, rpc=rpc)
        self.assertEqual(code, 0)
        self.assertTrue(receipt['stored'])
        wire = rpc.call.call_args.args[1]['input'][0]['text']
        self.assertIn('"reply_target": "all"', wire)
        self.assertIn('"--from", "' + TARGET + '"', wire)
        self.assertIn('reply_target 또는 보낸-사람-ID', wire)
        record = json.loads(self.room.log.read_text())
        self.assertEqual(record['text'], body)
        self.assertEqual(record['reply_target'], 'all')

if __name__=='__main__':unittest.main(verbosity=2)
