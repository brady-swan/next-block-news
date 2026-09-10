"""Targeted reporter PDF reads, separate from the legacy first-20-page extractor."""
from pathlib import Path
import hashlib
import re
import subprocess
import tempfile
import time
from urllib.parse import urljoin

import httpx

from . import sources

MAX_BYTES = 32 * 1024 * 1024
MAX_PAGES = 500
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
LIMITATIONS = ('PDF text layer only; scanned pages, charts and table layout are not verified. '
               'Extraction does not establish publication date. Page numbers are physical PDF pages.')


def extract(data, *, query='', start_page=1, page_count=5, text_offset=0, deadline=None):
    """Read selected pages or return literal search snippets with their actual page numbers."""
    if len(data) > MAX_BYTES: raise ValueError('PDF exceeds 32 MiB input limit')
    if not data.startswith(b'%PDF-'): raise ValueError('Response is not a PDF')
    if isinstance(start_page, bool) or not isinstance(start_page, int) or not 1 <= start_page <= MAX_PAGES:
        raise ValueError('start_page must be 1–500')
    if isinstance(page_count, bool) or not isinstance(page_count, int) or not 1 <= page_count <= 12:
        raise ValueError('page_count must be 1–12')
    query = str(query).strip()
    if len(query) > 200: raise ValueError('PDF literal query must be at most 200 characters')
    if isinstance(text_offset,bool) or not isinstance(text_offset,int) or not 0<=text_offset<=MAX_OUTPUT_BYTES:
        raise ValueError('pdf_text_offset must be 0–8388608')
    last = MAX_PAGES if query else min(MAX_PAGES, start_page + page_count - 1)
    end = min(deadline or float('inf'), time.monotonic() + 12)
    with tempfile.TemporaryDirectory(prefix='nbn-reporter-pdf-') as directory:
        path, output = Path(directory)/'source.pdf', Path(directory)/'text.txt'
        path.write_bytes(data)
        if time.monotonic() >= end: raise ValueError('PDF extraction deadline')
        proc = subprocess.Popen(['pdftotext','-f',str(start_page),'-l',str(last),'-enc','UTF-8',
                                 '-eol','unix',str(path),str(output)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            while proc.poll() is None:
                if time.monotonic() >= end: raise ValueError('PDF extraction deadline')
                if output.exists() and output.stat().st_size > MAX_OUTPUT_BYTES:
                    raise ValueError('PDF extracted text exceeds 8 MiB limit; select a narrower page range')
                time.sleep(.02)
            if proc.returncode: raise ValueError('PDF cannot be read or requested page is out of range')
            if output.stat().st_size > MAX_OUTPUT_BYTES: raise ValueError('PDF extracted text exceeds 8 MiB limit')
            raw = output.read_text(encoding='utf-8', errors='replace')
        finally:
            if proc.poll() is None: proc.kill()
            proc.wait()
    pages = raw.split('\f')
    if pages and not pages[-1].strip(): pages.pop()
    matches, selected, readable = [], [], False
    for number, text in enumerate(pages, start_page):
        text = re.sub(r'[^\S\n]+', ' ', text).strip()
        readable = readable or any(c.isalnum() for c in text)
        if query:
            # Match across line wraps without turning a substring into a semantic claim.
            text = re.sub(r'\s+', ' ', text)
            at = text.lower().find(query.lower())
            if at < 0: continue
            matches.append(number)
            if len(selected) >= 12: continue
            text = text[max(0,at-600):at+len(query)+1200]
        if text: selected.append(f'[PDF page {number}]\n{text}')
    combined = '\n\n'.join(selected)
    first_label=combined.rfind('[PDF page ',0,text_offset+1)
    continuation_label=(combined[first_label:combined.find('\n',first_label)+1] if text_offset>first_label>=0 else '')
    stop=min(len(combined),text_offset+24000-len(continuation_label))
    clipped = text_offset>0 or stop<len(combined) or len(matches)>12
    next_cursor=None
    if stop<len(combined):
        next_cursor={'start_page':start_page,'page_count':page_count,'pdf_query':query,'pdf_text_offset':stop}
    elif query and len(matches)>12:
        next_cursor={'start_page':matches[12],'page_count':page_count,'pdf_query':query,'pdf_text_offset':0}
    excerpt=continuation_label+combined[text_offset:stop]
    return {'text':excerpt, 'outcome':'ok' if readable else 'evidence_failed',
            'error_kind':'' if readable else 'pdf_no_text', 'query':query,
            'input_bytes':len(data),'document_sha256':hashlib.sha256(data).hexdigest(),
            'match_pages':matches, 'pages_scanned':[start_page, start_page+len(pages)-1] if pages else [],
            'requested_page_range':[start_page,last], 'truncated':clipped,
            'text_offset':text_offset,'next_cursor':next_cursor,
            'next_page':(None if next_cursor else start_page+len(pages)
                         if len(pages)==last-start_page+1 and start_page+len(pages)<=MAX_PAGES else None),
            'limitations':LIMITATIONS + (' Literal search snippets only; a match is not a reading of the full page. '
                'No match means not found in the searched text layer, not absent from images or later pages.' if query else
                ' Only the selected page range was read.') + (' Excerpt clipped; unread remainder is not evidence.' if clipped else '')}


def fetch(url, *, query='', start_page=1, page_count=5, text_offset=0, deadline=None):
    end = min(deadline or float('inf'), time.monotonic()+35)
    current = url
    with httpx.Client(follow_redirects=False, headers={'User-Agent':sources.UA}) as client:
        for _ in range(6):
            sources._assert_public_http_url(current)
            remaining = end-time.monotonic()
            if remaining <= 0: raise ValueError('PDF download deadline')
            with client.stream('GET', current, timeout=min(15,remaining)) as response:
                if response.is_redirect:
                    location=response.headers.get('location')
                    if not location: raise ValueError('PDF redirect without location')
                    current=urljoin(current,location); continue
                response.raise_for_status()
                data=bytearray()
                for part in response.iter_bytes(65536):
                    data.extend(part)
                    if len(data)>MAX_BYTES: raise ValueError('PDF exceeds 32 MiB download limit')
                    if time.monotonic()>=end: raise ValueError('PDF download deadline')
                return {**extract(bytes(data),query=query,start_page=start_page,page_count=page_count,text_offset=text_offset,deadline=end),
                        'final_url':current, 'published_at':'', 'content_type':'application/pdf'}
    raise ValueError('PDF redirect limit')
