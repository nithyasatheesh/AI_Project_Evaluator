"""Individual logins.

Users live in Streamlit secrets (never in the code repository):

    [users.LD001]
    name = "Priya Venkatesh"
    role = "participant"            # or "trainer"
    password_hash = "pbkdf2_sha256$200000$<salt>$<hash>"

make_logins.py creates the IDs, random passwords and these hashes.
"""
import base64
import hashlib
import hmac
import os
import threading
import time

ITERATIONS = 200_000
_FAILS = {}
_LOCK = threading.Lock()
MAX_FAILS, LOCK_SECONDS = 5, 120


def hash_password(password, salt=None, iterations=ITERATIONS):
    salt = salt or base64.b64encode(os.urandom(12)).decode()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${base64.b64encode(digest).decode()}"


def verify_password(password, stored):
    try:
        algo, iterations, salt, _ = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        return hmac.compare_digest(hash_password(password, salt, int(iterations)), stored)
    except Exception:
        return False


def login(users, login_id, password):
    """Return (user dict | None, error message)."""
    login_id = (login_id or "").strip().upper()
    with _LOCK:
        fails, since = _FAILS.get(login_id, (0, 0))
        if fails >= MAX_FAILS and time.time() - since < LOCK_SECONDS:
            return None, "Too many attempts. Wait 2 minutes and try again."
    user = None
    for uid, u in (users or {}).items():
        if uid.upper() == login_id:
            user = {"id": uid.upper(), "name": u.get("name", uid), "role": u.get("role", "participant")}
            stored = u.get("password_hash", "")
            break
    if user and verify_password(password or "", stored):
        with _LOCK:
            _FAILS.pop(login_id, None)
        return user, ""
    with _LOCK:
        fails, since = _FAILS.get(login_id, (0, time.time()))
        _FAILS[login_id] = (fails + 1, since if fails else time.time())
    return None, "Login ID or password is incorrect."
