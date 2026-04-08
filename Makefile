run: 
	uvicorn app.main:application --reload

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