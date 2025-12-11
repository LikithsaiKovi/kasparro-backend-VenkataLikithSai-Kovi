.PHONY: up down build logs test format

up:
	docker-compose up --build -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

test:
	docker-compose run --rm api pytest -q

format:
	docker-compose run --rm api bash -lc "ruff check --fix . || true"


