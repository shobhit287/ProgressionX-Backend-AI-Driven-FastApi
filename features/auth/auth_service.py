from sqlalchemy.ext.asyncio import AsyncSession

from features.users.users_service import UserService
from core.security import verify_password, create_access_token, create_refresh_token, verify_token
from core.exception_handlers import BaseDomainError
from core.config import settings


class AuthService:
    def __init__(self, db: AsyncSession):
      self.db = db
      self.users_service = UserService(db)

    def _issue_tokens(self, user) -> dict:
        """Build the JWT response payload for any successful login path."""
        access_token = create_access_token({"id": str(user.id)})
        refresh_token = create_refresh_token({"id": str(user.id)})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "is_profile_complete": bool(user.is_profile_complete),
        }

    async def login(self, payload: dict) -> dict:
      email = payload.get("email", "").strip().lower()
      user = await self.users_service.get_by_email(email)
      if not user or not user.hashed_password or not verify_password(
          payload.get("password"), user.hashed_password
      ):
          raise BaseDomainError("Invalid Credentials", 401)

      return self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> dict:
      payload = verify_token(refresh_token)
      if payload.get("type") != "refresh":
          raise BaseDomainError("Invalid token type", 401)

      user_id = payload.get("id")
      user = await self.users_service.get_by_id(user_id)
      if not user:
          raise BaseDomainError("User not found", 401)

      return self._issue_tokens(user)

    async def login_with_google(self, credential: str) -> dict:
        """Verify a Google ID token and either log in an existing user, link
        an existing email-only account to the Google identity, or create a
        stub user that must complete profile before using the app."""
        if not settings.GOOGLE_CLIENT_ID:
            raise BaseDomainError(
                "Google sign-in is not configured on this server.", 503
            )

        # Lazy import so the rest of the app boots even if google-auth isn't
        # installed yet (e.g., in tests that don't care about this path).
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        from google.auth.exceptions import GoogleAuthError

        try:
            claims = google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except (GoogleAuthError, ValueError):
            # Bad signature, wrong audience, expired, malformed, etc.
            raise BaseDomainError("Google sign-in token is invalid.", 401)

        # Google's docs require explicit iss check — verify_oauth2_token does
        # most validation but not this; guard belt-and-suspenders.
        if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise BaseDomainError("Google sign-in token has invalid issuer.", 401)

        if not claims.get("email_verified"):
            # Refuse to auto-link or create if Google hasn't vouched for the
            # email — otherwise a Workspace admin could hijack an account.
            raise BaseDomainError(
                "Your Google email isn't verified. Please verify it with Google first.",
                403,
            )

        sub = claims.get("sub")
        email = (claims.get("email") or "").strip().lower()
        given_name = claims.get("given_name") or ""
        family_name = claims.get("family_name") or ""
        if not sub or not email:
            raise BaseDomainError("Google sign-in token is missing required fields.", 401)

        user = await self.users_service.upsert_google_user(
            google_sub=sub,
            email=email,
            given_name=given_name,
            family_name=family_name,
        )
        return self._issue_tokens(user)
