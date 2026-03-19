"""
NCAA 2026 Bracket Filter
Enter real game results to eliminate brackets that no longer match.

Run this any time during the tournament to prune your saved brackets.
Each time you enter a new result, any bracket that predicted the wrong
winner for that game gets removed. What's left are still-viable brackets.

Usage:
    python filter_results.py
    python filter_results.py --input brackets_output/low_upset_brackets.jsonl

Your entered results are saved to results.json automatically so you never
have to re-enter old results — just run it again each day and add new ones.
"""

import gzip
import json
import os
import argparse
from collections import defaultdict

# ─────────────────────────────────────────────
# 2026 BRACKET STRUCTURE (must match generator)
# ─────────────────────────────────────────────

BRACKET = {
    "East": [
        (1,  "Duke"),           (16, "Siena"),
        (8,  "Ohio State"),     (9,  "TCU"),
        (5,  "St. Johns"),      (12, "Northern Iowa"),
        (4,  "Kansas"),         (13, "Cal Baptist"),
        (6,  "Louisville"),     (11, "South Florida"),
        (3,  "Michigan State"), (14, "North Dakota State"),
        (7,  "UCLA"),           (10, "UCF"),
        (2,  "UConn"),          (15, "Furman"),
    ],
    "West": [
        (1,  "Arizona"),        (16, "LIU"),
        (8,  "Villanova"),      (9,  "Utah State"),
        (5,  "Wisconsin"),      (12, "High Point"),
        (4,  "Arkansas"),       (13, "Hawaii"),
        (6,  "BYU"),            (11, "Texas"),
        (3,  "Gonzaga"),        (14, "Kennesaw State"),
        (7,  "Miami FL"),       (10, "Missouri"),
        (2,  "Purdue"),         (15, "Queens"),
    ],
    "Midwest": [
        (1,  "Michigan"),       (16, "UMBC"),
        (8,  "Georgia"),        (9,  "Saint Louis"),
        (5,  "Texas Tech"),     (12, "Akron"),
        (4,  "Alabama"),        (13, "Hofstra"),
        (6,  "Tennessee"),      (11, "SMU"),
        (3,  "Virginia"),       (14, "Wright State"),
        (7,  "Kentucky"),       (10, "Santa Clara"),
        (2,  "Iowa State"),     (15, "Tennessee State"),
    ],
    "South": [
        (1,  "Florida"),        (16, "Prairie View AM"),
        (8,  "Clemson"),        (9,  "Iowa"),
        (5,  "Vanderbilt"),     (12, "McNeese"),
        (4,  "Nebraska"),       (13, "Troy"),
        (6,  "North Carolina"), (11, "VCU"),
        (3,  "Illinois"),       (14, "Penn"),
        (7,  "Saint Marys"),    (10, "Texas AM"),
        (2,  "Houston"),        (15, "Idaho"),
    ],
}

REGIONS = ["East", "West", "Midwest", "South"]
ROUND_NAMES = ["Round of 64", "Round of 32", "Sweet 16", "Elite Eight"]

# ─────────────────────────────────────────────
# LOAD / SAVE HELPERS
# ─────────────────────────────────────────────

def load_brackets(jsonl_path):
    if not os.path.exists(jsonl_path):
        print(f"\n  Error: '{jsonl_path}' not found.")
        print(  "  Run bracket_generator.py first to generate brackets.")
        return []
    brackets = []
    opener = gzip.open if jsonl_path.endswith(".gz") else open
    with opener(jsonl_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    brackets.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return brackets

def save_brackets(brackets, path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "wt", encoding="utf-8") as f:
        for b in brackets:
            f.write(json.dumps(b, separators=(",", ":")) + "\n")

def load_results(results_path):
    """Load previously entered real results."""
    if os.path.exists(results_path):
        with open(results_path) as f:
            return json.load(f)
    return []

def save_results(results, results_path):
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

# ─────────────────────────────────────────────
# BRACKET MATCHING
# ─────────────────────────────────────────────

def get_predicted_winner(bracket, region, round_name, game_index):
    """Get what a bracket predicted for a given game."""
    try:
        if region in REGIONS:
            return bracket["results"][region][round_name][game_index]["w"]
        elif region == "Final Four":
            return bracket["results"]["Final Four"][game_index]["w"]
        elif region == "Championship":
            return bracket["results"]["Championship"]["w"]
    except (KeyError, IndexError):
        return None

def bracket_still_valid(bracket, known_results):
    """Return True if bracket correctly predicted every known result."""
    for r in known_results:
        predicted = get_predicted_winner(
            bracket, r["region"], r["round"], r["game_index"]
        )
        if predicted != r["winner"]:
            return False
    return True

def filter_brackets(brackets, known_results):
    return [b for b in brackets if bracket_still_valid(b, known_results)]

# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────

def sep(char="─", width=62):
    print(char * width)

def show_survivors(brackets):
    if not brackets:
        print("\n  !! Zero surviving brackets — no saved bracket predicted this correctly.")
        return
    champ_counts = defaultdict(int)
    for b in brackets:
        champ_counts[b["champion"]] += 1
    print(f"\n  Surviving brackets: {len(brackets):,}")
    print(f"  Remaining champion distribution:")
    for team, count in sorted(champ_counts.items(), key=lambda x: -x[1]):
        pct = count / len(brackets) * 100
        bar = "█" * max(1, int(pct / 2))
        print(f"    {team:<25} {count:>6,}  ({pct:5.1f}%)  {bar}")

def show_known_results(known_results):
    if not known_results:
        print("  (none yet)")
        return
    for r in known_results:
        label = f"{r['region']} — {r['round']} game {r['game_index'] + 1}"
        print(f"  ✓  {r['winner']:<25}  [{label}]")

# ─────────────────────────────────────────────
# GAME SELECTION MENUS
# ─────────────────────────────────────────────

def pick_round():
    """Let user choose which round to enter a result for."""
    options = []
    for region in REGIONS:
        for round_name in ROUND_NAMES:
            options.append((region, round_name))
    options.append(("Final Four", "Final Four"))
    options.append(("Championship", "Championship"))

    print("\n  Which round?")
    for i, (region, round_name) in enumerate(options, 1):
        if region in ("Final Four", "Championship"):
            print(f"    {i:>2}.  {region}")
        else:
            print(f"    {i:>2}.  {region} — {round_name}")
    print(f"    {0:>2}.  Cancel")

    while True:
        raw = input("\n  Enter number: ").strip()
        if raw == "0":
            return None, None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("  Invalid choice, try again.")

def pick_game(region, round_name, known_results):
    """
    Show the games for the selected round and let user pick one.
    For Round of 64 we know exact matchups. For later rounds we show
    game slots (1, 2, 3...) since teams depend on prior results.
    """
    already_entered = {
        (r["region"], r["round"], r["game_index"])
        for r in known_results
    }

    if region == "Final Four":
        matchups = [
            (0, "East champion  vs  West champion"),
            (1, "Midwest champion  vs  South champion"),
        ]
        print("\n  Final Four games:")
        for game_index, label in matchups:
            tag = " ✓" if ("Final Four", "Final Four", game_index) in already_entered else ""
            print(f"    {game_index + 1}.  {label}{tag}")
        print(f"    0.  Cancel")

        while True:
            raw = input("\n  Pick game: ").strip()
            if raw == "0":
                return None
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(matchups):
                    return idx
            except ValueError:
                pass
            print("  Invalid choice.")

    elif region == "Championship":
        return 0  # only one game

    else:
        # Regional rounds
        teams = BRACKET[region]
        num_games = len(teams) // (2 ** (ROUND_NAMES.index(round_name) + 1))

        if round_name == "Round of 64":
            # We know exact matchups
            pairs = [(teams[i], teams[i+1]) for i in range(0, len(teams), 2)]
            print(f"\n  {region} — {round_name} games:")
            for i, (a, b) in enumerate(pairs):
                tag = " ✓" if (region, round_name, i) in already_entered else ""
                print(f"    {i+1}.  ({a[0]}) {a[1]}  vs  ({b[0]}) {b[1]}{tag}")
        else:
            print(f"\n  {region} — {round_name} games (teams depend on prior results):")
            for i in range(num_games):
                tag = " ✓" if (region, round_name, i) in already_entered else ""
                print(f"    {i+1}.  Game {i+1}{tag}")

        print(f"    0.  Cancel")

        while True:
            raw = input("\n  Pick game: ").strip()
            if raw == "0":
                return None
            try:
                idx = int(raw) - 1
                if 0 <= idx < num_games:
                    return idx
            except ValueError:
                pass
            print("  Invalid choice.")

def pick_winner_from_brackets(brackets, region, round_name, game_index):
    """
    Show the unique teams that appear as winner for this game slot
    across all surviving brackets, letting user pick the real winner.
    """
    candidates = sorted(set(
        get_predicted_winner(b, region, round_name, game_index)
        for b in brackets
        if get_predicted_winner(b, region, round_name, game_index)
    ))

    if not candidates:
        print("  No candidates found for this game slot in surviving brackets.")
        return None

    print(f"\n  Who won? (teams seen across your surviving brackets)")
    for i, name in enumerate(candidates, 1):
        count = sum(
            1 for b in brackets
            if get_predicted_winner(b, region, round_name, game_index) == name
        )
        pct = count / len(brackets) * 100
        print(f"    {i}.  {name:<25}  predicted by {count:,} brackets ({pct:.1f}%)")
    print(f"    0.  Cancel / not played yet")
    print(f"    M.  Manually type a team name")

    while True:
        raw = input("\n  Enter number (or M): ").strip()
        if raw == "0":
            return None
        if raw.upper() == "M":
            name = input("  Team name: ").strip()
            return name if name else None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        except ValueError:
            pass
        print("  Invalid choice.")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NCAA 2026 Bracket Filter")
    parser.add_argument("--input",   type=str, default="brackets_output/low_upset_brackets.jsonl",
                        help="Path to the .jsonl bracket file")
    parser.add_argument("--results", type=str, default="brackets_output/results.json",
                        help="Path to save/load your entered results")
    args = parser.parse_args()

    print("\n" + "=" * 62)
    print("  NCAA 2026 Bracket Filter")
    print("=" * 62)

    # Load brackets
    print(f"\n  Loading brackets from: {args.input}")
    all_brackets = load_brackets(args.input)
    if not all_brackets:
        return
    print(f"  Loaded {len(all_brackets):,} brackets")

    # Load previously saved results
    known_results = load_results(args.results)
    if known_results:
        print(f"\n  Previously entered results ({len(known_results)}):")
        show_known_results(known_results)

    # Apply existing results to get current survivors
    survivors = filter_brackets(all_brackets, known_results)
    print(f"\n  Brackets still alive after previous results: {len(survivors):,}")

    # Main loop
    while True:
        print()
        sep()
        print(f"  Surviving brackets: {len(survivors):,}  |  Results entered: {len(known_results)}")
        sep()
        print("  Options:")
        print("    1.  Enter a new game result")
        print("    2.  Show surviving bracket stats")
        print("    3.  Show all entered results")
        print("    4.  Undo last result")
        print("    5.  Save survivors to a new file")
        print("    0.  Quit")

        choice = input("\n  Choice: ").strip()

        # ── Enter a result ──────────────────────────────────────
        if choice == "1":
            region, round_name = pick_round()
            if region is None:
                continue

            game_index = pick_game(region, round_name, known_results)
            if game_index is None:
                continue

            # Check if already entered
            existing = next(
                (r for r in known_results
                 if r["region"] == region and r["round"] == round_name and r["game_index"] == game_index),
                None
            )
            if existing:
                print(f"\n  Already entered: {existing['winner']} won this game.")
                overwrite = input("  Overwrite? (y/n): ").strip().lower()
                if overwrite != "y":
                    continue
                known_results.remove(existing)

            winner = pick_winner_from_brackets(survivors, region, round_name, game_index)
            if winner is None:
                continue

            new_result = {
                "region": region,
                "round": round_name,
                "game_index": game_index,
                "winner": winner,
            }
            known_results.append(new_result)
            save_results(known_results, args.results)

            # Filter
            before = len(survivors)
            survivors = filter_brackets(survivors, [new_result])
            eliminated = before - len(survivors)

            print(f"\n  Result recorded: {winner} wins")
            print(f"  Eliminated {eliminated:,} brackets  ({before:,} → {len(survivors):,} remaining)")
            show_survivors(survivors)

        # ── Show stats ──────────────────────────────────────────
        elif choice == "2":
            show_survivors(survivors)

        # ── Show entered results ────────────────────────────────
        elif choice == "3":
            print("\n  Results entered so far:")
            show_known_results(known_results)

        # ── Undo last result ────────────────────────────────────
        elif choice == "4":
            if not known_results:
                print("\n  Nothing to undo.")
                continue
            removed = known_results.pop()
            save_results(known_results, args.results)
            survivors = filter_brackets(all_brackets, known_results)
            print(f"\n  Undid: {removed['winner']} ({removed['region']} — {removed['round']} game {removed['game_index']+1})")
            print(f"  Brackets restored to: {len(survivors):,}")

        # ── Save survivors ──────────────────────────────────────
        elif choice == "5":
            if not survivors:
                print("\n  No survivors to save.")
                continue
            default_out = args.input.replace(".jsonl.gz", "_filtered.jsonl.gz").replace(".jsonl", "_filtered.jsonl.gz")
            out_path = input(f"  Save to [{default_out}]: ").strip() or default_out
            save_brackets(survivors, out_path)
            size_mb = os.path.getsize(out_path) / 1024**2
            print(f"  Saved {len(survivors):,} brackets → {out_path} ({size_mb:.1f} MB)")

        # ── Quit ────────────────────────────────────────────────
        elif choice == "0":
            print(f"\n  Exiting. {len(survivors):,} brackets still alive.")
            break

        else:
            print("  Invalid choice.")

if __name__ == "__main__":
    main()