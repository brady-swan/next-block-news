import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch, Mock

PATH=Path(__file__).parents[1]/'infra/codex-reporter/reporter_mcp.py'
spec=importlib.util.spec_from_file_location('reporter_mcp_test',PATH)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

# No model/backend/Typefully calls. All effects live in owned fixture processes.
WORKER='''import json,sys,time,subprocess,os
x=json.load(sys.stdin);a=x['params'].get('arguments',{})
if a.get('die'): sys.exit(2)
if a.get('child'):
 p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
 open(a['child'],'w').write(str(p.pid))
time.sleep(a.get('sleep',0))
print(json.dumps({'content':[{'type':'text','text':'done'}],'isError':False}))
'''

class ReporterMCPTests(unittest.TestCase):
    def test_abrupt_bridge_death_reaps_worker_and_browser_child(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            marker=str(Path(folder)/'pids')
            worker_code=("import importlib.util,os,subprocess,sys,time,json; "
                f"s=importlib.util.spec_from_file_location('bridge',{str(PATH)!r}); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "exec(\"def hang(*args):\\n child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\\n "
                f"open({marker!r},'w').write(json.dumps([os.getpid(),child.pid]))\\n time.sleep(30)\"); "
                "m.call=hang; m.worker()")
            command=[sys.executable,'-c',worker_code]
            bridge_code=("import importlib.util; "
                f"s=importlib.util.spec_from_file_location('bridge',{str(PATH)!r});m=importlib.util.module_from_spec(s);s.loader.exec_module(m); "
                f"original=m.ToolServer;m.ToolServer=lambda emit:original(emit,worker_command={command!r});m.main()")
            bridge=subprocess.Popen([sys.executable,'-c',bridge_code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                bridge.stdin.write(json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call',
                    'params':{'name':'nbn_browser','arguments':{}}})+'\n');bridge.stdin.flush()
                self.wait(lambda:Path(marker).exists())
                pids=json.loads(Path(marker).read_text())
                bridge.kill();bridge.wait(timeout=1)
                def gone():
                    for pid in pids:
                        result=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
                        if result.returncode==0 and not result.stdout.strip().startswith('Z'):return False
                    return True
                self.wait(gone)
            finally:
                if bridge.poll() is None:bridge.kill()
                bridge.communicate(timeout=2)

    def test_reentrant_cleanup_signals_a_group_only_once(self):
        server,_=self.server()
        proc=Mock();proc.pid=123;proc._nbn_cleaned=False
        with patch.object(m.os,'killpg',side_effect=lambda *_:server.kill(proc)) as kill:
            thread=threading.Thread(target=server.kill,args=(proc,),daemon=True)
            thread.start();thread.join(1)
            self.assertFalse(thread.is_alive())
            kill.assert_called_once()

    def wait(self, predicate, timeout=4):
        end=time.monotonic()+timeout
        while not predicate() and time.monotonic()<end: time.sleep(.01)
        self.assertTrue(predicate())

    def server(self, timeout=.6):
        replies={}
        server=m.ToolServer(lambda ident,value:replies.__setitem__(ident,value),
            worker_command=[sys.executable,'-c',WORKER],timeout=timeout)
        self.addCleanup(server.close)
        return server,replies

    def test_saturated_reads_do_not_block_notes_or_cancellation(self):
        server,replies=self.server(timeout=4)
        for i in range(3): server.submit(i,'tools/call',{'name':'nbn_browser','arguments':{'sleep':10}})
        self.wait(lambda:all(j['proc'] is not None for j in server.jobs.values()))
        server.submit(3,'tools/call',{'name':'nbn_browser','arguments':{}})
        self.assertIn('tool_busy_not_dispatched',replies[3]['content'][0]['text'])
        server.submit(4,'tools/call',{'name':'nbn_note','arguments':{}})
        self.wait(lambda:4 in replies)
        self.assertFalse(replies[4]['isError'])
        server.cancel(0)
        self.wait(lambda:0 in replies)
        self.assertIn('tool_cancelled',replies[0]['content'][0]['text'])
        self.assertNotIn(1,replies)

    def test_timeout_leaves_no_worker_and_retains_submission_identity(self):
        server,replies=self.server()
        server.submit(1,'tools/call',{'name':'nbn_submit','arguments':{'sleep':10,'submission_id':'stable'}})
        self.wait(lambda:server.jobs[1]['proc'] is not None)
        proc=server.jobs[1]['proc']
        self.wait(lambda:1 in replies)
        result=json.loads(replies[1]['content'][0]['text'])
        self.assertEqual(result['delivery_status'],'uncertain')
        self.assertEqual(result['submission_id'],'stable')
        self.assertEqual(result['error_kind'],'tool_timeout')
        self.assertIsNotNone(proc.poll())
        self.assertFalse(server.jobs)

    def test_cancel_eof_and_worker_death_preserve_uncertainty(self):
        for action in ('cancel','close','die'):
            with self.subTest(action=action):
                server,replies=self.server(timeout=4)
                args={'sleep':10,'submission_id':'same-id'} if action!='die' else {'die':True,'submission_id':'same-id'}
                server.submit(1,'tools/call',{'name':'nbn_submit','arguments':args})
                if action!='die':
                    self.wait(lambda:server.jobs[1]['proc'] is not None)
                    server.cancel(1) if action=='cancel' else server.close()
                self.wait(lambda:1 in replies)
                value=json.loads(replies[1]['content'][0]['text'])
                self.assertEqual(value['delivery_status'],'uncertain')
                self.assertEqual(value['submission_id'],'same-id')
                self.assertFalse(server.jobs)

    def test_eof_closes_stdio_server_without_stdin_thread_hang(self):
        proc=subprocess.Popen([sys.executable,str(PATH)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        out,err=proc.communicate(json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize'})+'\n',timeout=3)
        self.assertEqual(proc.returncode,0,err)
        self.assertEqual(json.loads(out)['result']['serverInfo']['version'],'0077')

    def test_targeted_text_beyond_initial_window(self):
        text='a'*30000+'Original source clause.'+'b'*20000
        first=m.text_window(text)
        self.assertEqual(first['next_offset'],24000)
        found=m.text_window(text,query='source clause')
        self.assertIn('Original source clause.',found['text'])
        self.assertGreater(found['text_offset'],24000)
        self.assertTrue(found['truncated'])
        self.assertEqual(m.text_window(text,query='absent')['query_match_offset'],-1)

    def test_private_urls_and_credentials_are_rejected(self):
        with patch.object(m.socket,'getaddrinfo',return_value=[(0,0,0,'',('127.0.0.1',443))]):
            with self.assertRaisesRegex(ValueError,'Private'):m.public_url('https://example.com')
        for url in ('file:///etc/passwd','https://user:pass@example.com','http://example.com:8080'):
            with self.assertRaises(ValueError):m.public_url(url)

    def test_browser_returns_links_and_blocks_post_requests(self):
        from types import SimpleNamespace
        context=Mock();page=Mock();context.new_page.return_value=page
        page.url='https://example.com/article';page.title.return_value='Original article'
        page.goto.return_value=SimpleNamespace(status=200)
        page.locator.return_value.inner_text.return_value='a'*30000+'Original clause.'
        page.locator.return_value.evaluate_all.return_value=[{'url':'https://example.com/original','text':'Source'}]
        page.screenshot.return_value=b'pixels'
        browser=Mock();browser.new_context.return_value=context
        playwright=Mock();playwright.chromium.launch.return_value=browser
        manager=Mock();manager.__enter__=Mock(return_value=playwright);manager.__exit__=Mock()
        with patch.dict(sys.modules,{'playwright.sync_api':SimpleNamespace(sync_playwright=lambda:manager)}), \
                patch.object(m,'public_url') as public:
            result=m.browser('https://example.com/article',query='Original clause')
            route=context.route.call_args.args[1]
            blocked=Mock();blocked.request.method='POST';route(blocked)
            blocked.abort.assert_called_once();blocked.continue_.assert_not_called()
            private=Mock();private.request.method='GET';private.request.url='https://127.0.0.1'
            public.side_effect=ValueError('Private');route(private)
            private.abort.assert_called_once()
        self.assertEqual(result['links'][0]['text'],'Source')
        self.assertIn('Original clause',result['text'])
        self.assertGreater(result['text_offset'],24000)
        context.close.assert_called_once();browser.close.assert_called_once()

    def test_child_group_is_cleaned_up(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'child'
            server,replies=self.server(timeout=1)
            server.submit(1,'tools/call',{'name':'nbn_browser','arguments':{'sleep':10,'child':str(path)}})
            self.wait(path.exists)
            child=int(path.read_text())
            self.wait(lambda:1 in replies)
            # An orphan may briefly be a zombie awaiting init reaping, never executing.
            def gone():
                result=subprocess.run(['ps','-p',str(child),'-o','stat='],capture_output=True,text=True)
                return result.returncode!=0 or result.stdout.strip().startswith('Z')
            self.wait(gone)
