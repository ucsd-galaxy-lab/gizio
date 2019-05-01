UNAME = $(shell uname)
ifeq ($(UNAME),Darwin)
	OPEN = open
endif
ifeq ($(UNAME),Linux)
	OPEN = xdg-open
endif

.PHONY: help
help:
	cat Makefile

# env

.PHONY: init
init: env install interpreters

.PHONY: up
up: env install
	conda env update -f environment.yml -p env

env:
	conda env create -f environment.yml -p env

.PHONY: install
install: env
	mv pyproject.toml pyproject.toml.backup
	env/bin/pip install -e .
	mv pyproject.toml.backup pyproject.toml

# code

.PHONY: fmt
fmt:
	black docs/conf.py src tests setup.py

.PHONY: lint
lint:
	pylint src

.PHONY: test
test: data
	PATH=$(PWD)/interpreter:$(PATH) tox

# doc

.PHONY: doc
doc: data
	# Strip notebook output
	jupyter nbconvert --to notebook --inplace --ClearOutputPreprocessor.enabled=True docs/*.ipynb
	# Remove existing API docs to build from scratch
	rm -rf docs/{_build,api}
	# Build HTML output
	cd docs && make html
	# Open to review
	$(OPEN) docs/_build/html/index.html

# release

.PHONY: build
build:
	rm -rf build dist
	python setup.py sdist bdist_wheel

.PHONY: publish-test
publish-test:
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

.PHONY: publish
publish:
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# misc

.PHONY: data
data: data/FIRE_M12i_ref11
data/FIRE_M12i_ref11:
	mkdir -p data
	cd data && curl http://yt-project.org/data/FIRE_M12i_ref11.tar.gz | tar xz

PY_VERS = 3.6 3.7
INTERPRETERS = $(addprefix interpreter/python,$(PY_VERS))
.PHONY: interpreters
interpreters: $(INTERPRETERS)
interpreter/python%:
	conda create -p interpreter/envs/python$* python=$*
	cd interpreter && ln -s envs/python$*/bin/python$*
