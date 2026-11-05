"""
The ONLY place that talks to Gemini. Every service calls generate_text().
Benefits: one model setting (GEMINI_MODEL in .env), one timeout, one error policy,
and one file to change when you move to the newer google-genai package.
"""
import logging
import os

import google.generativeai as genai
from config import Config

log = logging.getLogger(__name__)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TIMEOUT_SECONDS = 30

LLM_UNAVAILABLE = "The AI service is temporarily unavailable. Please try again in a moment."
QUOTA_EXCEEDED = (
    "The daily free AI quota has been used up. Search still works; "
    "AI answers will be back after the quota resets."
)
FAILURE_MESSAGES = {LLM_UNAVAILABLE, QUOTA_EXCEEDED}

genai.configure(api_key=Config.GEMINI_API_KEY)
_model = genai.GenerativeModel(MODEL_NAME)


def is_quota_error(exc):
    s = str(exc).lower()
    return "429" in s or "quota" in s or "resourceexhausted" in s or "resource_exhausted" in s


def generate_text(prompt):
    """Returns the model's text, or one of FAILURE_MESSAGES if the call failed."""
    try:
        return _model.generate_content(
            prompt, request_options={"timeout": TIMEOUT_SECONDS}
        ).text
    except Exception as exc:
        log.exception("Gemini call failed (model=%s)", MODEL_NAME)
        return QUOTA_EXCEEDED if is_quota_error(exc) else LLM_UNAVAILABLE