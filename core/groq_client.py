import json
import logging

from groq import AsyncGroq

from core.config import settings
from core.exception_handlers import BaseDomainError

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Check if exception is a Groq rate limit error (works across SDK versions)."""
    cls_name = type(exc).__name__
    if cls_name == "RateLimitError":
        return True
    # httpx-based errors: check status code
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    return False


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
        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            if _is_rate_limit_error(e):
                logger.warning(f"Groq rate limit hit: {e}")
                raise BaseDomainError("AI is temporarily busy. Please try again in a minute.", 503)
            logger.error(f"Groq API error: {type(e).__name__} - {e}")
            raise BaseDomainError("AI service is currently unavailable. Please try again later.", 503)

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
        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            if _is_rate_limit_error(e):
                logger.warning(f"Groq rate limit hit: {e}")
                raise BaseDomainError("AI is temporarily busy. Please try again in a minute.", 503)
            logger.error(f"Groq API error: {type(e).__name__} - {e}")
            raise BaseDomainError("AI service is currently unavailable. Please try again later.", 503)

    async def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: str,
        max_tokens: int = 1024,
    ) -> dict:
        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
        except Exception as e:
            if _is_rate_limit_error(e):
                logger.warning(f"Groq rate limit hit: {e}")
                raise BaseDomainError("AI is temporarily busy. Please try again in a minute.", 503)
            logger.error(f"Groq API error: {type(e).__name__} - {e}")
            raise BaseDomainError("AI service is currently unavailable. Please try again later.", 503)

        return self._parse_json(raw)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Parse JSON from LLM output. Returns the full parsed dict.

        Falls back to the analysis-style shape on decode failure so existing
        analysis endpoints degrade gracefully.
        """
        if text is None:
            return {"analysis": "", "suggestions": []}
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
            return {"analysis": text, "suggestions": []}
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM. Raw: {text[:300]}")
            return {"analysis": text, "suggestions": []}


groq_client = GroqClient()
