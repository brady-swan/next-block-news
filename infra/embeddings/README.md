# Private NBN embedding companion

Deploy this directory as its own Railway service `nbn-embeddings`, same production project
and region as NBN. One replica, persistent `/models` volume, port11434, **no public domain**.
Use the pinned official image. Startup checks the persisted model before a bounded download.
No vendor API key or laptop dependency. This is a CPU embedding service, not another writer.

NBN config: `MEMORY_EMBED_URL=http://nbn-embeddings.railway.internal:11434` and
`MEMORY_EMBED_MODEL=nomic-embed-text:v1.5`. The model's returned digest enters every cache key.
One model/parallel request and one CPU inference thread; start with modest replica limits,
measure real memory/cold+warm latency before enabling the caller. Model download274MB is not
resident RAM. The official runtime image also contains unused accelerator libraries.

Indexing runs in NBN's separate background thread/SQLite connection, bounded batches, no
network in a write transaction. A Writer query has bounded lookup/embedding deadlines.
Missing model, bad response, service outage or pending index degrades to ranked keywords.
Neither NBN startup nor its minute worker awaits the companion. Clear `MEMORY_EMBED_URL`
and redeploy NBN to disable semantic search without removing stored notes or vectors.

Smoke: `/api/tags` model digest; `/api/embed` 768 finite values; cold/warm query and batch
latency; cgroup memory+CPU; restart then confirm digest/model cache; no public domain.
Use held-out NBN queries with synonyms plus exact-ID and different-event controls. Record
measurement and hosting-cost assumptions in the release findings; do not equate recall
similarity with factual support or claim editorial quality from fixture tests.
