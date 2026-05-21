.PHONY: black lint test all

isort:
	isort ./src
	isort ./tests

black:
	black --verbose ./src
	black --verbose ./tests

lint:
	pylint ./src
	pylint ./tests

test:
	pytest ./tests

all: isort black lint test
