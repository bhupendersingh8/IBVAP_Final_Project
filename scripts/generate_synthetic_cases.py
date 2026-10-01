#!/usr/bin/env python3
"""
Generate Synthetic Attack & Evaluation Suite (SIH26228)
======================================================
Generates deterministic synthetic attack cases under data/synthetic_eval/
with exact SHA-256 Merkle root provenance.
Runs 100% offline without network or operational data.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.assurance.synthetic_eval import generate_synthetic_suite


def main():
    target_dir = project_root / "data" / "synthetic_eval"
    print(f"[*] Generating SIH26228 Synthetic Attack & Evaluation Suite...")
    print(f"    Target directory: {target_dir}")

    provenance = generate_synthetic_suite(target_dir)

    print(f"[+] Successfully generated {provenance['total_cases']} synthetic test cases.")
    print(f"    Total files: {provenance['total_files']}")
    print(f"    Manifest SHA-256: {provenance['manifest_sha256']}")
    print(f"    Merkle Root:     {provenance['merkle_root']}")
    print(f"[+] Provenance saved to: {target_dir / 'synthetic_provenance.json'}")


if __name__ == "__main__":
    main()
