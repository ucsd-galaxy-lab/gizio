Development
===========

The whole development workflow is managed by a Makefile. The only prerequisite is `conda <https://docs.conda.io>`_ for environment management.

* Manage environment:
    * ``make env`` to create the conda env.
    * ``make up`` to update the conda env.
    * ``source ./activate`` to activate the conda env.
* Edit code:
    * ``make fmt`` to format source code consistently.
    * ``make lint`` until all pass.
    * ``make test`` until all pass.
* Edit doc:
    * ``make doc`` to build and open the doc for review.
