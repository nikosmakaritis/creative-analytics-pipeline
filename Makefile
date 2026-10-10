.PHONY: all extract generate build validate notebook open sql

all: extract generate build validate notebook open

extract:
	uv run python -m creative_analytics.extract_creatives

generate:
	uv run python -m creative_analytics.generate_audience

build:
	uv run python -m creative_analytics.build_warehouse

validate:
	uv run python -m creative_analytics.validate

notebook:
	uv run jupyter nbconvert --to notebook --execute --inplace notebooks/creative_analysis.ipynb

open:
	uv run jupyter notebook notebooks/creative_analysis.ipynb

sql:
	uv run duckdb creative_analytics.duckdb
