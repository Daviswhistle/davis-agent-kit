from unittest import mock
import concurrent.futures, importlib.machinery, importlib.util, json, os, pathlib, subprocess, tempfile, unittest, uuid
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agent_workspace import agent_chat as mod
CLI = pathlib.Path(mod.__file__)
class Local(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
 def tearDown(self): self.tmp.cleanup()
 def runcli(self,*args):
  return subprocess.run([str(CLI),'--home',str(self.root),*args],capture_output=True,text=True)
 def send(self,text='hello',sender='user',to='all'):
  if to!='all':
   # Stored-mail fixtures exercise reader compatibility independently of admission.
   mod.Room(self.root).append({'id':str(uuid.uuid4()),'ts':'test','from':sender,'to':to,'kind':'msg','text':text})
   return
  p=self.runcli('send','--from',sender,'--to',to,text); self.assertEqual(p.returncode,0,p.stderr)
 def test_nested_native_claude_identity(self):
  with mock.patch.dict(os.environ,{'CODEX_THREAD_ID':'parent','CLAUDE_CODE_SESSION_ID':'child'},clear=True), mock.patch.object(mod.os,'readlink',return_value='/opt/claude/versions/2.1.318'), mock.patch.object(mod.Path,'read_text',return_value='claude'):
   self.assertEqual(mod.identity(),'claude:child')
 def test_receiver_reply_commands_work_without_session_environment(self):
  env={k:v for k,v in os.environ.items() if k not in ('CODEX_THREAD_ID','CLAUDE_CODE_SESSION_ID')}
  for mode in ('claude-hook','codex-hook','read','wait'):
   with self.subTest(mode=mode):
    root=self.root/mode;room=mod.Room(root);who=('codex:' if mode=='codex-hook' else 'claude:')+'receiver'
    def cli(*args,input=None):
     result=subprocess.run([sys.executable,str(CLI),'--home',str(root),*args],input=input,capture_output=True,text=True,env=env)
     self.assertEqual(result.returncode,0,result.stderr);return result.stdout
    room.read(who)
    cli('send','--from','codex:board-operator','--to','all','--reply-target','all','--','question')
    if mode=='wait':
     record=json.loads(room.log.read_text());record.update(id=str(uuid.uuid4()),to=who);room.append(record)
     output=cli('wait','--id',who,'--timeout','1')
    elif mode.endswith('-hook'):
     client=mode.split('-')[0]
     output=json.loads(cli('hook','--client',client,input=json.dumps({'session_id':'receiver','hook_event_name':'PostToolUse'})))['hookSpecificOutput']['additionalContext']
    else:output=cli('read','--from',who,'--max-chars','1000')
    message=json.loads(output.splitlines()[1]);command=message['reply_command']
    self.assertEqual(command[command.index('--from')+1],who)
    reply=subprocess.run([*command,'answer'],capture_output=True,text=True,env=env)
    self.assertEqual(reply.returncode,0,reply.stderr)
    receipt=json.loads(reply.stdout);self.assertTrue(receipt['stored']);self.assertEqual(receipt['from'],who)
    rows=[json.loads(line) for line in room.log.read_text().splitlines()]
    self.assertEqual(rows[-1]['text'],'answer');self.assertEqual(rows[-1]['to'],'all')
 def test_concurrency_and_append_only(self):
  self.send('prefix'); prefix=(self.root/'chat.jsonl').read_bytes()
  def write(i): return self.runcli('send','--from',f'codex:writer-{i}',f'parallel-{i}')
  with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool: results=list(pool.map(write,range(20)))
  self.assertTrue(all(p.returncode==0 for p in results))
  raw=(self.root/'chat.jsonl').read_bytes();self.assertTrue(raw.startswith(prefix))
  rows=[json.loads(x) for x in raw.splitlines()];self.assertEqual(len(rows),21); self.assertEqual(len({r['id'] for r in rows}),21)
  self.assertEqual((self.root/'chat.jsonl').stat().st_mode&0o777,0o600)
 def test_address_cursor_limit_and_all(self):
  self.send('self',sender='codex:reader');self.send('other',to='claude:someone')
  for i in range(12):self.send('visible-'+str(i),to='codex:reader')
  payload={'session_id':'reader','hook_event_name':'PostToolUse'}
  def hook():return subprocess.run([str(CLI),'--home',str(self.root),'hook','--client','codex'],input=json.dumps(payload),capture_output=True,text=True)
  a=hook();b=hook();c=hook();self.assertEqual(c.stdout,'')
  for p in (a,b): self.assertEqual(p.returncode,0,p.stderr)
  ca=json.loads(a.stdout)['hookSpecificOutput']['additionalContext'];cb=json.loads(b.stdout)['hookSpecificOutput']['additionalContext']
  self.assertEqual(len(ca.splitlines()),9); self.assertEqual(len(cb.splitlines()),5);self.assertNotIn('"text": "self"',ca);self.assertNotIn('"text": "other"',ca)
  saved=(self.root/'chat-state/codex:reader.json').read_bytes()
  full=self.runcli('read','--from','codex:reader','--all');self.assertIn('"text": "self"',full.stdout)
  self.assertEqual((self.root/'chat-state/codex:reader.json').read_bytes(),saved)
 def test_hook_caps_and_replay(self):
  self.assertEqual(mod.Room(str(self.root)).read('claude:caps'),'')
  for i in range(20):self.send('긴글"\n'*300)
  p=subprocess.run([str(CLI),'--home',str(self.root),'hook','--client','claude'],input=json.dumps({'session_id':'caps','hook_event_name':'UserPromptSubmit'}),capture_output=True,text=True)
  context=json.loads(p.stdout)['hookSpecificOutput']['additionalContext'];self.assertLessEqual(len(context),4000);self.assertTrue(context.startswith(mod.HEADER))
  total=len(context.splitlines())-1
  while True:
   out=mod.Room(str(self.root)).read('claude:caps',limit=8,chars=4000,per_text=600)
   if not out:break
   total+=len(out.splitlines())-1
  self.assertEqual(total,20)
 def test_rejection_no_echo_no_append(self):
  for text in ['sk-'+'A'*40,'token='+('a'*30),'12345678901234','123-456-789012','-----BEGIN PRIVATE KEY-----','aB3d'*12]:
   p=self.runcli('send','--from','user',text);self.assertNotEqual(p.returncode,0);self.assertNotIn(text,p.stderr)
  self.assertFalse((self.root/'chat.jsonl').exists())
 def test_all_replays_beyond_normal_batch_without_cursor_change(self):
  room=mod.Room(str(self.root))
  for i in range(150):room.append({'id':str(i),'ts':'2026-11-05T00:00:00+09:00','from':'user','to':'all','kind':'msg','text':'full-'+str(i)})
  result=self.runcli('read','--all','--from','codex:history')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(len(result.stdout.splitlines()),151)
  self.assertFalse((self.root/'chat-state/codex:history.json').exists())
  self.assertEqual(self.runcli('read','--from','codex:history').stdout,'')
 def test_symlink_and_partial_fail_closed(self):
  target=self.root/'target';target.write_text('do not touch');(self.root/'chat.jsonl').symlink_to(target)
  self.assertNotEqual(self.runcli('send','--from','user','hello').returncode,0);self.assertEqual(target.read_text(),'do not touch')
  (self.root/'chat.jsonl').unlink();(self.root/'chat.jsonl').write_text('{partial')
  self.assertNotEqual(self.runcli('send','--from','user','hello').returncode,0);self.assertEqual((self.root/'chat.jsonl').read_text(),'{partial')
 def test_parent_alias_cannot_store_in_git_but_private_alias_remains_usable(self):
  repo=self.root/'repo';(repo/'.git').mkdir(parents=True);(repo/'.git/HEAD').write_text('ref: refs/heads/main\n')
  (repo/'nested').mkdir();alias=self.root/'alias';alias.symlink_to(repo/'nested',target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'Git'):
   mod.Room(alias/'room')
  self.assertFalse((repo/'nested/room/chat.jsonl').exists())
  alias.unlink();private=self.root/'private';private.mkdir();(private/'.git').mkdir()
  alias.symlink_to(private,target_is_directory=True)
  mod.Room(alias/'room').append({'text':'allowed'})
  self.assertEqual(json.loads((private/'room/chat.jsonl').read_text())['text'],'allowed')
  leaf=self.root/'leaf';leaf.symlink_to(private/'room',target_is_directory=True)
  with self.assertRaises(ValueError):mod.Room(leaf)
 def test_readers_same_session_no_duplicates(self):
  self.assertEqual(self.runcli('read','--from','codex:one').stdout,'')
  for i in range(30):self.send('row-'+str(i))
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   result=list(pool.map(lambda _:self.runcli('read','--from','codex:one','--limit','5'),range(8)))
  rows=[json.loads(line)['id'] for p in result for line in p.stdout.splitlines()[1:]]
  self.assertEqual(len(rows),30);self.assertEqual(len(set(rows)),30)
 def hook(self,client,session,*options):
  return subprocess.run([str(CLI),'--home',str(self.root),'hook','--client',client,*options],input=json.dumps({'session_id':session,'hook_event_name':'PostToolUse'}),capture_output=True,text=True)
 def context_rows(self,p):
  self.assertEqual(p.returncode,0,p.stderr)
  if not p.stdout:return []
  value=json.loads(p.stdout)['hookSpecificOutput']['additionalContext']
  self.assertTrue(value.startswith(mod.HEADER));self.assertLessEqual(len(value),4000)
  return [json.loads(line) for line in value.splitlines()[1:]]
 def test_idle_claude_cli_mail_consumed_once_by_next_hook_or_wait(self):
  for stale in (False,True):
   for first in ('hook','wait'):
    with self.subTest(stale=stale,first=first):
     session=f'idle-{stale}-{first}';target='claude:'+session
     if stale:
      self.assertEqual(self.hook('claude',session).stdout,'')
      path=self.root/('chat-state/'+target+'.json');state=json.loads(path.read_text())
      state['last_seen']='2000-01-01T00:00:00+00:00';path.write_text(json.dumps(state))
     sent=self.runcli('send','--from','codex:worker','--to',target,'saved report '+session)
     self.assertEqual(sent.returncode,4,sent.stderr)
     receipt=json.loads(sent.stdout)
     self.assertTrue(receipt['stored']);self.assertTrue(receipt['pending_idle'])
     stored=[json.loads(line) for line in (self.root/'chat.jsonl').read_text().splitlines()]
     self.assertEqual(stored[-1]['id'],receipt['id'])
     if first=='hook':
      rows=self.context_rows(self.hook('claude',session))
     else:
      result=self.runcli('wait','--id',target,'--timeout','0')
      self.assertEqual(result.returncode,0,result.stderr)
      rows=[json.loads(line) for line in result.stdout.splitlines()[1:]]
     self.assertEqual([m['id'] for m in rows],[receipt['id']])
     self.assertEqual(rows[0]['text'],'saved report '+session)
     # Both readers share consumption, irrespective of which received first.
     self.assertEqual(self.hook('claude',session).stdout,'')
     waited=self.runcli('wait','--id',target,'--timeout','0')
     self.assertEqual(waited.returncode,124,waited.stderr);self.assertEqual(waited.stdout,'')
 def test_prejoin_all_hidden_first_hook(self):
  self.send('PREJOIN_BROADCAST')
  snapshot=(self.root/'chat.jsonl').read_bytes()
  for client in ('claude','codex'):
   with self.subTest(client=client):
    result=self.hook(client,'new')
    self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'')
    state=json.loads((self.root/('chat-state/'+client+':new.json')).read_text())
    self.assertEqual(state['offset'],len(snapshot));self.assertEqual(state['joined_offset'],len(snapshot))
    self.assertEqual(self.hook(client,'new').stdout,'')
    saved=(self.root/('chat-state/'+client+':new.json')).read_bytes()
    history=self.runcli('read','--from',client+':new','--all')
    self.assertIn('PREJOIN_BROADCAST',history.stdout)
    self.assertEqual((self.root/('chat-state/'+client+':new.json')).read_bytes(),saved)
  self.assertEqual((self.root/'chat.jsonl').read_bytes(),snapshot)
 def test_first_read_skips_all_then_receives_postjoin(self):
  self.send('OLD_ALL')
  first=self.runcli('read','--from','codex:new-read')
  self.assertEqual(first.returncode,0,first.stderr);self.assertEqual(first.stdout,'')
  end=(self.root/'chat.jsonl').stat().st_size
  self.assertEqual(json.loads((self.root/'chat-state/codex:new-read.json').read_text())['offset'],end)
  self.send('NEW_ALL');self.send('NOT_FOR_READER',to='claude:other');self.send('OWN',sender='codex:new-read')
  result=self.runcli('read','--from','codex:new-read')
  self.assertEqual([json.loads(line)['text'] for line in result.stdout.splitlines()[1:]],['NEW_ALL'])
  self.assertEqual(self.runcli('read','--from','codex:new-read').stdout,'')
 def test_postjoin_all_visible_in_both_hooks(self):
  for client in ('claude','codex'):
   with self.subTest(client=client):
    self.assertEqual(self.hook(client,'live').stdout,'')
  self.send('AFTER_JOIN')
  for client in ('claude','codex'):
   with self.subTest(client=client):
    self.assertEqual([m['text'] for m in self.context_rows(self.hook(client,'live'))],['AFTER_JOIN'])
    self.assertEqual(self.hook(client,'live').stdout,'')
 def test_prejoin_direct_delivered_only_to_exact_recipient(self):
  self.send('OLD_ALL')
  for client in ('claude','codex'):
   self.send('DIRECT_'+client,to=client+':mailbox')
   self.send('SELF',sender=client+':mailbox',to=client+':mailbox')
  end=(self.root/'chat.jsonl').stat().st_size
  for client in ('claude','codex'):
   with self.subTest(client=client):
    result=self.hook(client,'mailbox')
    self.assertEqual([m['text'] for m in self.context_rows(result)],['DIRECT_'+client])
    state=json.loads((self.root/('chat-state/'+client+':mailbox.json')).read_text())
    self.assertEqual(state['offset'],end);self.assertEqual(state['joined_offset'],end)
    self.assertEqual(self.hook(client,'mailbox').stdout,'')
  # The CLI read path has the same exception, without a hook wrapper.
  self.send('READ_DIRECT',to='codex:read-mailbox')
  result=self.runcli('read','--from','codex:read-mailbox')
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual([json.loads(line)['text'] for line in result.stdout.splitlines()[1:]],['READ_DIRECT'])
 def test_prejoin_direct_backlog_survives_limit_and_postjoin(self):
  for i in range(12):
   self.send('OLD_ALL_'+str(i));self.send('MAIL_'+str(i),to='codex:backlog')
  boundary=(self.root/'chat.jsonl').stat().st_size
  first=self.context_rows(self.hook('codex','backlog'))
  self.assertEqual(len(first),8)
  state=json.loads((self.root/'chat-state/codex:backlog.json').read_text())
  self.assertEqual(state['offset'],boundary);self.assertLess(state['pending_direct_offset'],boundary)
  self.send('LIVE_ALL');self.send('LIVE_DIRECT',to='codex:backlog')
  rest=self.context_rows(self.hook('codex','backlog'))
  self.assertEqual([m['text'] for m in first+rest],['MAIL_'+str(i) for i in range(12)]+['LIVE_ALL','LIVE_DIRECT'])
  self.assertEqual(self.hook('codex','backlog').stdout,'')
 def test_prejoin_direct_char_cap_does_not_lose_backlog(self):
  for i in range(5):
   self.send('OLD_ALL_'+str(i));self.send('MAIL_'+str(i)+'x '*450,to='claude:char-backlog')
  seen=[]
  for _ in range(8):
   result=self.hook('claude','char-backlog','--max-chars','1000')
   rows=self.context_rows(result)
   if not rows:break
   self.assertLessEqual(len(json.loads(result.stdout)['hookSpecificOutput']['additionalContext']),1000)
   seen.extend(m['id'] for m in rows)
  self.assertEqual(len(seen),5);self.assertEqual(len(set(seen)),5)
 def test_concurrent_first_read_direct_delivery_exactly_once(self):
  for i in range(30):
   self.send('STALE_'+str(i));self.send('DIRECT_'+str(i),to='codex:first-race')
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   result=list(pool.map(lambda _:self.runcli('read','--from','codex:first-race','--limit','5'),range(8)))
  for p in result:self.assertEqual(p.returncode,0,p.stderr)
  rows=[json.loads(line) for p in result for line in p.stdout.splitlines()[1:]]
  self.assertEqual(len(rows),30);self.assertEqual(len({r['id'] for r in rows}),30)
  self.assertTrue(all(r['to']=='codex:first-race' for r in rows))
 def test_existing_legacy_state_keeps_unread_offset(self):
  self.send('ALREADY_JOINED_UNREAD')
  st=(self.root/'chat.jsonl').stat()
  saved={'id':'codex:legacy','offset':0,'inode':st.st_ino,'device':st.st_dev}
  (self.root/'chat-state/codex:legacy.json').write_text(json.dumps(saved))
  result=self.runcli('read','--from','codex:legacy')
  self.assertEqual(result.returncode,0,result.stderr);self.assertIn('ALREADY_JOINED_UNREAD',result.stdout)
  self.assertEqual(self.runcli('read','--from','codex:legacy').stdout,'')
 def test_valid_dates_and_basic_credentials(self):
  mod.safe_text('Review on 2099-01-01 with commit '+'a'*40)
  for value in ['Authorization: Basic ZHVtbXk6ZHVtbXk=', 'token=2099-01-01', json.dumps({'api_key':'a'*40})]:
   with self.assertRaises(ValueError):mod.safe_text(value)
if __name__=='__main__':unittest.main(verbosity=2)
