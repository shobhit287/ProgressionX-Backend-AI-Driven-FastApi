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

    # Reserve tokens for system prompt + current user message + response
    MAX_HISTORY_TOKENS = 2048

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return len(text) // 4

    def _trim_history(self, history: list[dict]) -> list[dict]:
        """Keep most recent messages that fit within the token budget."""
        trimmed: list[dict] = []
        token_count = 0
        for msg in reversed(history):
            msg_tokens = self._estimate_tokens(msg["content"])
            if token_count + msg_tokens > self.MAX_HISTORY_TOKENS:
                break
            trimmed.append(msg)
            token_count += msg_tokens
        return list(reversed(trimmed))

    async def generate_with_history(
        self,
        prompt: str,
        *,
        system_instruction: str,
        history: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        messages = [{"role": "system", "content": system_instruction}]
        for msg in self._trim_history(history):
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        response = await self._client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
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
