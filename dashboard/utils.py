import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "your_secret_key_here"  # Use Django settings.SECRET_KEY in production


def create_token(email, password, otp):
    now = datetime.now(timezone.utc)
    payload = {
        "email": email,
        "password": password,
        "otp": otp,
        "iat": now,
        "exp": now + timedelta(minutes=5),  # Token valid for 5 minutes
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "email": payload["email"],
            "password": payload["password"],
            "otp": payload["otp"],
        }
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}


def mask_email(email):
    try:
        username, domain = email.split("@")
        masked_username = username[0] + "*" * (len(username) - 1)
        domain_name, domain_ext = domain.split(".")
        masked_domain = domain_name[0] + "*" * (len(domain_name) - 1) + "." + domain_ext
        return f"{masked_username}@{masked_domain}"
    except Exception:
        return "Invalid email"
