import hashlib
import hmac
import os


def hash_secret(secret, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_secret(secret, stored):
    salt, expected = stored.split("$", 1)
    candidate = hash_secret(secret, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected)
