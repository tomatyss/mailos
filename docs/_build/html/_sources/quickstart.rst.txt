Quickstart Guide
===============

This guide will help you get started with MailOS quickly.

Installation
-----------

1. Install MailOS using pip::

    pip install mailos

2. Create a configuration file ``email_config.json`` in your working directory::

    {
        "checkers": []
    }

Basic Usage
----------

1. Start the Web Interface
~~~~~~~~~~~~~~~~~~~~~~~~~

Run the following Python code::

    from mailos import check_email_app
    check_email_app()

This will open a web interface in your default browser.

2. Configure Email Checker
~~~~~~~~~~~~~~~~~~~~~~~~

1. Click "Add Checker" to create a new email monitor
2. Fill in the required fields:

   * Checker Name (optional)
   * Email to monitor
   * Email password
   * IMAP Server settings
   * LLM Provider configuration

3. Enable Features:

   * Enable monitoring
   * Auto-reply to emails (optional)

4. Configure LLM:

   * Select provider (OpenAI, Anthropic, or AWS Bedrock)
   * Enter API credentials
   * Choose model
   * Set system prompt

Example Configuration
-------------------

OpenAI Configuration::

    {
        "checkers": [
            {
                "name": "Support Email",
                "monitor_email": "support@example.com",
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "enabled": true,
                "auto_reply": true,
                "llm_provider": "openai",
                "model": "gpt-4",
                "api_key": "your-openai-key"
            }
        ]
    }

Anthropic Configuration::

    {
        "checkers": [
            {
                "name": "Sales Email",
                "monitor_email": "sales@example.com",
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "enabled": true,
                "auto_reply": true,
                "llm_provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "api_key": "your-anthropic-key"
            }
        ]
    }

Next Steps
---------

* Read the :doc:`configuration` guide for detailed configuration options
* Learn about :doc:`guides/adding_vendors` if you want to add support for new LLM providers
* Check the API documentation in :doc:`api/modules` for programmatic usage
