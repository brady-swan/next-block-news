"""Opt-in GPO margin cleanup: real layout shape, no network or inference."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from nbn import reporter_pdf as pdf, reporter_tools as tools, reporter_store as rs, visual_render, visuals
from tests.support import temporary_store
from tests.test_pdf_source import pdf_bytes


PASSAGE = '(e) EFFECTIVE DATE.—The amendments made by this section shall apply to dispositions after the date of the introduction of this Act.'


def layout_page(number=51, bodies=None):
    bodies = bodies or ['Unchanged body text.']*25
    rows = [r'           G:\M\19\TEST\TEST_001.XML', '', f'                      {number}']
    for i, body in enumerate(bodies,1):
        rows.append(' '*(33 if i<10 else 31)+str(i)+' '+body)
    rows += ['', r'           G:\V\G\091426\G091426.015.xml   (1088227|5)',
             '           September 14, 2026 (2:29 p.m.)',
             'VerDate Nov 24 2008  Jkt 000000  PO 00000  Frm 00051  Fmt 6652  Sfmt 6201']
    return '\n'.join(rows)+'\n'


def extract_layout(raw, **kwargs):
    def spawn(argv, **_):
        assert '-layout' in argv
        Path(argv[-1]).write_text(raw+'\f')
        process=Mock();process.poll.return_value=0;process.returncode=0
        return process
    with patch.object(pdf.subprocess,'Popen',side_effect=spawn):
        return pdf.extract(pdf_bytes(['source']),start_page=51,page_count=1,text_mode='legislation',**kwargs)


class LegislativeLayoutTests(unittest.TestCase):
    def setUp(self):
        self.bodies=['Unchanged body text.']*25
        self.bodies[5:8]=['(e) EFFECTIVE DATE.—The amendments made by',
                          'this section shall apply to dispositions after the date of',
                          'the introduction of this Act.']
        self.bodies[10]='1986 remains a substantive number; before January 1, 2028.'
        self.raw=layout_page(bodies=self.bodies)

    def spec(self):
        return {'source':'House bill text','source_fetch_id':'r1','passage':PASSAGE,
                'document_title':'Proposed effective date','location':'Section 301(e), page 51',
                'highlights':['after the date of the introduction of this Act']}

    def test_only_margin_tokens_removed_with_real_column_shift(self):
        clean,meta=pdf.legislative_page(self.raw,51)
        self.assertEqual(meta['margin_end_columns'],[33,34])
        self.assertEqual(meta['removed_label_count'],25)
        self.assertIn(PASSAGE,visual_render.normalized(clean))
        self.assertIn(self.bodies[10],clean)
        before=self.raw.splitlines();after=clean.splitlines()
        for old,new in zip(before,after):
            if old!=new:
                self.assertEqual(len(old),len(new))
                removed=''.join(a for a,b in zip(old,new) if a!=b)
                self.assertTrue(removed.isdigit())
                self.assertTrue(all(b==' ' for a,b in zip(old,new) if a!=b))

    def test_ambiguous_and_unsupported_layouts_rejected(self):
        variants=[self.raw.replace('G:\\M\\19','Other header'),
                  self.raw.replace('Sfmt','OtherFooter'),
                  self.raw.replace(' '*33+'7 ',' '*33+'9 ',1),
                  self.raw.replace(' '*31+'10 ',' '*40+'10 ',1),
                  self.raw.replace(' '*33+'8 ','unexplained line\n'+' '*33+'8 ',1),
                  self.raw.replace(' '*33+'8 ','(8) ',1),
                  layout_page(bodies=['1 2 3','4 5 6']),
                  '1 Item one\n2 Item two\n3 Item three',
                  'Year   Value\n2024  30\n2025  40']
        for raw in variants:
            with self.subTest(raw=raw[:80]),self.assertRaisesRegex(ValueError,'Unrecognized'):
                pdf.legislative_page(raw,51)
        with self.assertRaises(ValueError):pdf.legislative_page(self.raw,50)

    def test_provenance_retained_and_quote_validation_stays_strict(self):
        read=extract_layout(self.raw)
        self.assertEqual(read['layout_provenance']['raw_pages'],[{'page':51,'text':self.raw}])
        self.assertEqual(read['layout_provenance']['version'],pdf.LEGISLATIVE_LAYOUT_VERSION)
        self.assertEqual(read['pages_scanned'],[51,51])
        self.assertIn('raw layout is retained',read['limitations'])
        receipt={**read,'fetch_id':'r1','retrieval_kind':'direct_fetch','final_url':'https://example.com/source.pdf'}
        valid=visual_render.validate('excerpt',self.spec(),[receipt])
        self.assertEqual(valid['normalization'],'whitespace-only')
        for changed in (PASSAGE.replace('after','before'),PASSAGE.replace('Act.','Act!'),PASSAGE.replace('Act.','Act in 2028.')):
            with self.assertRaisesRegex(ValueError,'contiguous verbatim'):
                visual_render.validate('excerpt',{**self.spec(),'passage':changed},[receipt])
        plain={**receipt,'text':self.raw}
        with self.assertRaisesRegex(ValueError,'contiguous verbatim'):
            visual_render.validate('excerpt',self.spec(),[plain])
        with temporary_store() as con:
            asset=visuals.render_asset(con,run_id='test',candidate_id='test',kind='excerpt',preset='landscape',
                 spec=self.spec(),evidence=[receipt],alt_text='Proposed effective-date clause.',purpose='Show the clause.')
            serialized=json.dumps(asset['metadata'])
            self.assertIn('layout_provenance',serialized)
            self.assertIn(pdf.LEGISLATIVE_LAYOUT_VERSION,serialized)
            self.assertLess(len(serialized.encode()),128*1024)

    def test_no_hyphenation_or_section_number_repair(self):
        bodies=copy.copy(self.bodies);bodies[0]='Section 1091 and 30 days are unchanged.'
        bodies[1:3]=['substan-','tially identical assets']
        read=extract_layout(layout_page(bodies=bodies))
        self.assertIn('Section 1091 and 30 days',read['text'])
        self.assertIn('substan-',read['text']);self.assertNotIn('substantially',read['text'])

    def test_bounds_modes_and_continuation(self):
        for kwargs in ({'text_mode':'unknown'},{'text_mode':'legislation','query':'a'}):
            with patch.object(pdf.subprocess,'Popen') as spawn,self.assertRaises(ValueError):
                pdf.extract(pdf_bytes(['source']),**kwargs)
            spawn.assert_not_called()
        with patch.object(pdf,'MAX_LAYOUT_BYTES',100),self.assertRaisesRegex(ValueError,'select fewer pages'):
            extract_layout(self.raw)
        # Fill one recognized body row up to the bounded provenance ceiling.
        # Compact but recognized gutter leaves enough prose after space collapse.
        compact=self.raw.replace(' '*33,' '*5).replace(' '*31,' '*4)
        spare=pdf.MAX_LAYOUT_BYTES-len(compact.encode())-1
        raw=compact.replace(self.bodies[0],self.bodies[0]+'x'*spare,1)
        first=extract_layout(raw)
        self.assertIsNotNone(first['next_cursor'])
        self.assertEqual(first['next_cursor']['pdf_text_mode'],'legislation')
        second=extract_layout(raw,text_offset=first['next_cursor']['pdf_text_offset'])
        self.assertIsNone(second['next_cursor'])
        self.assertEqual(second['layout_provenance'],first['layout_provenance'])

    def test_tool_schema_dispatch_and_plain_default(self):
        schema=next(t for t in tools.TOOLS if t['name']=='nbn_fetch')
        self.assertEqual(schema['inputSchema']['properties']['pdf_text_mode']['enum'],['plain','legislation'])
        read=extract_layout(self.raw)
        with temporary_store() as con:
            shift=rs.start(con,worker_id='test',shift_id='layout-test')
            with patch.object(pdf,'fetch',return_value=read) as fetch:
                result=tools.dispatch(con,shift_id='layout-test',generation=shift['generation'],name='nbn_fetch',
                     args={'url':'https://example.com/a.pdf','start_page':51,'page_count':1,'pdf_text_mode':'legislation'})
                self.assertEqual(fetch.call_args.kwargs['text_mode'],'legislation')
                self.assertEqual(result['layout_provenance'],read['layout_provenance'])
        plain=pdf.extract(pdf_bytes(['Simple source with 2028 and 30 days.']),page_count=1)
        self.assertIn('2028 and 30 days',plain['text'])
        self.assertNotIn('layout_provenance',plain)


if __name__=='__main__':unittest.main()
