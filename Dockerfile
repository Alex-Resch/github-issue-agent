FROM python:3.12-slim

WORKDIR /code

COPY pyproject.toml uv.lock ./

RUN pip install uv --no-cache-dir && \
    uv sync --frozen --no-dev

COPY src/ src/

ENV PYTHONPATH=/code
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
