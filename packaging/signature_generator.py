"""Signature Generator + Manifest Signer (master spec's `packaging/
signature_generator`, `manifest_signer`, folded into one real module).

Real asymmetric signing via Ed25519 (the `cryptography` library,
confirmed installed and exercised live — generate/sign/verify/reject-
tampered — before this module was written, not assumed from docs). This
is genuine cryptographic signing: a release's manifest hash is signed
with a private key that stays local, and ANYONE with just the public key
can verify the signature without ever having the secret — the same
guarantee real software-release signing provides, short of an actual PKI
(no certificate authority, no trust chain beyond "this is the one key
this KOBA Creator Engine instance has always signed with").

The keypair is generated once and persisted under config/signing/ (never
regenerated silently — a new keypair would invalidate every previous
release's verifiability, so get_or_create_keypair() only creates one if
none exists yet).
"""
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from core.config import PROJECT_ROOT

SIGNING_DIR = os.path.join(PROJECT_ROOT, "config", "signing")
PRIVATE_KEY_PATH = os.path.join(SIGNING_DIR, "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(SIGNING_DIR, "public_key.pem")


class SignatureError(Exception):
    pass


def get_or_create_keypair():
    """Loads the existing keypair if one exists; generates and persists
    a new one only if this is genuinely the first signing operation ever
    run — never silently rotates keys, which would make every prior
    release's signature unverifiable against a "current" public key."""
    if os.path.isfile(PRIVATE_KEY_PATH):
        with open(PRIVATE_KEY_PATH, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        return private_key, private_key.public_key()

    os.makedirs(SIGNING_DIR, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    os.chmod(PRIVATE_KEY_PATH, 0o600)

    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    return private_key, public_key


def get_public_key_pem():
    """For a verifier who doesn't have (and must never need) the private
    key — e.g. a future marketplace checking a package's authenticity."""
    if not os.path.isfile(PUBLIC_KEY_PATH):
        get_or_create_keypair()
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return f.read()


def sign_bytes(data: bytes) -> bytes:
    private_key, _ = get_or_create_keypair()
    return private_key.sign(data)


def sign_file(path) -> bytes:
    """Signs the file's own real bytes directly (Ed25519 handles
    arbitrary-length messages natively — no separate pre-hash needed,
    unlike RSA)."""
    with open(path, "rb") as f:
        return sign_bytes(f.read())


def verify_signature(data: bytes, signature: bytes, public_key_pem: bytes = None) -> bool:
    """Real verification — returns False on ANY mismatch or corruption,
    never raises past this boundary and never returns True on a guess.
    If public_key_pem is omitted, verifies against this instance's own
    current public key (the common case: checking a release you just
    built); pass it explicitly to verify a package signed elsewhere."""
    try:
        if public_key_pem is None:
            public_key_pem = get_public_key_pem()
        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        public_key.verify(signature, data)
        return True
    except (InvalidSignature, ValueError):
        return False


def verify_file_signature(path, signature: bytes, public_key_pem: bytes = None) -> bool:
    with open(path, "rb") as f:
        return verify_signature(f.read(), signature, public_key_pem=public_key_pem)
