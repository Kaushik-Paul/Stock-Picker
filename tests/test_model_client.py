import os
import unittest
from unittest.mock import patch

from stock_picker.model_client import create_llm


class CreateLlmTest(unittest.TestCase):
    environment = {
        "BASE_URL": "https://api.example.com/v1",
        "API_KEY": "test-key",
        "MODEL": "vendor/test-model",
    }

    def test_creates_openai_compatible_llm_from_environment(self) -> None:
        with patch.dict(os.environ, self.environment, clear=True):
            client = create_llm(temperature=0.2, timeout=15)

        self.assertEqual(client.model, "openai/vendor/test-model")
        self.assertEqual(client.base_url, "https://api.example.com/v1")
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.temperature, 0.2)
        self.assertEqual(client.timeout, 15)

    def test_accepts_an_openai_prefixed_model(self) -> None:
        environment = {**self.environment, "MODEL": "openai/vendor/test-model"}

        with patch.dict(os.environ, environment, clear=True):
            client = create_llm()

        self.assertEqual(client.model, "openai/vendor/test-model")

    def test_requires_each_configuration_value(self) -> None:
        for name in self.environment:
            with self.subTest(name=name):
                environment = {**self.environment}
                del environment[name]

                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        f"Missing required environment variable: {name}",
                    ):
                        create_llm()


if __name__ == "__main__":
    unittest.main()
