from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    tenant_code: str | None = None


class MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=8)


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class AcceptInviteIn(BaseModel):
    token: str
    password: str = Field(min_length=10, max_length=200)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=200)


class TokenOut(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    mfa_required: bool = False
    mfa_token: str | None = None
