import os

from google import genai

from llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini implementation of the LLM provider interface."""

    def __init__(self, model: str):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return response.text.strip()
