# Official multi-platform Ollama 0.33.3 manifest, verified 2026-09-09.
FROM ollama/ollama:0.33.3@sha256:32931b46719f673c05fdbaa81ccb26da18ea4a1c57590a754874ab28ba269eb2
ENV OLLAMA_HOST=[::]:11434 \
    OLLAMA_MODELS=/models \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_KEEP_ALIVE=30m \
    NBN_EMBED_MODEL=nomic-embed-text:v1.5
COPY start.sh /start.sh
ENTRYPOINT ["sh", "/start.sh"]
