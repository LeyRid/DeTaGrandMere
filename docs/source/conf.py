# DeTaGrandMere documentation build configuration file

import os
import sys

sys.path.insert(0, os.path.abspath("../../"))

project = "DeTaGrandMere"
copyright = "2026, DeTaGrandMere Contributors"
author = "DeTaGrandMere Team"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Napoleon settings for NumPy-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": False,
    "special-members": False,
    "inherited-members": True,
    "show-inheritance": True,
}

autodoc_docstring_scope = {
    "class": "current",
    "method": "current",
    "function": "current",
}

# Viewcode settings
viewcode_import = "yes"
viewcode_ignore = [""]
