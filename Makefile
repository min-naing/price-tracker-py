lint:
	uv run ruff check src/

format:
	uv run ruff format src/

typecheck:
	uv run pyright

test:
	uv run pytest

start:
	uv run price-tracker