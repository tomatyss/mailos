MailOS Documentation
====================

MailOS is an AI-powered email monitoring and response system that supports multiple LLM providers.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   configuration
   guides/tools
   guides/adding_vendors
   api/modules

Features
--------

* Multiple LLM Provider Support
* IMAP Email Monitoring
* Automatic Response Generation
* Web-based Configuration Interface
* Extensible Tool System

Getting Started
--------------

Installation::

    pip install mailos

Basic usage::

    from mailos import check_email_app
    check_email_app()

For more detailed information, see the :doc:`quickstart` guide.

Tool System
----------

MailOS includes a powerful tool system that allows you to extend its capabilities:

* Weather information
* PDF manipulation
* Python code execution
* Bash command execution
* And more...

Learn how to create and manage tools in the :doc:`guides/tools` guide.

Indices and tables
================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
