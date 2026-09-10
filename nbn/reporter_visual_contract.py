"""The existing renderer's input shape, exposed to the reporter rather than hidden in code."""
import json

def string(maximum): return {'type':'string','minLength':1,'maxLength':maximum}

POINT = {'type':'object','required':['label','value','date','source_fetch_id'],
         'properties':{'label':string(28),'value':{'type':['number','null']},'date':string(40),'source_fetch_id':string(200)},
         'additionalProperties':False}
COMMON = {'source':string(70),'date':string(40),
          'color':{'type':'string','enum':['blue','red','yellow','green','orange','purple']}}
CHART = {'type':'object','required':['source','headline','unit','period','points'],
         'properties':{**COMMON,'headline':string(110),'eyebrow':string(60),'unit':string(40),'period':string(80),
            'points':{'type':'array','minItems':2,'maxItems':8,'items':POINT},
            'metric':{'type':'string','enum':['none','sum','change','last']},
            'x_axis':{'type':'string','enum':['time','category']}},'additionalProperties':False}
PASSAGE = {'type':'object','required':['source','source_fetch_id','passage'],
           'properties':{**COMMON,'source_fetch_id':string(200),'passage':string(1100),'speaker':string(100),
                'document_title':string(250),'location':string(150),
                'highlights':{'type':'array','maxItems':4,'items':string(300)},
                'paragraph_breaks':{'type':'array','maxItems':4,'items':{'type':'integer','minimum':1}}},
           'additionalProperties':False}
SPEC = {'oneOf':[CHART,PASSAGE]}
EXAMPLE = {'operation':'render','kind':'bar','preset':'landscape','evidence_ids':['RECEIPT_ID'],
    'spec':{'headline':'Revenue by quarter','source':'Company results','unit':'USD millions',
        'period':'Q2 year-over-year','metric':'none','points':[
            {'label':'Q2 2025','value':100,'date':'2025-06-30','source_fetch_id':'RECEIPT_ID'},
            {'label':'Q2 2026','value':32,'date':'2026-06-30','source_fetch_id':'RECEIPT_ID'}]},
    'alt_text':'Revenue was $100 million in Q2 2025 and $32 million in Q2 2026.',
    'purpose':'Show the size of the revenue change.'}
GUIDANCE = ('Render requires kind, spec, evidence_ids, alt_text and purpose. Use headline/points, NOT title/data. '
    'Chart points need actual retained source_fetch_id values. Comparison has exactly two points. '
    'Line defaults to a time axis: distinct increasing YYYY-MM-DD dates; use x_axis=category for categories. '
    'Quote requires speaker and a contiguous verbatim passage of at most600 characters; excerpt allows1100. '
    'Quote/excerpt source_fetch_id must reference directly fetched text, not paraphrases. '
    'Look at returned pixels before selecting the image. Complete EXAMPLE ONLY—replace all illustrative facts and receipt IDs: '
    + json.dumps(EXAMPLE))


def check(args):
    operation=args.get('operation')
    fields={'inspect':['asset_id'],'render':['kind','spec','evidence_ids','alt_text','purpose'],
            'pdf_page':['url'],'source_image':['url']}.get(operation)
    if fields is None: raise ValueError('unsupported visual operation')
    missing=[key for key in fields if key not in args or args[key] in (None,'',[])]
    if operation=='render' and isinstance(args.get('spec'),dict):
        spec=args['spec']; kind=args.get('kind')
        shape=CHART if kind in {'bar','line','comparison'} else PASSAGE
        missing += ['spec.'+key for key in shape['required'] if key not in spec or spec[key] in (None,'',[])]
        if kind=='quote' and not spec.get('speaker'): missing.append('spec.speaker')
        unknown=set(spec)-set(shape['properties'])
        if unknown: missing += ['unexpected spec.'+key for key in sorted(unknown)]
        if isinstance(spec.get('points'),list):
            for i,point in enumerate(spec['points']):
                if not isinstance(point,dict): missing.append(f'spec.points[{i}] must be an object'); continue
                missing += [f'spec.points[{i}].{key}' for key in POINT['required'] if key not in point]
    if missing: raise ValueError('Visual input fields: '+', '.join(missing)+'. See the nbn_visual schema and complete render example.')
