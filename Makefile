.PHONY: run
run: 
	uvicorn app.main:application --reload

.PHONY: test
test:
	.venv/bin/python -m pytest tests -q

.PHONY: test-cov
test-cov:
	.venv/bin/python -m coverage run -m pytest tests -q
	.venv/bin/python -m coverage report -m

.PHONY: test-cov-html
test-cov-html:
	.venv/bin/python -m coverage run -m pytest tests -q
	.venv/bin/python -m coverage html

.PHONY: makemigrations
makemigrations:
	@if [ -z "$(name)" ]; then \
			tortoise makemigrations; \
	else \
			tortoise makemigrations --name $(name); \
	fi

.PHONY: pending-migrations
pending-migrations:
	@tortoise heads

.PHONY: migrate-up
migrate-up:
	@tortoise upgrade

.PHONY: migrate-down
migrate-down:
	@if [ -z "$(version)" ]; then \
			tortoise downgrade; \
	else \
			tortoise downgrade main $(version); \
	fi

.PHONY: shell
shell:
	@tortoise shell


.PHONY: seed-roles
seed-roles:
	@python3 -m app.orm.seeds.permission_roles
