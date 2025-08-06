import secrets


def generage_state() -> str:
    return secrets.token_urlsafe(16)
