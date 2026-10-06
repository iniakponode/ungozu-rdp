"""
Password hashing utilities using bcrypt directly.
passlib is not used — it is incompatible with bcrypt >= 4.x.
"""
import bcrypt


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of *plain_password*."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
