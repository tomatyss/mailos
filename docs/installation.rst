Installation
============

This guide will help you install MailOS and its dependencies.

Requirements
-----------

* Python 3.8 or higher
* pip package manager
* Virtual environment (recommended)

Basic Installation
----------------

Install using pip::

    pip install mailos

Development Installation
---------------------

For development, clone the repository and install in editable mode::

    git clone https://github.com/tomatyss/mailos.git
    cd mailos
    pip install -e ".[dev]"

This will install additional development dependencies like:

* pytest for testing
* black for code formatting
* flake8 for linting
* sphinx for documentation

Documentation Dependencies
-----------------------

To build the documentation, install the docs extras::

    pip install -e ".[docs]"

This includes:

* sphinx
* sphinx-rtd-theme
* sphinx-autobuild
* sphinxcontrib-mermaid

Tool Dependencies
--------------

Different tools may require additional dependencies:

Weather Tool::

    pip install requests  # For OpenWeatherMap API

PDF Tool::

    pip install PyPDF2  # For PDF manipulation
    pip install reportlab  # For PDF creation

Verification
----------

Verify the installation::

    python -c "import mailos; print(mailos.__version__)"

This should print the version number without errors.

Next Steps
---------

* Read the :doc:`quickstart` guide to get started
* Configure your environment with :doc:`configuration`
* Learn about extending with :doc:`guides/tools`
