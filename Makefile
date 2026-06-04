.PHONY: black lint test all release release-check guard-wsl

# The release recipes rely on Unix tools (grep, sed, git). When make is invoked
# from native Windows (PowerShell/cmd) $(OS) is "Windows_NT" and these break, so
# guard against it and point the user to WSL.
ifeq ($(OS),Windows_NT)
guard-wsl:
	@echo "ERROR: run 'make release' from WSL, not PowerShell/cmd."
	@exit 1
else
guard-wsl:
	@:
endif

VERSION := $(shell grep -m1 '^version' pyproject.toml | sed -E 's/version *= *"([^"]+)"/\1/')

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

release-check: guard-wsl
	@test -n "$(VERSION)" || { echo "ERROR: could not read version from pyproject.toml"; exit 1; }
	@test -z "$$(git status --porcelain)" || { echo "ERROR: working tree is not clean, commit or stash your changes first"; exit 1; }
	@git fetch --tags --quiet
	@! git rev-parse "v$(VERSION)" >/dev/null 2>&1 || { echo "ERROR: tag v$(VERSION) already exists, bump the version in pyproject.toml"; exit 1; }
	@echo "Checks passed for v$(VERSION)"

release: release-check
	@echo "Creating and pushing tag v$(VERSION)"
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	git push origin "v$(VERSION)"
