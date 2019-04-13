Development
===========

The whole development workflow is managed by a Makefile. The only prerequisite is `conda <https://docs.conda.io>`_.

* Manage environment:
    * ``make env`` to create the conda environment.
    * ``make up`` to update the conda environment.
    * ``source ./activate`` to activate the conda environment.
* Edit code:
    * ``make fmt`` to format source code consistently.
    * ``make lint`` until it passes.
* Edit doc:
    * ``make doc`` to build and open the doc for review.
