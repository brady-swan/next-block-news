"""Verify image input on the same resumed compatibility session, not a news run."""
import json
import os
from openai_codex import LocalImageInput, TextInput
from local_probe import CONTROL, WORK, checked_thread, client, require_pass, runtime_env

os.environ.clear()
os.environ.update(runtime_env())
os.chdir(WORK)
require_pass()
with client() as codex:
    thread = checked_thread(codex, resume=True)
    result = thread.run([
        TextInput(text='Read the attached test image only. What is the publication date shown '
                  'at the top, and the maximum purchase amount in its first table row? '
                  'This is a visual compatibility check, not a news assignment. No tools or changes.'),
        LocalImageInput(path=str(WORK / 'treasury-pdf-smoke.png')),
    ], effort='medium', service_tier='default')
    payload = {'thread_id': thread.id, 'status': str(result.status),
               'response': result.final_response,
               'usage': result.usage.model_dump(mode='json') if result.usage else None}
    (CONTROL / 'vision-smoke.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload), flush=True)
