# Contributing

The whole development workflow is managed by a Makefile. [conda](https://docs.conda.io) is the only prerequisite to start developing. Other required tools will be installed in the development conda environment.

* Manage environment:
    * `make init` to create the conda environment and do some other initialization.
    * `make up` to update the conda environment.
    * `source ./activate` to activate the conda environment.
* Edit code:
    * `make fmt` to format source code consistently. Certain rules are forced automatically so we humans don't need to care that much.
    * `make lint` until all pass.
    * `make test` until all pass.
* Edit doc:
    * `make doc` to build and open the doc for review.
* Release:
    * Make sure changelog is up to date.
    * Change `__version__` (in `gizio.__about__`) from dev to production. From `1.0.0.dev0` to `1.0.0` for example. Commit the change.
    * `make build`.
    * `make publish-test` to test publish on [TestPyP](https://test.pypi.org).
    * `make publish` to publish officially on [PyPI](https://pypi.org).
    * Change `__version__` back to dev. From `1.0.0` to `1.1.0.dev0` for example. Commit the change.
