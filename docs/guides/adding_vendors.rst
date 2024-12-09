Adding New LLM Vendors
=====================

This guide explains how to add support for new LLM vendors to MailOS.

Overview
--------

Adding a new vendor requires three main steps:

1. Create vendor configuration
2. Implement vendor-specific LLM class
3. Register the vendor with LLMFactory

Step 1: Vendor Configuration
---------------------------

Add your vendor configuration to ``src/mailos/vendors/config.py``::

    VENDOR_CONFIGS["your-vendor"] = VendorConfig(
        name="Your Vendor Name",
        fields=[
            ConfigField(
                name="api_key",
                label="API Key",
                type="password",
                help_text="Your vendor API key",
            ),
            # Add other required fields
        ],
        default_model="default-model-name",
        supported_models=[
            "model-1",
            "model-2",
        ],
    )

Step 2: Implement Vendor Class
----------------------------

Create a new file ``src/mailos/vendors/your_vendor_llm.py``::

    from mailos.vendors.base import BaseLLM
    from mailos.vendors.models import LLMResponse, Message

    class YourVendorLLM(BaseLLM):
        def __init__(self, api_key: str, model: str, **kwargs):
            super().__init__(api_key, model, **kwargs)
            # Initialize vendor-specific client
            self.client = YourVendorClient(api_key)

        async def generate(self, messages: List[Message], stream: bool = False):
            # Implement message generation
            pass

        async def process_image(self, image_data: bytes, prompt: str):
            # Implement if supported
            raise NotImplementedError()

        async def generate_embedding(self, content: Union[str, List[str]]):
            # Implement if supported
            raise NotImplementedError()

Step 3: Register the Vendor
-------------------------

Add your vendor to ``src/mailos/vendors/factory.py``::

    from mailos.vendors.your_vendor_llm import YourVendorLLM

    LLMFactory.register("your-vendor", YourVendorLLM)

Testing
-------

1. Create unit tests in ``tests/vendors/test_your_vendor.py``
2. Add integration tests if applicable
3. Test the UI configuration form

Example Implementation
--------------------

Here's a complete example using a hypothetical vendor::

    # src/mailos/vendors/example_llm.py
    class ExampleLLM(BaseLLM):
        def __init__(self, api_key: str, model: str = "example-v1", **kwargs):
            super().__init__(api_key, model, **kwargs)
            self.client = ExampleAPI(api_key)

        async def generate(self, messages: List[Message], stream: bool = False):
            formatted_messages = self._format_messages(messages)
            response = await self.client.generate(
                messages=formatted_messages,
                model=self.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return self._parse_response(response)

Best Practices
-------------

1. Always implement proper error handling
2. Document all vendor-specific features and limitations
3. Follow the existing type hints and docstring formats
4. Add appropriate logging
5. Implement rate limiting handling
6. Add configuration validation
