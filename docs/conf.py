"""Sphinx configuration file."""

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "MailOS"
copyright = "2024, Ivan Iufriakov"
author = "Ivan Iufriakov"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Theme configuration
html_theme = "alabaster"
html_theme_options = {
    "description": "AI-powered email monitoring and response system",
    "github_user": "tomatyss",
    "github_repo": "mailos",
    "fixed_sidebar": True,
}

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Mermaid configuration
mermaid_version = "latest"
mermaid_init_js = """
    mermaid.initialize({
        startOnLoad: true,
        theme: 'default',
        securityLevel: 'loose',
    });
"""

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True

# AutoDoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Output file base name for HTML help builder
htmlhelp_basename = 'mailosdoc'
