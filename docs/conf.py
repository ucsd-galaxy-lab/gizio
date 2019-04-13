# See http://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------

project = 'gizio'
author = 'UC San Diego Galaxy Lab'
copyright = '2019, UC San Diego Galaxy Lab'

# -- General configuration ---------------------------------------------------

extensions = [
    'nbsphinx',
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinxcontrib.apidoc',
]
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**.ipynb_checkpoints']

# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'

# -- Options for extensions --------------------------------------------------

# sphinx.ext.autodoc
autodoc_member_order = 'bysource'

# sphinx.ext.intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'astropy' : ('http://docs.astropy.org/en/stable/', None),
    'unyt': ('https://unyt.readthedocs.io/en/stable/', None),
}

# sphinxcontrib.apidoc
apidoc_module_dir = '../gizio'
apidoc_output_dir = 'api'
apidoc_excluded_paths = []
apidoc_separate_modules = True
apidoc_toc_file = False
apidoc_module_first = True
apidoc_extra_args = []

# -- Custom script -----------------------------------------------------------

from pathlib import Path
from subprocess import run

def download_data(app):
    run('make data', cwd=Path(__file__).parents[1], shell=True)

def setup(app):
    app.connect('builder-inited', download_data)
