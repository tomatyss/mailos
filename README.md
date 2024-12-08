# Mailos

Mailos is a Python package that transforms any email inbox into an intelligent agent powered by Large Language Models (LLMs). It monitors email accounts and can automatically respond to incoming messages using various AI providers including OpenAI, Anthropic, and AWS Bedrock.

## Features

- 🤖 Multiple LLM Provider Support (OpenAI, Anthropic Claude, AWS Bedrock)
- 📧 IMAP Email Monitoring
- ⚡ Real-time Email Processing
- 🔄 Automatic Response Generation
- 🎯 Smart Reply Filtering
- 🌐 Web-based Configuration Interface
- ⏱️ Scheduled Email Checking

## Installation

```bash
pip install mailos
```

## Quick Start

1. Launch the web interface:

```bash
mailos
```

2. Open your browser and navigate to `http://localhost:8080`

3. Click "Add New Checker" and configure your email account:
   - Email credentials (IMAP server, port, etc.)
   - LLM provider settings
   - Auto-reply preferences

## Configuration

### Email Settings
- IMAP server and port
- Email address and password
- Monitoring frequency

### LLM Provider Options

#### OpenAI

```json
{
    "llm_provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key"
}
```

#### Anthropic Claude

```json
{
    "llm_provider": "anthropic",
    "model": "claude-3-sonnet",
    "api_key": "your-api-key"
}
```

#### AWS Bedrock (Claude)

```json
{
    "llm_provider": "bedrock-anthropic",
    "model": "anthropic.claude-3-sonnet",
    "aws_access_key": "your-access-key",
    "aws_secret_key": "your-secret-key",
    "aws_region": "us-east-1"
}
```

## Development

1. Clone the repository:

```bash
git clone https://github.com/tomatyss/mailos.git
cd mailos
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:

```bash
pip install -e ".[dev]"
```

4. Run tests:

```bash
pytest
```

## Architecture

The package consists of several key components:

1. **Email Monitor**: Continuously checks for new emails using IMAP

```python:src/mailos/check_emails.py
startLine: 29
endLine: 78
```

2. **LLM Integration**: Supports multiple AI providers through a unified interface

```python:src/mailos/vendors/models.py
startLine: 8
endLine: 65
```

3. **Reply Handler**: Manages email response generation and filtering

```python:src/mailos/reply.py
startLine: 169
endLine: 192
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Ivan Iufriakov (tomatyss@gmail.com)

## Acknowledgments

- PyWebIO for the web interface
- APScheduler for task scheduling
- OpenAI, Anthropic, and AWS for their LLM services