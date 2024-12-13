"""Configuration schemas for LLM vendors."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ConfigField:
    """Configuration field definition."""

    name: str
    label: str
    type: str  # "text", "password", "number", etc.
    required: bool = True
    default: Optional[str] = None
    help_text: Optional[str] = None


@dataclass
class VendorConfig:
    """Vendor configuration schema."""

    name: str
    fields: List[ConfigField]
    default_model: str
    supported_models: List[str]


# Define configurations for each vendor
VENDOR_CONFIGS: Dict[str, VendorConfig] = {
    "anthropic": VendorConfig(
        name="Anthropic",
        fields=[
            ConfigField(
                name="api_key",
                label="API Key",
                type="password",
                help_text="Your Anthropic API key",
            ),
        ],
        default_model="claude-3-5-sonnet-latest",
        supported_models=[
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240229",
        ],
    ),
    "openai": VendorConfig(
        name="OpenAI",
        fields=[
            ConfigField(
                name="api_key",
                label="API Key",
                type="password",
                help_text="Your OpenAI API key",
            ),
        ],
        default_model="gpt-4o",
        supported_models=["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"],
    ),
    "bedrock-anthropic": VendorConfig(
        name="AWS Bedrock (Anthropic)",
        fields=[
            ConfigField(
                name="aws_access_key",
                label="AWS Access Key",
                type="password",
                help_text="Your AWS access key",
            ),
            ConfigField(
                name="aws_secret_key",
                label="AWS Secret Key",
                type="password",
                help_text="Your AWS secret key",
            ),
            ConfigField(
                name="aws_session_token",
                label="AWS Session Token",
                type="password",
                required=False,
                help_text="Optional AWS session token",
            ),
            ConfigField(
                name="aws_region",
                label="AWS Region",
                type="text",
                default="us-east-1",
                help_text="AWS region for Bedrock service",
            ),
        ],
        default_model="anthropic.claude-3-sonnet-20240229-v1:0",
        supported_models=[
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240229-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
        ],
    ),
}
