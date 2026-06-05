"""Pydantic schemas for the auth layer (SEC-01 / SEC-02 / SEC-17)."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Password length policy: long-enough to defeat trivial guessing without
# capping pass-phrase length (OWASP password-storage guidance). 128 covers
# anything a human types and still protects Argon2 from absurd inputs.
_PASSWORD_MIN_LENGTH = 12
_PASSWORD_MAX_LENGTH = 128
# Conservative email regex (RFC 5321 length cap, basic local@domain shape).
# We do not need RFC-5322 compliance — this is the auth boundary, not a
# mass-mailing tool. Reject obvious garbage; the operator confirms ownership.
_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_EMAIL_MAX_LENGTH = 254


def _normalize_email(value: str) -> str:
    cleaned = value.strip().lower()
    if len(cleaned) > _EMAIL_MAX_LENGTH or not _EMAIL_RE.match(cleaned):
        raise ValueError("Invalid email address")
    return cleaned


class RegisterRequest(BaseModel):
    """Inbound payload for `POST /auth/register`."""

    email: str = Field(..., max_length=_EMAIL_MAX_LENGTH)
    password: str = Field(
        ..., min_length=_PASSWORD_MIN_LENGTH, max_length=_PASSWORD_MAX_LENGTH
    )

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _normalize_email(value)


class LoginRequest(BaseModel):
    """Inbound payload for `POST /auth/login`."""

    email: str = Field(..., max_length=_EMAIL_MAX_LENGTH)
    password: str = Field(..., min_length=1, max_length=_PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _normalize_email(value)


class UserRead(BaseModel):
    """Outbound representation of the authenticated user (no secrets)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime
