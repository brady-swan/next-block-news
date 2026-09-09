#!/bin/sh
# Only this private companion bootstraps a model. NBN never waits for it to start.
set -eu
ollama serve &
server_pid=$!
trap 'kill -TERM "$server_pid" 2>/dev/null || true' TERM INT EXIT
attempt=0
until OLLAMA_HOST=http://127.0.0.1:11434 ollama list >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo 'Embedding daemon did not become ready' >&2
    exit 1
  fi
  sleep 2
done
if ! OLLAMA_HOST=http://127.0.0.1:11434 ollama show "$NBN_EMBED_MODEL" >/dev/null 2>&1; then
  if ! OLLAMA_HOST=http://127.0.0.1:11434 timeout 180 ollama pull "$NBN_EMBED_MODEL"; then
    echo 'Model bootstrap unavailable; NBN keyword fallback remains usable. Restart this companion to retry.' >&2
  fi
fi
wait "$server_pid"
