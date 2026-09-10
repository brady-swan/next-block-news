import copy
import json
import time
import unittest
from unittest.mock import patch

import httpx

from nbn import config, reporter_pdf as pdf, reporter_search as lookup, reporter_store as rs
from nbn import reporter_tools as tools, reporter_visual_contract as contract, search, store, visual_render, visuals
from tests.support import temporary_store
from tests.test_pdf_source import pdf_bytes


class ReporterToolingTests(unittest.TestCase):
    def test_clipped_pdf_can_continue_inside_the_same_page(self):
        # Use many short text lines so the text layer remains on the physical page.
        original=pdf_bytes(['placeholder'])
        text='Beginning '+('evidence '*3200)+'Final clause.'
        with patch.object(pdf.subprocess,'Popen') as popen:
            def fake(argv,**kw):
                from pathlib import Path
                from unittest.mock import Mock
                Path(argv[-1]).write_text(text+'\f')
                proc=Mock();proc.poll.return_value=0;proc.returncode=0
                return proc
            popen.side_effect=fake
            first=pdf.extract(original,page_count=1)
            cursor=first['next_cursor']
            self.assertEqual(cursor['start_page'],1)
            second=pdf.extract(original,start_page=cursor['start_page'],page_count=cursor['page_count'],
                               text_offset=cursor['pdf_text_offset'])
        self.assertIn('Final clause.',second['text'])
        self.assertIn('[PDF page 1]',second['text'])
        self.assertLessEqual(len(second['text']),24030)
        self.assertIsNone(second['next_cursor'])

    def test_selected_pdf_page_25_and_literal_search(self):
        data=pdf_bytes([f'Page {i}: '+('Credit union operative language.' if i==25 else 'Unrelated text.') for i in range(1,30)])
        read=pdf.extract(data,start_page=25,page_count=1)
        self.assertIn('[PDF page 25]',read['text'])
        self.assertNotIn('Page 24:',read['text'])
        self.assertEqual(read['pages_scanned'],[25,25])
        result=pdf.extract(data,query='Credit union')
        self.assertEqual(result['match_pages'],[25])
        self.assertIn('snippets only',result['limitations'])
        self.assertIn('publication date',result['limitations'])
        self.assertEqual(pdf.extract(data,query='nonexistent')['text'],'')

    def test_pdf_failures_and_bounds(self):
        data=pdf_bytes(['A source.'])
        with patch.object(pdf,'MAX_BYTES',2),patch.object(pdf.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'32 MiB'):pdf.extract(data)
            spawn.assert_not_called()
        for args in ({'start_page':501},{'start_page':True},{'page_count':13},{'query':'x'*201}):
            with self.assertRaises(ValueError):pdf.extract(data,**args)
        with self.assertRaisesRegex(ValueError,'deadline'):pdf.extract(data,deadline=time.monotonic()-1)
        self.assertEqual(pdf.extract(pdf_bytes(['']))['error_kind'],'pdf_no_text')
        with self.assertRaisesRegex(ValueError,'out of range'):pdf.extract(data,start_page=25)

    def test_search_snippets_and_text_are_bounded(self):
        # Many pages match: return first12 snippets and enumerate all searched matching pages.
        result=pdf.extract(pdf_bytes(['Term in a page.']*30),query='term')
        self.assertEqual(result['match_pages'],list(range(1,31)))
        self.assertEqual(result['text'].count('[PDF page'),12)
        self.assertTrue(result['truncated'])
        with patch.object(pdf,'MAX_OUTPUT_BYTES',2):
            with self.assertRaisesRegex(ValueError,'8 MiB'):pdf.extract(pdf_bytes(['More than two bytes']))

    def test_pdf_bounded_stream_and_public_redirect(self):
        calls=[]
        def respond(request):
            calls.append(str(request.url))
            if request.url.path=='/start': return httpx.Response(302,headers={'location':'https://other.example/doc.pdf'})
            return httpx.Response(200,content=pdf_bytes(['Original']))
        original=httpx.Client
        with patch.object(pdf.httpx,'Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(respond),**kw)), \
                patch.object(pdf.sources,'_assert_public_http_url') as check:
            result=pdf.fetch('https://example.com/start')
        self.assertEqual(check.call_count,2)
        self.assertEqual(result['final_url'],'https://other.example/doc.pdf')
        self.assertIn('Original',result['text'])

    def test_chart_example_renders_and_missing_fields_are_reported_together(self):
        args=copy.deepcopy(contract.EXAMPLE)
        contract.check(args)
        clean=visual_render.validate('bar',args['spec'],[{'fetch_id':'RECEIPT_ID','text':'100 then32','retrieval_kind':'direct_fetch'}])
        data,_=visual_render.render('bar','landscape',clean)
        self.assertTrue(data.startswith(b'\x89PNG'))
        with self.assertRaises(ValueError) as caught:
            contract.check({'operation':'render','kind':'bar','spec':{'title':'Treasury','data':[]}})
        for field in ('purpose','alt_text','spec.headline','spec.unit','spec.period','spec.points','unexpected spec.title'):
            self.assertIn(field,str(caught.exception))

    def test_schema_exposes_example_and_real_required_fields(self):
        schema=next(t for t in tools.TOOLS if t['name']=='nbn_visual')
        self.assertIn(json.dumps(contract.EXAMPLE),schema['description'])
        self.assertEqual(schema['inputSchema']['properties']['spec']['oneOf'][0]['required'],contract.CHART['required'])

    def test_search_success_empty_cache_and_failure_are_distinct(self):
        with temporary_store() as con,patch.object(config,'SERPAPI_KEY','fixture'):
            with patch.object(search,'google',return_value=[]) as google:
                first=lookup.google(con,'actual query','test')
                second=lookup.google(con,'actual query','test')
            self.assertTrue(first['ok']);self.assertEqual(first['results'],[])
            self.assertTrue(second['cached']);google.assert_called_once()
            with patch.object(search,'google',side_effect=search.SearchError('transport error',kind='transport')):
                failed=lookup.google(con,'different query','test')
            self.assertFalse(failed['ok']);self.assertEqual(failed['error_kind'],'transport')
            self.assertNotIn('results',failed)
            self.assertIn('native web search',failed['message'])

    def test_search_cooldown_and_unconfigured_do_not_call_provider(self):
        with temporary_store() as con,patch.object(search,'google') as google:
            with patch.object(config,'SERPAPI_KEY',''):
                self.assertEqual(lookup.google(con,'a','test')['error_kind'],'unconfigured')
            store.record_search_failure(con,'serpapi','rate_limited','429',retry_after_seconds=60)
            with patch.object(config,'SERPAPI_KEY','fixture'):
                self.assertEqual(lookup.google(con,'a','test')['error_kind'],'rate_limited')
            google.assert_not_called()

    def test_new_tools_do_not_bypass_paused_shift(self):
        with temporary_store() as con:
            shift=rs.start(con,worker_id='test',shift_id='fixture')
            rs.stop(con,shift_id='fixture',status='paused')
            with patch.object(pdf,'fetch') as fetch:
                with self.assertRaises(Exception):
                    tools.dispatch(con,shift_id='fixture',generation=shift['generation'],name='nbn_fetch',
                                   args={'url':'https://example.com/a.pdf','start_page':25})
                fetch.assert_not_called()

    def test_x_rate_limit_is_not_an_empty_result(self):
        with temporary_store() as con,patch.object(config,'X_BEARER_TOKEN','fixture'):
            shift=rs.start(con,worker_id='test',shift_id='fixture')
            response=httpx.Response(429,request=httpx.Request('GET','https://api.twitter.com/2/tweets/search/recent'))
            with patch.object(tools.httpx,'get',return_value=response):
                result=tools.dispatch(con,shift_id='fixture',generation=shift['generation'],name='nbn_x',args={'query':'bitcoin'})
            self.assertFalse(result['ok']);self.assertEqual(result['error_kind'],'rate_limited')
            self.assertNotIn('posts',result)

    def test_x_errors_and_malformed_success_are_not_empty_results(self):
        with temporary_store() as con,patch.object(config,'X_BEARER_TOKEN','fixture'):
            shift=rs.start(con,worker_id='test',shift_id='fixture')
            for raw,expected in [([],False),({'errors':[{'title':'Unavailable'}]},False),
                                 ({'data':[]},True),({'data':[{'id':'123','text':'Source'}],'errors':[{'title':'Partial'}]},True)]:
                with patch.object(tools.httpx,'get',return_value=httpx.Response(200,json=raw)):
                    result=tools.dispatch(con,shift_id='fixture',generation=shift['generation'],name='nbn_x',args={'query':'bitcoin'})
                self.assertEqual(result['ok'],expected)
                if expected and raw.get('errors'):self.assertTrue(result['partial'])

    def test_pdf_page25_pixels_allowed_only_for_reporter(self):
        data=pdf_bytes([f'Physical page {i}' for i in range(1,26)])
        original=httpx.Client
        with patch.object(visuals.httpx,'Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(
                lambda req:httpx.Response(200,content=data)),**kw)),patch.object(pdf.sources,'_assert_public_http_url'):
            pixels,meta=visuals.pdf_page('https://example.com/report.pdf',25,deadline=time.monotonic()+20,reporter=True)
            self.assertTrue(pixels.startswith(b'\x89PNG'));self.assertEqual(meta['page'],25)
            with self.assertRaisesRegex(ValueError,'first 20'):
                visuals.pdf_page('https://example.com/report.pdf',25,deadline=time.monotonic()+20)
