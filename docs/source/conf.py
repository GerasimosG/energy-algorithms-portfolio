"""Energy Algorithms — Sphinx configuration."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.abspath('.'), '..', '..', 'src'))

extensions = [
 'sphinx.ext.autodoc',
 'sphinx.ext.napoleon',
 'sphinx.ext.viewcode',
]

project = 'Energy Algorithms'
copyright = '2026, GerryBerry'
author = 'GerryBerry'

version = '0.3.0'
release = '0.3.0'

templates_path = ['_templates']
exclude_patterns: list[str] = []

# -- Options for autodoc ----------------------------------------------------
autodoc_default_options = {
 'members': True,
 'undoc-members': True,
 'show-inheritance': True,
}

# -- Options for napoleon (NumPy-style docstrings) -------------------------
napoleon_google_docstring = False
napoleon_numpy_docstring = True

# -- Options for HTML output -----------------------------------------------
html_theme = 'alabaster'
html_static_path: list[str] = []
