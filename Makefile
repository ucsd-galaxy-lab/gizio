# Initialize a development environment
.PHONY: init
init: env

env: environment.yml
	conda env create -f environment.yml -p env
	env/bin/pip install -e .

# Update the development environment
.PHONY: update
update: environment.yml | env
	conda env update -f environment.yml -p env
	env/bin/pip install -e .
