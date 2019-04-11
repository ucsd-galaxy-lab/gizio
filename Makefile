env: environment.yml
	conda env create -f environment.yml -p env
	env/bin/pip install -e .

.PHONY: up
up: environment.yml | env
	conda env update -f environment.yml -p env
	env/bin/pip install -e .

.PHONY: fmt
fmt:
	black gizio setup.py

.PHONY: lint
lint:
	pylint gizio
