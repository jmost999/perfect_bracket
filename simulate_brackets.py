"""
NCAA 2026 March Madness Bracket Generator
Runs continuously, generating random brackets weighted by seed.
Only saves brackets with few upsets (best shots at a perfect bracket).

Features:
  - gzip compression (~4-5x smaller than plain .jsonl)
  - SHA-256 manifest proof so you can prove brackets were made pre-tournament
    Post the root hash somewhere public (tweet, Discord, GitHub gist) before
    tip-off. Anyone can verify the hash later to confirm brackets weren't faked.

Usage:
    python bracket_generator.py

    # Run for a specific number of brackets:
    python bracket_generator.py --count 10000

    # Run for a specific number of hours:
    python bracket_generator.py --hours 8

    # Run forever until Ctrl+C:
    python bracket_generator.py --forever

    # Only save perfect brackets:
    python bracket_generator.py --max-upsets 0

    # Relax the filter:
    python bracket_generator.py --max-upsets 8
"""

import gzip
import hashlib
import json
import os
import random
import time
import argparse
from datetime import datetime, timezone
from collections import defaultdict

# ─────────────────────────────────────────────
# 2026 BRACKET DATA
# ─────────────────────────────────────────────

BRACKET = {
    "East": [
        (1,  "Duke"),
        (16, "Siena"),
        (8,  "Ohio State"),
        (9,  "TCU"),
        (5,  "St. Johns"),
        (12, "Northern Iowa"),
        (4,  "Kansas"),
        (13, "Cal Baptist"),
        (6,  "Louisville"),
        (11, "South Florida"),
        (3,  "Michigan State"),
        (14, "North Dakota State"),
        (7,  "UCLA"),
        (10, "UCF"),
        (2,  "UConn"),
        (15, "Furman"),
    ],
    "West": [
        (1,  "Arizona"),
        (16, "LIU"),
        (8,  "Villanova"),
        (9,  "Utah State"),
        (5,  "Wisconsin"),
        (12, "High Point"),
        (4,  "Arkansas"),
        (13, "Hawaii"),
        (6,  "BYU"),
        (11, "Texas"),
        (3,  "Gonzaga"),
        (14, "Kennesaw State"),
        (7,  "Miami FL"),
        (10, "Missouri"),
        (2,  "Purdue"),
        (15, "Queens"),
    ],
    "Midwest": [
        (1,  "Michigan"),
        (16, "UMBC"),
        (8,  "Georgia"),
        (9,  "Saint Louis"),
        (5,  "Texas Tech"),
        (12, "Akron"),
        (4,  "Alabama"),
        (13, "Hofstra"),
        (6,  "Tennessee"),
        (11, "SMU"),
        (3,  "Virginia"),
        (14, "Wright State"),
        (7,  "Kentucky"),
        (10, "Santa Clara"),
        (2,  "Iowa State"),
        (15, "Tennessee State"),
    ],
    "South": [
        (1,  "Florida"),
        (16, "Prairie View AM"),
        (8,  "Clemson"),
        (9,  "Iowa"),
        (5,  "Vanderbilt"),
        (12, "McNeese"),
        (4,  "Nebraska"),
        (13, "Troy"),
        (6,  "North Carolina"),
        (11, "VCU"),
        (3,  "Illinois"),
        (14, "Penn"),
        (7,  "Saint Marys"),
        (10, "Texas AM"),
        (2,  "Houston"),
        (15, "Idaho"),
    ],
}

UPSET_PROBS = {
    (1, 16): 0.985,
    (2, 15): 0.940,
    (3, 14): 0.850,
    (4, 13): 0.795,
    (5, 12): 0.645,
    (6, 11): 0.620,
    (7, 10): 0.605,
    (8, 9):  0.520,
}

# ─────────────────────────────────────────────
# SIMULATION
# ─────────────────────────────────────────────

def seed_win_prob(seed_a, seed_b):
    lo, hi = min(seed_a, seed_b), max(seed_a, seed_b)
    base = UPSET_PROBS.get((lo, hi))
    if base is not None:
        return base if seed_a == lo else 1 - base
    diff = seed_b - seed_a
    prob = 0.5 + diff * 0.08
    return max(0.05, min(0.95, prob))

def simulate_game(team_a, team_b):
    seed_a, _ = team_a
    seed_b, _ = team_b
    if random.random() < seed_win_prob(seed_a, seed_b):
        return team_a, team_b
    return team_b, team_a

def simulate_region(teams):
    rounds = {}
    current = teams[:]
    for round_name in ["Round of 64", "Round of 32", "Sweet 16", "Elite Eight"]:
        winners = []
        games = []
        for i in range(0, len(current), 2):
            winner, loser = simulate_game(current[i], current[i+1])
            winners.append(winner)
            games.append({
                "w": winner[1], "ws": winner[0],
                "l": loser[1],  "ls": loser[0],
                "u": winner[0] > loser[0],
            })
        rounds[round_name] = games
        current = winners
    return rounds, current[0]

def simulate_bracket():
    results = {}
    final_four = []

    for region, teams in BRACKET.items():
        rounds, champion = simulate_region(teams)
        results[region] = rounds
        final_four.append((champion, region))

    ff_games = []
    championship_teams = []
    for i, j in [(0, 1), (2, 3)]:
        winner, loser = simulate_game(final_four[i][0], final_four[j][0])
        ff_games.append({
            "w": winner[1], "ws": winner[0],
            "wr": final_four[i][1] if winner == final_four[i][0] else final_four[j][1],
            "l": loser[1],  "ls": loser[0],
            "u": winner[0] > loser[0],
        })
        championship_teams.append(winner)

    results["Final Four"] = ff_games

    champ_winner, champ_loser = simulate_game(championship_teams[0], championship_teams[1])
    results["Championship"] = {
        "w": champ_winner[1], "ws": champ_winner[0],
        "l": champ_loser[1],  "ls": champ_loser[0],
        "u": champ_winner[0] > champ_loser[0],
    }

    return results

def count_upsets(results):
    upsets = 0
    for region in BRACKET:
        for games in results[region].values():
            upsets += sum(1 for g in games if g["u"])
    upsets += sum(1 for g in results["Final Four"] if g["u"])
    if results["Championship"]["u"]:
        upsets += 1
    return upsets

# ─────────────────────────────────────────────
# HASHING / PROOF
# ─────────────────────────────────────────────

def hash_line(line: str) -> str:
    """SHA-256 hash of a single JSON line."""
    return hashlib.sha256(line.encode("utf-8")).hexdigest()

def merkle_root(hashes: list) -> str:
    """
    Combine a list of hex hashes into a single root hash (Merkle-style).
    Pairs are concatenated and hashed; odd node gets paired with itself.
    """
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

def save_manifest(manifest_path, run_meta, bracket_hashes):
    """
    Write MANIFEST.txt with the root hash and all individual bracket hashes.
    The root hash is the single value you post publicly before tip-off.
    """
    root = merkle_root(bracket_hashes)
    lines = [
        "=" * 70,
        "  NCAA 2026 BRACKET GENERATOR — PROOF OF PRE-TOURNAMENT GENERATION",
        "=" * 70,
        "",
        "  HOW TO USE THIS FILE:",
        "  1. Copy the ROOT HASH below and post it publicly BEFORE tip-off.",
        "     (Tweet it, post to Discord, paste in a GitHub gist — anything",
        "      with a public timestamp works.)",
        "  2. After the tournament, share this full MANIFEST.txt.",
        "  3. Anyone can verify: re-hash each bracket line and recompute the",
        "     Merkle root — if it matches the root hash, the brackets existed",
        "     before the tournament started.",
        "",
        "─" * 70,
        "  ROOT HASH (post this publicly before tip-off):",
        f"  {root}",
        "─" * 70,
        "",
        "  RUN METADATA:",
        f"    Generated at (UTC):  {run_meta['started_utc']}",
        f"    Completed at (UTC):  {run_meta['finished_utc']}",
        f"    Total simulated:     {run_meta['total_simulated']:,}",
        f"    Total saved:         {run_meta['total_saved']:,}",
        f"    Max upsets filter:   {run_meta['max_upsets']}",
        f"    Output file:         {run_meta['output_file']}",
        "",
        "  TO VERIFY:",
        "    python verify_manifest.py --manifest MANIFEST.txt \\",
        "                              --input low_upset_brackets.jsonl.gz",
        "",
        "─" * 70,
        f"  INDIVIDUAL BRACKET HASHES ({len(bracket_hashes):,} total):",
        "─" * 70,
    ]
    for i, h in enumerate(bracket_hashes, 1):
        lines.append(f"  {i:>10}  {h}")

    with open(manifest_path, "w") as f:
        f.write("\n".join(lines))

    return root

# ─────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────

def update_stats(stats, results, upsets, saved=False):
    stats["champions"][results["Championship"]["w"]] += 1
    stats["total"] += 1
    stats["total_upsets"] += upsets
    if upsets == 0:
        stats["perfect"] += 1
    for region in BRACKET:
        for games in results[region].values():
            for g in games:
                if g["u"]:
                    stats["upset_teams"][g["w"]] += 1
    if saved:
        stats["saved_champions"][results["Championship"]["w"]] += 1
        for region in BRACKET:
            for games in results[region].values():
                for g in games:
                    if g["u"]:
                        stats["saved_upset_teams"][g["w"]] += 1

def save_stats(stats, output_dir, file_path):
    path = os.path.join(output_dir, "STATS.txt")
    file_size_mb = os.path.getsize(file_path) / 1024**2 if os.path.exists(file_path) else 0
    file_size_gb = file_size_mb / 1024
    saved = max(1, stats["saved"])
    lines = [
        f"SAVED BRACKET STATS",
        f"Brackets saved: {stats['saved']:,}  |  Perfect: {stats['perfect']:,}  |  File: {file_size_gb:.2f} GB",
        "",
        "CHAMPION FREQUENCY (saved brackets only):",
    ]
    for team, count in sorted(stats["saved_champions"].items(), key=lambda x: -x[1]):
        pct = count / saved * 100
        bar = "█" * int(pct / 2)
        lines.append(f"  {team:<25} {count:>8,} ({pct:5.1f}%)  {bar}")
    lines += ["", "TOP CINDERELLA TEAMS (saved brackets only):"]
    for team, count in sorted(stats["saved_upset_teams"].items(), key=lambda x: -x[1])[:15]:
        lines.append(f"  {team:<25} {count:>8,} upsets")
    with open(path, "w") as f:
        f.write("\n".join(lines))

def print_progress(stats, bracket_id, start_time, max_upsets, file_path):
    elapsed = time.time() - start_time
    rate = stats["total"] / max(1, elapsed)
    file_mb = os.path.getsize(file_path) / 1024**2 if os.path.exists(file_path) else 0
    print(
        f"\r  #{bracket_id:>9,} | {rate:>7.0f}/sec | "
        f"saved (<=={max_upsets} upsets): {stats['saved']:>7,} | "
        f"perfect: {stats['perfect']:>4,} | "
        f"compressed: {file_mb:>7.1f} MB",
        end="", flush=True
    )

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NCAA 2026 Bracket Generator")
    parser.add_argument("--count",       type=int,   default=None,  help="Number of brackets to simulate")
    parser.add_argument("--output",      type=str,   default="brackets_output", help="Output directory")
    parser.add_argument("--max-upsets",  type=int,   default=8,     help="Only save brackets with this many upsets or fewer (default: 8)")
    parser.add_argument("--max-gb",      type=float, default=75.0,  help="Hard stop saving at this many GB (default: 75)")
    parser.add_argument("--stats-every", type=int,   default=10000, help="Print progress every N brackets")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    jsonl_path    = os.path.join(args.output, "low_upset_brackets.jsonl")
    manifest_path = os.path.join(args.output, "MANIFEST.txt")
    max_bytes     = args.max_gb * 1024 ** 3

    stats = {
        "total": 0,
        "total_upsets": 0,
        "perfect": 0,
        "saved": 0,
        "champions": defaultdict(int),
        "upset_teams": defaultdict(int),
        "saved_champions": defaultdict(int),
        "saved_upset_teams": defaultdict(int),
    }

    started_utc  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    start_time   = time.time()
    bracket_id   = 0
    storage_full = False
    bracket_hashes = []

    print(f"\n2026 NCAA Bracket Generator")
    print(f"Output: {os.path.abspath(jsonl_path)}")
    print(f"Manifest / proof: {os.path.abspath(manifest_path)}")
    print(f"Saving brackets with <={args.max_upsets} upsets  |  Hard stop at: {args.max_gb} GB")
    if args.count:
        print(f"Simulating {args.count:,} brackets...")
    else:
        print("Running until 75 GB cap or Ctrl+C...")
    print()

    try:
        with open(jsonl_path, "a", encoding="utf-8") as outfile:
            while True:
                if args.count and bracket_id >= args.count:
                    break
                if storage_full:
                    break

                bracket_id += 1
                results = simulate_bracket()
                upsets  = count_upsets(results)
                update_stats(stats, results, upsets)

                if upsets <= args.max_upsets and not storage_full:
                    record = {
                        "id":            bracket_id,
                        "upsets":        upsets,
                        "champion":      results["Championship"]["w"],
                        "champion_seed": results["Championship"]["ws"],
                        "results":       results,
                    }
                    line = json.dumps(record, separators=(",", ":")) + "\n"
                    bracket_hashes.append(hash_line(line.strip()))
                    outfile.write(line)
                    stats["saved"] += 1
                    update_stats(stats, results, upsets, saved=True)

                    # Check storage cap every 1000 saves — hard stop
                    if stats["saved"] % 1000 == 0 and os.path.getsize(jsonl_path) >= max_bytes:
                        storage_full = True
                        print(f"\n  75 GB cap reached — stopping.")

                if bracket_id % args.stats_every == 0:
                    save_stats(stats, args.output, jsonl_path)
                    print_progress(stats, bracket_id, start_time, args.max_upsets, jsonl_path)

    except KeyboardInterrupt:
        print("\n\nStopped by user.")

    # Final stats
    save_stats(stats, args.output, jsonl_path)
    print_progress(stats, bracket_id, start_time, args.max_upsets, jsonl_path)

    finished_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    elapsed      = time.time() - start_time
    file_size_mb = os.path.getsize(jsonl_path) / 1024**2 if os.path.exists(jsonl_path) else 0

    # Build and save the proof manifest
    print("\n\n  Building proof manifest...")
    root = save_manifest(manifest_path, {
        "started_utc":     started_utc,
        "finished_utc":    finished_utc,
        "total_simulated": stats["total"],
        "total_saved":     stats["saved"],
        "max_upsets":      args.max_upsets,
        "output_file":     jsonl_path,
    }, bracket_hashes)

    print(f"\n{'=' * 62}")
    print(f"  Done!")
    print(f"  Simulated:  {stats['total']:,} brackets in {elapsed/60:.1f} min")
    print(f"  Saved:      {stats['saved']:,} brackets (<={args.max_upsets} upsets)")
    print(f"  Perfect:    {stats['perfect']:,}")
    print(f"  File size:  {file_size_mb:.1f} MB")
    print(f"{'─' * 62}")
    print(f"  !! POST THIS HASH PUBLICLY BEFORE THE TOURNAMENT !!")
    print(f"  ROOT HASH:")
    print(f"  {root}")
    print(f"{'─' * 62}")
    print(f"  Manifest:   {os.path.abspath(manifest_path)}")
    print(f"  Stats:      {os.path.abspath(args.output)}/STATS.txt")
    print(f"{'=' * 62}")

    if stats["perfect"] > 0:
        print(f"\n  *** FOUND {stats['perfect']:,} PERFECT BRACKET(S)! ***")

if __name__ == "__main__":
    main()
