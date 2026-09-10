"""Reporter adapter for existing search cache and provider health; no model/provider changes."""
import time
from . import config, search, store

FALLBACK = ('Search failed, not an empty search. Use your native web search, an exact source URL, '
            'or nbn_x for an original post. Search results are pointers, not inspected evidence.')


def google(con, query, run_id):
    identity=search.request_identity(query, max_results=8)
    if not identity.get('query'): return {'ok':False,'error_kind':'empty_query'}
    cached=store.search_cache_get(con,identity)
    if cached is not None:
        store.record_search_activity(con,run_id,'cache_hit')
        return {'ok':True,'cached':True,'results':cached,'kind':'search_pointers'}
    if not config.SERPAPI_KEY:
        return {'ok':False,'error_kind':'unconfigured','message':FALLBACK}
    state=store.search_provider_state(con)
    until=float(state.get('next_search_at') or 0)
    if state.get('state') in {'quota_exhausted','degraded','rate_limited'} and until>time.time():
        return {'ok':False,'error_kind':state['state'],'retry_at_epoch':until,'message':FALLBACK}
    token=''
    if state.get('state')=='quota_exhausted':
        token=store.claim_search_probe(con,'serpapi',lease_seconds=config.SERPAPI_TIMEOUT_SECONDS+15)
        if not token: return {'ok':False,'error_kind':'provider_probe_in_progress','message':FALLBACK}
    store.record_search_activity(con,run_id,'provider_http_attempt')
    try:
        results=search.google(identity['query'],max_results=8)
    except search.SearchError as exc:
        store.record_search_failure(con,'serpapi',exc.kind,str(exc),probe_token=token,
            retry_after_seconds=exc.retry_after_seconds,cooldown_seconds=config.SEARCH_PROVIDER_COOLDOWN_SECONDS)
        store.record_search_activity(con,run_id,'provider_failure',exc.kind)
        return {'ok':False,'error_kind':exc.kind,'error_message':str(exc)[:200],
                'retry_after_seconds':exc.retry_after_seconds,'message':FALLBACK}
    # Ensure even a first successful reporter-only query has a provider-health row.
    with con: store._ensure_search_provider_row(con,'serpapi')
    store.record_search_success(con,'serpapi',probe_token=token)
    results=store.search_cache_put(con,identity,results,ttl_seconds=config.SEARCH_CACHE_TTL_SECONDS)
    return {'ok':True,'cached':False,'results':results,'kind':'search_pointers'}
