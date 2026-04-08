from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password."""
    return _ph.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Verify a plaintext password against a hash."""
    try:
        return _ph.verify(hashed, plaintext)
    except VerifyMismatchError, VerificationError, InvalidHashError:
        return False
