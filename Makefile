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

env:
	conda env create -f environment.yml -p env
	env/bin/pip install -e .

.PHONY: up
up:
	conda env update -f environment.yml -p env
	env/bin/pip install -e .

.PHONY: fmt
fmt:
	black gizio setup.py

.PHONY: lint
lint:
	pylint gizio

.PHONY: data
data: data/FIRE_M12i_ref11
data/FIRE_M12i_ref11:
	mkdir -p data
	cd data && curl http://yt-project.org/data/FIRE_M12i_ref11.tar.gz | tar xz

.PHONY: doc
doc:
	jupyter nbconvert --to notebook --inplace --ClearOutputPreprocessor.enabled=True docs/*.ipynb
	rm -rf docs/api
	cd docs && make html
	$(OPEN) docs/_build/html/index.html
