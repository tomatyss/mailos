Configuration Guide
==================

This guide covers all configuration options available in MailOS.

Configuration File
----------------

MailOS uses a JSON configuration file ``email_config.json`` to store settings.

Email Checker Configuration
-------------------------

Each checker in the configuration has the following options:

Basic Settings
------------

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

Tool Configuration
----------------

Tools can be enabled and configured per checker:

``enabled_tools``
    List of enabled tool names for this checker

``tool_config``
    Tool-specific configuration options

Example tool configuration::

    {
        "checkers": [{
            "enabled_tools": ["weather", "python_interpreter"],
            "tool_config": {
                "weather": {
                    "default_units": "metric",
                    "api_key": "your-api-key"
                },
                "python_interpreter": {
                    "timeout": 30,
                    "max_memory": 128
                }
            }
        }]
    }

Available Tools
-------------

weather
    Weather information lookup
    
    Options:
        - ``default_units``: "metric" or "imperial"
        - ``api_key``: OpenWeatherMap API key

python_interpreter
    Python code execution
    
    Options:
        - ``timeout``: Maximum execution time (seconds)
        - ``max_memory``: Memory limit in MB
        - ``allowed_modules``: List of allowed Python modules

bash_command
    Bash command execution
    
    Options:
        - ``timeout``: Maximum execution time (seconds)
        - ``allowed_commands``: List of allowed commands
        - ``working_dir``: Working directory for commands

LLM Configuration
---------------

``llm_provider``
    LLM provider name (see supported providers below)

``model``
    Model name to use (provider-specific)

Provider-Specific Settings
-----------------------

Each provider has its own required and optional fields as defined in the vendor configuration. See the provider documentation for details:

- OpenAI: API key
- Anthropic: API key
- AWS Bedrock: AWS credentials (access key, secret key, optional session token)

For the most up-to-date list of required fields and supported models, check the vendor configurations in ``src/mailos/vendors/config.py``.

System Prompt
-----------

``system_prompt``
    Instructions for the LLM when generating responses

Environment Variables
------------------

You can use environment variables for sensitive information:

Tool-specific:
    * ``OPENWEATHER_API_KEY``
    * ``PDF_TOOL_LICENSE_KEY``

LLM Providers:
    * ``OPENAI_API_KEY``
    * ``ANTHROPIC_API_KEY``
    * ``AWS_ACCESS_KEY_ID``
    * ``AWS_SECRET_ACCESS_KEY``
    * ``AWS_SESSION_TOKEN``

Create a ``.env`` file in your project directory::

    OPENWEATHER_API_KEY=your-weather-api-key
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
* Validate tool inputs
* Implement rate limiting for tools
* Regular security audits

See Also
--------

* :doc:`guides/tools` for detailed tool documentation
* :doc:`api/tools` for tool API reference
* :doc:`quickstart` for basic setup
