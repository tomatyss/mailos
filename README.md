# 📯 Mailos

Mailos is a Python framework that transforms email inboxes into an intelligent multi-agent system powered by Large Language Models (LLMs). It creates a network of AI agents that monitor email accounts and orchestrate automated interactions, leveraging various AI providers including OpenAI, Anthropic, and AWS Bedrock.

## 🤖 Multi-Agent System

Mailos transforms emails into a sophisticated multi-agent ecosystem:
- Each email account becomes an autonomous agent capable of understanding and responding to messages
- Agents can collaborate and coordinate responses across multiple email accounts
- Built-in tool system allows agents to perform complex tasks (weather lookup, PDF manipulation, code execution)
- Configurable system prompts guide agent behavior and decision-making
- Smart filtering prevents unnecessary auto-replies and feedback loops

## ✨ Features

- 🤖 Multiple LLM Provider Support (OpenAI, Anthropic Claude, AWS Bedrock)
- 📧 IMAP Email Monitoring
- ⚡ Real-time Email Processing
- 🔄 Automatic Response Generation
- 🎯 Smart Reply Filtering
- 🌐 Web-based Configuration Interface
- ⏱️ Scheduled Email Checking
- 🛠️ Extensible Tool System
- 🔒 Optional Authentication System

## 🚀 Installation

```bash
pip install mailos
```

## 🏃 Quick Start

1. Launch the web interface:

```bash
mailos
```

2. Open your browser and navigate to `http://localhost:8080`

3. Click "Add New Checker" and configure your email account:
   - Email credentials (IMAP server, port, etc.)
   - LLM provider settings
   - Auto-reply preferences
   - Tool configurations
   - System prompts

## ⚙️ Configuration

### Authentication Settings

By default, the web interface is accessible without authentication. To enable authentication:

```bash
# Enable authentication
export MAILOS_AUTH_ENABLED=true

# Optional: Configure custom credentials (defaults to admin/admin)
export MAILOS_AUTH_USERNAME=your_username
export MAILOS_AUTH_PASSWORD=your_password

# Start Mailos
mailos
```

### Email Settings
- IMAP server and port
- Email address and password
- Monitoring frequency
- Auto-reply settings
- Tool permissions

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

## 🛠️ Tool System

Mailos includes a powerful tool system that extends agent capabilities:

### Built-in Tools
- **Weather Tool**: Fetch weather information
- **PDF Tool**: Create and manipulate PDF documents
- **Python Interpreter**: Execute Python code
- **Bash Command**: Run system commands

### Tool Configuration

```json
{
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
}
```

## 🔧 Development

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

## 🏗️ Architecture

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

## System Requirements

- Python 3.8 or higher
- pip package manager
- IMAP-enabled email account
- API keys for chosen LLM provider
- Internet connection for email and API access

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

Ivan Iufriakov (tomatyss@gmail.com)

## 🙏 Acknowledgments

- PyWebIO for the web interface
- APScheduler for task scheduling
- OpenAI, Anthropic, and AWS for their LLM services
