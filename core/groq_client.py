import json
import logging
import time
import uuid
from contextvars import ContextVar

from groq import AsyncGroq

from core.config import settings
from core.exception_handlers import BaseDomainError

logger = logging.getLogger(__name__)

# Context vars set by endpoints before calling AI — allows logging without
# changing every service method signature.
_llm_user_id: ContextVar[str | None] = ContextVar("_llm_user_id", default=None)
_llm_endpoint: ContextVar[str | None] = ContextVar("_llm_endpoint", default=None)


def set_llm_context(*, user_id: str | None = None, endpoint: str | None = None):
    """Call from a router/service before invoking the LLM."""
    if user_id is not None:
        _llm_user_id.set(user_id)
    if endpoint is not None:
        _llm_endpoint.set(endpoint)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Check if exception is a Groq rate limit error (works across SDK versions)."""
    cls_name = type(exc).__name__
    if cls_name == "RateLimitError":
        return True
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    return False


async def _log_llm_call(
    *,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    duration_ms: int,
    status: str,
):
    """Persist an LLM call record. Uses its own short-lived session."""
    try:
        from db.database import AsyncSessionLocal
        from features.ai_analysis.llm_call_log_model import LlmCallLog

        raw_user_id = _llm_user_id.get()
        endpoint = _llm_endpoint.get() or "unknown"

        # asyncpg requires a UUID instance for UUID columns — coerce strings safely
        user_id_value: uuid.UUID | None = None
        if raw_user_id is not None:
            try:
                user_id_value = (
                    raw_user_id
                    if isinstance(raw_user_id, uuid.UUID)
                    else uuid.UUID(str(raw_user_id))
                )
            except (ValueError, TypeError):
                user_id_value = None

        async with AsyncSessionLocal() as session:
            log = LlmCallLog(
                id=uuid.uuid4(),
                user_id=user_id_value,
                endpoint=endpoint,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                status=status,
            )
            session.add(log)
            await session.commit()
    except Exception:
        # Never let logging failures break the actual AI response, but make the
        # failure visible — silent warnings get lost and the dashboard ends up
        # showing 0 calls forever.
        logger.exception("Failed to log LLM call")


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
        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            usage = response.usage
            await _log_llm_call(
                model=self.MODEL,
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
                duration_ms=duration_ms,
                status="success",
            )
            return response.choices[0].message.content
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            status = "rate_limited" if _is_rate_limit_error(e) else "error"
            await _log_llm_call(
                model=self.MODEL,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms,
                status=status,
            )
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
        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                max_tokens=max_tokens,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            usage = response.usage
            await _log_llm_call(
                model=self.MODEL,
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
                duration_ms=duration_ms,
                status="success",
            )
            return response.choices[0].message.content
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            status = "rate_limited" if _is_rate_limit_error(e) else "error"
            await _log_llm_call(
                model=self.MODEL,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms,
                status=status,
            )
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
        start = time.monotonic()
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
            duration_ms = int((time.monotonic() - start) * 1000)
            usage = response.usage
            await _log_llm_call(
                model=self.MODEL,
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
                duration_ms=duration_ms,
                status="success",
            )
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            status = "rate_limited" if _is_rate_limit_error(e) else "error"
            await _log_llm_call(
                model=self.MODEL,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms,
                status=status,
            )
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
