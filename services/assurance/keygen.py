"""
services/assurance/keygen.py
============================
Offline Ed25519 Key Generation Utility for Contributor Model Manifests.

Provides safe, offline cryptographic key generation:
- Never commits or writes private keys to public directories.
- Outputs ephemeral hex keys or secure PEM files.
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from services.assurance.contributor_manifest import (
    generate_ed25519_keypair,
    export_ed25519_keypair_hex
)


def main():
    parser = argparse.ArgumentParser(description="Generate Ed25519 Keypair for Contributor Manifest Signing")
    parser.add_argument("--out-dir", type=str, default=None, help="Directory to save private.key and public.key")
    args = parser.parse_args()

    priv_key, pub_key = generate_ed25519_keypair()
    priv_hex, pub_hex = export_ed25519_keypair_hex(priv_key)

    if args.out_dir:
        out_path = Path(args.out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        priv_file = out_path / "ed25519_contributor_private.key"
        pub_file = out_path / "ed25519_contributor_public.key"

        with open(priv_file, "w") as f:
            f.write(priv_hex + "\n")
        with open(pub_file, "w") as f:
            f.write(pub_hex + "\n")

        print(f"[+] Private key saved to: {priv_file} (KEEP SECRET - DO NOT COMMIT)")
        print(f"[+] Public key saved to:  {pub_file}")
        print(f"Public Key (Hex): {pub_hex}")
    else:
        print("=" * 60)
        print("IBVAP Ed25519 Contributor Keypair (Generated Offline)")
        print("=" * 60)
        print(f"Public Key (Hex):  {pub_hex}")
        print(f"Private Key (Hex): {priv_hex}")
        print("=" * 60)
        print("[!] SECURITY WARNING: Never commit private keys to source control!")


if __name__ == "__main__":
    main()
