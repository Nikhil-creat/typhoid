.PHONY: up down runner test lint
up:      ; cp -n .env.example .env; docker compose up --build
down:    ; docker compose down -v
runner:  ; docker build -t typhoid/runner:latest workers/runner
kafka:   ; docker compose --profile kafka up --build
test:    ; cd agents && pytest -q && cd ../backend && pytest -q
