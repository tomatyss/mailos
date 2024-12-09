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
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "anthropic": ("https://anthropic.readthedocs.io/en/latest/", None),
    "openai": ("https://platform.openai.com/docs/", None),
}
