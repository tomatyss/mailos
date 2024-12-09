Configuration Guide
=================

This guide covers all configuration options available in MailOS.

Configuration File
----------------

MailOS uses a JSON configuration file ``email_config.json`` to store settings.

Email Checker Configuration
-------------------------

Each checker in the configuration has the following options:

Basic Settings
~~~~~~~~~~~~

``name``
    Optional name for the checker

``monitor_email``
    Email address to monitor

``password``
    Email account password

``imap_server``
    IMAP server address (e.g., "imap.gmail.com")

``imap_port``
    IMAP server port (usually 993 for SSL)

``enabled``
    Boolean to enable/disable the checker

``auto_reply``
    Boolean to enable/disable automatic replies

LLM Configuration
~~~~~~~~~~~~~~

``llm_provider``
    LLM provider name ("openai", "anthropic", or "bedrock-anthropic")

``model``
    Model name to use

Provider-Specific Settings
~~~~~~~~~~~~~~~~~~~~~~~

OpenAI
^^^^^^

``api_key``
    OpenAI API key

Anthropic
^^^^^^^^

``api_key``
    Anthropic API key

AWS Bedrock
^^^^^^^^^^

``aws_access_key``
    AWS access key

``aws_secret_key``
    AWS secret key

``aws_region``
    AWS region (default: "us-east-1")

``aws_session_token``
    Optional AWS session token

System Prompt
~~~~~~~~~~~

``system_prompt``
    Instructions for the LLM when generating responses

Example Configuration
------------------

Complete configuration example::

    {
        "checkers": [
            {
                "name": "Support Email",
                "monitor_email": "support@example.com",
                "password": "your-password",
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "enabled": true,
                "auto_reply": true,
                "llm_provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "api_key": "your-api-key",
                "system_prompt": "You are a helpful customer support assistant..."
            }
        ]
    }

Environment Variables
------------------

You can also use environment variables for sensitive information:

* ``OPENAI_API_KEY``
* ``ANTHROPIC_API_KEY``
* ``AWS_ACCESS_KEY_ID``
* ``AWS_SECRET_ACCESS_KEY``
* ``AWS_SESSION_TOKEN``

Create a ``.env`` file in your project directory::

    OPENAI_API_KEY=your-openai-key
    ANTHROPIC_API_KEY=your-anthropic-key
    AWS_ACCESS_KEY_ID=your-aws-key
    AWS_SECRET_ACCESS_KEY=your-aws-secret

Security Considerations
--------------------

* Use environment variables for API keys
* Store email passwords securely
* Consider using app-specific passwords for email accounts
* Regularly rotate credentials
* Monitor API usage and costs
