"""Encryption for member broker credentials, with key rotation.

KAOS_BROKER_VAULT_KEY encrypts new data. KAOS_BROKER_VAULT_PREVIOUS_KEYS (comma-separated) only decrypts,
so the key can be rotated: set the new key, move the old one to PREVIOUS, run `python broker_vault.py rotate`,
then remove the old key.
"""
import asyncio
import os

from cryptography.fernet import Fernet, MultiFernet
from fastapi import HTTPException

ENCRYPTED_FIELDS = ("key_name_enc", "private_key_enc")


def vault() -> MultiFernet:
    primary = os.environ.get("KAOS_BROKER_VAULT_KEY")
    if not primary:
        raise HTTPException(503, "Broker vault not configured on this server")
    previous = [k.strip() for k in os.environ.get("KAOS_BROKER_VAULT_PREVIOUS_KEYS", "").split(",") if k.strip()]
    return MultiFernet([Fernet(k.encode()) for k in [primary, *previous]])


async def rotate_all(collection) -> int:
    """Re-encrypt every stored broker credential under the primary key. Returns rows updated."""
    v, n = vault(), 0
    async for row in collection.find({}, {f: 1 for f in ENCRYPTED_FIELDS}):
        update = {f: v.rotate(row[f].encode()).decode() for f in ENCRYPTED_FIELDS if row.get(f)}
        if update:
            await collection.update_one({"_id": row["_id"]}, {"$set": update})
            n += 1
    return n


if __name__ == "__main__":
    import sys
    from database import db
    if sys.argv[1:] != ["rotate"]:
        sys.exit("usage: python broker_vault.py rotate")
    print(f"re-encrypted {asyncio.run(rotate_all(db.broker_connections))} broker connection(s)")
