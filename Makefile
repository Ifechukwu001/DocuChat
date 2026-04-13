run: 
	uvicorn app.main:application --reload

test:
	.venv/bin/python -m pytest tests -q

test-cov:
	.venv/bin/python -m coverage run -m pytest tests -q
	.venv/bin/python -m coverage report -m

test-cov-html:
	.venv/bin/python -m coverage run -m pytest tests -q
	.venv/bin/python -m coverage html

makemigrations:
	@tortoise migrate --name $(name)

pending-migrations:
	@tortoise heads

migrate-up:
	@tortoise upgrade

migrate-down:
	@if [ -z "$(version)" ]; then \
		tortoise downgrade; \
	else \
		tortoise downgrade -v $(version); \
	fi