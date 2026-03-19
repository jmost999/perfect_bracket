"""
NCAA 2026 Bracket Verifier
Proves that a set of brackets existed before the tournament by recomputing
the Merkle root hash and comparing it to the one in MANIFEST.txt.

If someone doubts your brackets were made pre-tournament, share:
  1. This script
  2. Your MANIFEST.txt
  3. Your low_upset_brackets.jsonl.gz

They run this script and it will confirm the brackets hash to exactly
the root hash in your manifest — which you posted publicly before tip-off.

Usage:
    python verify_manifest.py
    python verify_manifest.py --manifest brackets_output/MANIFEST.txt \
                              --input   brackets_output/low_upset_brackets.jsonl.gz
"""

import gzip
import hashlib
import os
import argparse


def hash_line(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def merkle_root(hashes: list) -> str:
    if not hashes:
        return hashlib.sha256(b"empty").hexdigest()
    layer = hashes[:]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [
            hashlib.sha256((layer[i] + layer[i+1]).encode()).hexdigest()
            for i in range(0, len(layer), 2)
        ]
    return layer[0]


def load_manifest_root(manifest_path):
    """Extract the root hash and individual hashes from MANIFEST.txt."""
    root_hash = None
    manifest_hashes = []
    in_hashes_section = False

    with open(manifest_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("INDIVIDUAL BRACKET HASHES"):
                in_hashes_section = True
                continue
            if not in_hashes_section and stripped.startswith("ROOT HASH"):
                # Next non-empty, non-dashes line is the hash
                root_hash = "__next__"
                continue
            if root_hash == "__next__" and stripped and not stripped.startswith("─"):
                root_hash = stripped
                continue
            if in_hashes_section and stripped and not stripped.startswith("─"):
                parts = stripped.split()
                if len(parts) == 2:
                    manifest_hashes.append(parts[1])

    return root_hash, manifest_hashes


def load_bracket_hashes(gz_path):
    """Re-hash every bracket line from the .jsonl.gz file."""
    hashes = []
    opener = gzip.open if gz_path.endswith(".gz") else open
    with opener(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                hashes.append(hash_line(line))
    return hashes


def main():
    parser = argparse.ArgumentParser(description="NCAA 2026 Bracket Verifier")
    parser.add_argument("--manifest", type=str, default="brackets_output/MANIFEST.txt",
                        help="Path to MANIFEST.txt")
    parser.add_argument("--input",    type=str, default="brackets_output/low_upset_brackets.jsonl.gz",
                        help="Path to the bracket file (.jsonl or .jsonl.gz)")
    args = parser.parse_args()

    print(f"\n{'=' * 62}")
    print(f"  NCAA 2026 Bracket Verifier")
    print(f"{'=' * 62}")

    # Load manifest
    if not os.path.exists(args.manifest):
        print(f"\n  Error: manifest not found at '{args.manifest}'")
        return
    print(f"\n  Manifest:  {args.manifest}")
    manifest_root, manifest_hashes = load_manifest_root(args.manifest)
    print(f"  Root hash from manifest:")
    print(f"    {manifest_root}")
    print(f"  Individual hashes in manifest: {len(manifest_hashes):,}")

    # Re-hash bracket file
    if not os.path.exists(args.input):
        print(f"\n  Error: bracket file not found at '{args.input}'")
        return
    print(f"\n  Bracket file: {args.input}")
    print(f"  Re-hashing brackets... ", end="", flush=True)
    file_hashes = load_bracket_hashes(args.input)
    print(f"done. Found {len(file_hashes):,} brackets.")

    # Compare counts
    if len(file_hashes) != len(manifest_hashes):
        print(f"\n  WARNING: bracket count mismatch!")
        print(f"    Manifest has {len(manifest_hashes):,} hashes")
        print(f"    File has     {len(file_hashes):,} brackets")
        print(f"  The file may have been modified or truncated.")

    # Compare individual hashes
    mismatches = 0
    for i, (fh, mh) in enumerate(zip(file_hashes, manifest_hashes), 1):
        if fh != mh:
            mismatches += 1
            if mismatches <= 5:
                print(f"\n  MISMATCH at bracket #{i}:")
                print(f"    File:     {fh}")
                print(f"    Manifest: {mh}")

    if mismatches > 0:
        print(f"\n  FAILED: {mismatches:,} bracket(s) don't match the manifest.")
        print(f"  The brackets may have been tampered with.")
        return

    # Recompute Merkle root
    print(f"\n  Recomputing Merkle root... ", end="", flush=True)
    computed_root = merkle_root(file_hashes)
    print(f"done.")
    print(f"  Computed root hash:")
    print(f"    {computed_root}")

    print(f"\n{'─' * 62}")
    if computed_root == manifest_root:
        print(f"  VERIFIED")
        print(f"  The brackets match the manifest exactly.")
        print(f"  If the root hash was posted publicly before tip-off,")
        print(f"  these brackets are proven to be pre-tournament.")
    else:
        print(f"  FAILED: root hash mismatch!")
        print(f"  Expected: {manifest_root}")
        print(f"  Got:      {computed_root}")
        print(f"  The brackets do not match the original manifest.")
    print(f"{'=' * 62}\n")


if __name__ == "__main__":
    main()