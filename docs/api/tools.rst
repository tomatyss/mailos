Tools API Reference
===================

This section provides detailed API documentation for the MailOS tool system.

Tool Base
=========

.. module:: mailos.vendors.models

.. autoclass:: Tool
   :members:
   :special-members: __init__

Built-in Tools
==============

Weather Tool
------------

.. module:: mailos.tools.weather

.. autofunction:: get_weather

.. autodata:: weather_tool
   :annotation: = Tool instance for weather information

Python Interpreter
------------------

.. module:: mailos.tools.python_interpreter

.. autofunction:: execute_python

.. autodata:: python_interpreter_tool
   :annotation: = Tool instance for Python code execution

Bash Command
------------

.. module:: mailos.tools.bash_command

.. autodata:: bash_command_tool
   :annotation: = Tool instance for bash command execution

Tool Registry
=============

.. module:: mailos.tools

.. autodata:: AVAILABLE_TOOLS
   :annotation: = List of available tools

Tool Utilities
==============

.. module:: mailos.utils.logger_utils

.. autofunction:: setup_logger

Common Tool Patterns
====================

Error Handling
--------------

Tools should follow this error handling pattern:

.. code-block:: python

    def my_tool_function(param: str) -> Dict:
        try:
            # Tool implementation
            return {
                "status": "success",
                "data": result
            }
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

Response Format
---------------

Success Response::

    {
        "status": "success",
        "data": {
            # Tool-specific data
        }
    }

Error Response::

    {
        "status": "error",
        "message": "Error description"
    }

Tool Configuration
------------------

Tools can be configured using:

1. Environment variables
2. Tool-specific configuration in email_config.json
3. Runtime parameters passed to the tool function

Example Configuration::

    {
        "checkers": [{
            "enabled_tools": ["weather", "python_interpreter"],
            "tool_config": {
                "weather": {
                    "default_units": "metric"
                },
                "python_interpreter": {
                    "timeout": 30,
                    "max_memory": 128
                }
            }
        }]
    }
