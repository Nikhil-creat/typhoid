FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 git nodejs npm && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest && useradd -u 10002 -m runner
COPY agent.py /agent.py
USER runner
CMD ["sleep", "infinity"]
