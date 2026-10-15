# Judge / reproduction image. Runtime is stdlib-only Python; model inference
# goes to the OpenAI-compatible Apertus endpoint given by LLM_NAME,
# LLM_BASE_URL and LLM_API_KEY. Dev data, the pinned evaluator code and the
# paper prompts are downloaded (hash-verified) at run time, never baked in.
FROM python:3.12.7-slim

WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY src ./src
COPY manifests ./manifests
COPY results ./results
RUN mkdir -p runs data

ENTRYPOINT ["python", "-m", "uzh_rsd.cli"]
CMD ["run"]
