.PHONY: black pylint pytest all

black:
	black --check --verbose ./src

pylint:
	pylint ./src

pytest:
	pytest ./tests

all: black pylint pytest
