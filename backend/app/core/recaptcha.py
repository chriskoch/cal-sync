"""Google reCAPTCHA v3 verification utilities."""
import httpx
from typing import Optional
from app.config import settings


async def verify_recaptcha(token: str, action: str) -> tuple[bool, float, Optional[str]]:
    """
    Verify a reCAPTCHA v3 token with Google's API.

    Args:
        token: The reCAPTCHA token from the frontend
        action: The expected action name (e.g., 'register', 'login')

    Returns:
        Tuple of (is_valid, score, error_message)
        - is_valid: Whether the token passed verification and met the minimum score
        - score: The reCAPTCHA score (0.0 to 1.0)
        - error_message: Error message if verification failed, None otherwise
    """
    if not token:
        return False, 0.0, "reCAPTCHA token is required"

    # Make request to Google reCAPTCHA API
    verification_url = "https://www.google.com/recaptcha/api/siteverify"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                verification_url,
                data={
                    "secret": settings.recaptcha_secret_key,
                    "response": token,
                }
            )

            if response.status_code != 200:
                return False, 0.0, "Failed to verify reCAPTCHA with Google"

            result = response.json()

            # Check if verification was successful
            if not result.get("success"):
                error_codes = result.get("error-codes", [])
                return False, 0.0, f"reCAPTCHA verification failed: {', '.join(error_codes)}"

            # Get the score (0.0 to 1.0)
            score = result.get("score", 0.0)

            # Verify the action matches what we expected
            returned_action = result.get("action", "")
            if returned_action != action:
                return False, score, f"reCAPTCHA action mismatch: expected '{action}', got '{returned_action}'"

            # Check if score meets minimum threshold
            if score < settings.recaptcha_min_score:
                return False, score, f"reCAPTCHA score too low: {score} < {settings.recaptcha_min_score}"

            return True, score, None

    except httpx.RequestError as e:
        return False, 0.0, f"Network error verifying reCAPTCHA: {str(e)}"
    except Exception as e:
        return False, 0.0, f"Unexpected error verifying reCAPTCHA: {str(e)}"
