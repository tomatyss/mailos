# MailOS Tools

This directory contains the tool implementations for MailOS. Each tool provides specific functionality that can be used by the LLM system.

## Available Tools

- `weather.py`: Weather information lookup using OpenWeatherMap API
- `pdf_tool.py`: PDF manipulation and text extraction
- `python_interpreter.py`: Safe Python code execution
- `bash_command.py`: System command execution

## Adding New Tools

1. Create a new Python file in this directory
2. Implement your tool following the standard interface
3. Register it in `__init__.py`

Example:

```python
from typing import Dict
from mailos.vendors.models import Tool
from mailos.utils.logger_utils import logger

def my_tool_function(param1: str) -> Dict:
    try:
        # Implementation
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Tool error: {str(e)}")
        return {"status": "error", "message": str(e)}

my_tool = Tool(
    name="my_tool",
    description="Tool description",
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
```

## Tool Requirements

1. Must return a dictionary with:
   - Success: `{"status": "success", "data": result}`
   - Error: `{"status": "error", "message": str}`

2. Must use the logger for error reporting

3. Must include comprehensive tests in `tests/tools/`

## Documentation

Full documentation available at:
- Development Guide: `docs/guides/tools.rst`
- API Reference: `docs/api/tools.rst`
- Configuration: `docs/configuration.rst`

## Testing

Run tool tests:
```bash
pytest tests/tools/
```

## Security

- Validate all inputs
- Use environment variables for sensitive data
- Follow rate limiting guidelines
- Document security considerations
