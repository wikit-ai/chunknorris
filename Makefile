.PHONY: black pylint pytest all

isort:
	isort ./src
	isort ./tests

black:
	black --verbose ./src
	black --verbose ./tests

pylint:
	pylint ./src
	pylint ./tests

pytest:
	pytest ./tests

all: isort black pylint pytest
