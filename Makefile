# Makefile for common tasks

.PHONY: update-env format lint test run shell

# Update or create conda environment from environment.yml
update-env:
	conda env update -f environment.yml

# Format code with Black and isort
format:
	black .
	isort .

# Check code style
lint:
	flake8 .

# Run tests
test:
	pytest --maxfail=1 --disable-warnings --verbose

# Run the trading bot
run:
	python tradingbot.py

# Launch an interactive shell
shell:
	conda activate tradingbot_env && ipython

# (setup deprecated; use update-env and other targets)
