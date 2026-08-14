"""Shared Google Gemini client construction — used by the real (non-
mock) providers in apps.processing (classification) and apps.extraction
(structured extraction). One function so both apps build the client the
same way and tests only need to patch one name.

Import is lazy (inside the function, not at module level) so importing
this module — which importing apps.processing.providers /
apps.extraction.providers always does — never requires the google-genai
package's network stack to initialize; only actually calling this
function does. Mirrors the lazy-import pattern
apps.processing.providers.TesseractOCRProvider already uses for
pytesseract.
"""

from django.conf import settings


def build_gemini_client():
    from google import genai

    return genai.Client(api_key=settings.GEMINI_API_KEY)
