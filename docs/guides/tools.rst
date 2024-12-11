Tool Management Guide
=====================

This guide covers everything you need to know about managing tools in MailOS.

Tool System Architecture
------------------------

.. mermaid::

    graph TB
        LLM[LLM System] --> |Uses| ToolRegistry[Tool Registry]
        ToolRegistry --> |Manages| Tools[Available Tools]
        Tools --> Weather[Weather Tool]
        Tools --> PDF[PDF Tool]
        Tools --> Python[Python Interpreter]
        Tools --> Bash[Bash Command]
        
        subgraph Tool Implementation
            Weather --> |Uses| WeatherAPI[Weather API]
            PDF --> |Uses| PDFLib[PDF Library]
            Python --> |Uses| PyInterp[Python Runtime]
            Bash --> |Uses| Shell[Shell Environment]
        end

        subgraph Configuration
            Config[Config File] --> |Configures| Tools
            EnvVars[Environment Variables] --> |Configures| Tools
        end

        subgraph Error Handling
            Tools --> |Returns| Success[Success Response]
            Tools --> |Returns| Error[Error Response]
            Logger[Logger] --> |Records| Error
        end

Tool Structure
--------------

A typical tool consists of:

.. code-block:: text

    src/mailos/tools/
    ├── __init__.py          # Tool registry
    ├── weather.py           # Weather tool implementation
    ├── python_interpreter.py # Python code execution tool
    └── bash_command.py      # Bash command execution tool

Creating New Tools
------------------

1. Create a new file in ``src/mailos/tools/``
2. Define your tool function
3. Create a Tool instance
4. Register the tool in ``__init__.py``

Example Implementation
-------------------

.. code-block:: python

    from typing import Dict
    from mailos.vendors.models import Tool
    from mailos.utils.logger_utils import logger

    def my_tool_function(param1: str) -> Dict:
        """Implement your tool's functionality."""
        try:
            # Tool implementation
            result = {"status": "success", "data": "result"}
            return result
        except Exception as e:
            logger.error(f"Tool error: {str(e)}")
            return {"status": "error", "message": str(e)}

    # Define tool interface
    my_tool = Tool(
        name="my_tool",
        description="Description of what the tool does",
        parameters={
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Parameter description",
                }
            },
        },
        required_params=["param1"],
        function=my_tool_function,
    )

Tool Registration
---------------

In ``src/mailos/tools/__init__.py``:

.. code-block:: python

    from .my_tool import my_tool

    AVAILABLE_TOOLS = [
        ("my_tool", "My Tool Display Name"),
        # Other tools...
    ]

Tool Dependencies
---------------

1. Add dependencies to ``pyproject.toml``:

.. code-block:: toml

    [project]
    dependencies = [
        "existing-dep>=1.0.0",
        "my-tool-dep>=2.0.0",  # Add your tool's dependencies
    ]

2. Document dependencies in tool's docstring
3. Update installation instructions

Configuration
------------

Tools can be configured through:

1. Environment variables
2. Configuration files
3. Runtime parameters

Example Configuration
------------------

.. code-block:: python

    import os
    from dotenv import load_dotenv

    # Load configuration
    load_dotenv()

    # Get configuration
    API_KEY = os.getenv("MY_TOOL_API_KEY")
    BASE_URL = os.getenv("MY_TOOL_BASE_URL", "default-url")

Testing
-------

1. Create test file in ``tests/tools/``:

.. code-block:: python

    import pytest
    from mailos.tools.my_tool import my_tool_function

    def test_my_tool_success(mock_dependency):
        """Test successful tool execution."""
        result = my_tool_function("test_param")
        assert result["status"] == "success"
        assert "data" in result

    def test_my_tool_error_handling():
        """Test tool error handling."""
        result = my_tool_function("invalid_param")
        assert result["status"] == "error"
        assert "message" in result

2. Add fixtures in ``tests/conftest.py``
3. Run tests: ``pytest tests/tools/test_my_tool.py``

Best Practices
-------------

Naming Conventions
----------------

* Tool files: lowercase with underscores (e.g., ``my_tool.py``)
* Functions: lowercase with underscores
* Classes: PascalCase
* Constants: UPPERCASE with underscores

Documentation
------------

1. Docstrings for all public functions
2. Type hints for parameters and returns
3. Example usage in docstrings
4. Clear error messages

Error Handling
------------

1. Always return a dict with "status" and "data"/"message"
2. Log errors with appropriate level
3. Provide helpful error messages
4. Handle expected exceptions gracefully

Tool Lifecycle
------------

.. mermaid::

    stateDiagram-v2
        [*] --> Development
        Development --> Testing: Implement
        Testing --> Review: Pass Tests
        Review --> Integration: Approved
        Integration --> Production: Deploy
        Production --> Maintenance: Monitor
        Maintenance --> Deprecated: Obsolete
        Deprecated --> [*]: Remove

Troubleshooting
--------------

Common Issues
-----------

1. Tool not appearing in UI
   * Check registration in ``__init__.py``
   * Verify tool name matches registration

2. Dependencies not found
   * Ensure dependencies in ``pyproject.toml``
   * Check virtual environment activation

3. Configuration errors
   * Verify environment variables
   * Check configuration file format

Debug Procedures
--------------

1. Enable debug logging:

.. code-block:: python

    import logging
    logging.getLogger("mailos").setLevel(logging.DEBUG)

2. Check tool registration:

.. code-block:: python

    from mailos.tools import AVAILABLE_TOOLS
    print(AVAILABLE_TOOLS)

3. Test tool directly:

.. code-block:: python

    from mailos.tools.my_tool import my_tool_function
    result = my_tool_function("test")
    print(result)

Removing Tools
------------

1. Remove tool file
2. Remove from ``__init__.py``
3. Remove tests
4. Update documentation
5. Remove dependencies if no longer needed
6. Update version number

Version Management
----------------

1. Use semantic versioning
2. Document breaking changes
3. Maintain backwards compatibility when possible
4. Update documentation for new versions

Security Considerations
---------------------

1. Validate all inputs
2. Use environment variables for sensitive data
3. Implement rate limiting if needed
4. Follow security best practices for external APIs
5. Regular security audits

See Also
--------

* :doc:`../api/tools` for API reference
* :doc:`../configuration` for configuration options
* :doc:`../quickstart` for getting started
