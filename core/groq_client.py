import json

from groq import AsyncGroq

from core.config import settings


class GroqClient:
    """Thin async wrapper around Groq API."""

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str,
        max_tokens: int = 1024,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

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


groq_client = GroqClient()
