# Build from repo root:  docker build -f agents/Dockerfile .
FROM python:3.12-slim AS build
WORKDIR /w
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY agents/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* \
 && useradd -u 10001 -m app
WORKDIR /srv
COPY --from=build /install /usr/local
COPY agents/typhoid_agents ./typhoid_agents
COPY rag/typhoid_rag ./typhoid_rag
COPY workers ./workers
ENV PYTHONPATH=/srv
USER 10001
CMD ["python", "-m", "typhoid_agents.worker"]
