# Contributing

## Workflow

The whole development workflow is managed by a Makefile. [conda](https://docs.conda.io) is the only prerequisite to start developing. Other required tools would be available in the created conda environment.

* Manage environment:
    * `make env` to create the conda environment.
    * `make up` to update the conda environment.
    * `source ./activate` to activate the conda environment.
* Edit code:
    * `make fmt` to format source code consistently. Some rules are forced automatically so we humans don't need to care that much.
    * `make lint` until all pass.
    * `make test` until all pass.
* Edit doc:
    * `make doc` to build and open the doc for review.
* Release:
    * Change `__version__` (in `gizio.__about__`) from `dev` to production, `1.0.0` for example.
    * `make build`.
    * `make publish-test` to publish on `TestPyPI <https://test.pypi.org/>`_ until it looks good.
    * Commit and tag: `git commit -am "v1.0.0" && git tag v1.0.0`.
    * `make publish` to publish on `PyPI <https://pypi.org/>`_.
    * Modify `__version__` to `dev`, `1.1.0.dev0` for example, so it stays in dev until the next release.
