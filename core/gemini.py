import json

from google import genai

from core.config import settings


class GeminiClient:
    """Thin async wrapper around Google Gemini API."""

    MODEL = "gemini-2.0-flash"

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str,
        max_tokens: int = 1024,
    ) -> str:
        response = await self._client.aio.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    async def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: str,
        max_tokens: int = 1024,
    ) -> dict:
        raw = await self.generate(
            prompt,
            system_instruction=system_instruction,
            max_tokens=max_tokens,
        )
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            parsed = json.loads(cleaned)
            return {
                "analysis": parsed.get("analysis", text),
                "suggestions": parsed.get("suggestions", []),
            }
        except json.JSONDecodeError:
            return {"analysis": text, "suggestions": []}


gemini_client = GeminiClient()
