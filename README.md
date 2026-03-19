# NCAA 2026 March Madness Bracket Simulator

A high-performance bracket simulation tool for generating and filtering millions of NCAA tournament brackets with cryptographic proof of pre-tournament generation.

## Overview

This project helps you generate millions of possible NCAA tournament brackets weighted by seed strength, save only the most likely outcomes, and then filter them as the real tournament progresses. The system includes cryptographic proof mechanisms so you can verify brackets were generated before the tournament started.

## Features

- **Mass Bracket Generation**: Simulate millions of brackets using seed-based probability models
- **Smart Filtering**: Only save brackets with few upsets (your best shots at perfection)
- **Cryptographic Proof**: SHA-256 hashing with Merkle tree structure proves brackets existed pre-tournament
- **Real-Time Filtering**: Eliminate impossible brackets as games are played
- **Performance Tracking**: Live stats showing generation rate, perfect brackets found, and champion distribution

## Quick Start

### 1. Generate Brackets

Run the generator to create millions of possible brackets:

```bash
# Run until 75 GB cap or Ctrl+C
python simulate_brackets.py

# Generate a specific number of brackets
python simulate_brackets.py --count 1000000

# Only save perfect brackets (no upsets)
python simulate_brackets.py --max-upsets 0

# Save brackets with up to 8 upsets (default)
python simulate_brackets.py --max-upsets 8
```

**Important**: The generator creates a `MANIFEST.txt` file with a root hash. **Post this hash publicly** (Twitter, Discord, GitHub gist) **before the tournament starts** to prove your brackets weren't created after seeing results.

### 2. Filter As Games Are Played

As real games happen, eliminate brackets that predicted wrong winners:

```bash
# Use default paths
python remove_non_perfect.py

# Specify custom bracket file
python remove_non_perfect.py --input brackets_output/low_upset_brackets.jsonl
```

The filter tool will:
- Show you all games for each round
- Let you enter actual winners
- Automatically eliminate brackets that got it wrong
- Save your results so you never re-enter data
- Show surviving bracket statistics

## Files & Output

### Generated Files

- **`low_upset_brackets.jsonl`** - Your saved brackets (plain text JSONL format)
- **`MANIFEST.txt`** - Cryptographic proof with root hash (POST THIS PUBLICLY!)
- **`STATS.txt`** - Champion frequency and upset statistics
- **`results.json`** - Your entered game results (auto-saved by filter)

### File Structure

Each bracket in the JSONL file contains:

```json
{
  "id": 12345,
  "upsets": 3,
  "champion": "Duke",
  "champion_seed": 1,
  "results": {
    "East": {
      "Round of 64": [...],
      "Round of 32": [...],
      "Sweet 16": [...],
      "Elite Eight": [...]
    },
    "West": {...},
    "Midwest": {...},
    "South": {...},
    "Final Four": [...],
    "Championship": {...}
  }
}
```

## 2026 Tournament Structure

### Regions & Seeds

**East Region**
- (1) Duke vs (16) Siena
- (2) UConn vs (15) Furman
- (3) Michigan State vs (14) North Dakota State
- (4) Kansas vs (13) Cal Baptist
- (5) St. Johns vs (12) Northern Iowa
- (6) Louisville vs (11) South Florida
- (7) UCLA vs (10) UCF
- (8) Ohio State vs (9) TCU

**West Region**
- (1) Arizona vs (16) LIU
- (2) Purdue vs (15) Queens
- (3) Gonzaga vs (14) Kennesaw State
- (4) Arkansas vs (13) Hawaii
- (5) Wisconsin vs (12) High Point
- (6) BYU vs (11) Texas
- (7) Miami FL vs (10) Missouri
- (8) Villanova vs (9) Utah State

**Midwest Region**
- (1) Michigan vs (16) UMBC
- (2) Iowa State vs (15) Tennessee State
- (3) Virginia vs (14) Wright State
- (4) Alabama vs (13) Hofstra
- (5) Texas Tech vs (12) Akron
- (6) Tennessee vs (11) SMU
- (7) Kentucky vs (10) Santa Clara
- (8) Georgia vs (9) Saint Louis

**South Region**
- (1) Florida vs (16) Prairie View A&M
- (2) Houston vs (15) Idaho
- (3) Illinois vs (14) Penn
- (4) Nebraska vs (13) Troy
- (5) Vanderbilt vs (12) McNeese
- (6) North Carolina vs (11) VCU
- (7) Saint Mary's vs (10) Texas A&M
- (8) Clemson vs (9) Iowa

## Probability Model

The simulator uses historical NCAA tournament data to weight matchups:

| Matchup | Higher Seed Win % |
|---------|-------------------|
| 1 vs 16 | 98.5% |
| 2 vs 15 | 94.0% |
| 3 vs 14 | 85.0% |
| 4 vs 13 | 79.5% |
| 5 vs 12 | 64.5% |
| 6 vs 11 | 62.0% |
| 7 vs 10 | 60.5% |
| 8 vs 9  | 52.0% |

For later rounds, probability is calculated dynamically based on seed differential.

## Advanced Usage

### Custom Storage Limits

```bash
# Stop at 50 GB instead of default 75 GB
python simulate_brackets.py --max-gb 50
```

### Progress Reporting

```bash
# Update stats every 1000 brackets instead of 10000
python simulate_brackets.py --stats-every 1000
```

### Filter Tool Options

```bash
# Specify custom results file location
python remove_non_perfect.py --results my_results.json

# Work with a different bracket set (supports both .jsonl and .jsonl.gz)
python remove_non_perfect.py --input different_brackets.jsonl
```

## Example Stats Output

After running the generator, you'll see statistics like:

```
SAVED BRACKET STATS
Brackets saved: 12,817,233  |  Perfect: 4  |  File: 47.33 GB

CHAMPION FREQUENCY (saved brackets only):
  Florida                   3,054,541 ( 23.8%)  ███████████
  Michigan                  3,053,823 ( 23.8%)  ███████████
  Arizona                   3,052,516 ( 23.8%)  ███████████
  Duke                      3,050,349 ( 23.8%)  ███████████
  UConn                      143,926 (  1.1%)  
  Purdue                     143,690 (  1.1%)  

TOP CINDERELLA TEAMS (saved brackets only):
  Utah State                3,292,273 upsets
  Iowa                      3,290,945 upsets
  TCU                       3,290,491 upsets
```

## Cryptographic Verification

### Why It Matters

The MANIFEST.txt file proves your brackets existed before the tournament. This is crucial if you want to demonstrate you predicted outcomes without cheating.

### How to Use It

1. **Before the tournament**: Post the root hash from MANIFEST.txt publicly with a timestamp
2. **After the tournament**: Share the full MANIFEST.txt and bracket file
3. **Anyone can verify**: Re-compute the Merkle root from your brackets and confirm it matches

### Verification Process

```bash
# Verify the manifest matches the brackets
python verify_manifest.py --manifest MANIFEST.txt \
                          --input low_upset_brackets.jsonl
```

The verifier will:
- Hash each bracket line using SHA-256
- Rebuild the Merkle tree structure
- Compare the computed root to the manifest's root hash
- Confirm all brackets are accounted for

## Performance Tips

### Maximizing Generation Speed

- Close other applications to free up CPU
- Run overnight for best results
- SSD storage recommended for I/O performance
- Adjust `--max-upsets` based on your goals:
  - `0` = only perfect brackets (very rare, slow progress)
  - `4` = very conservative (good filtering rate)
  - `8` = default (balanced)
  - `12` = more permissive (faster generation, larger files)

### Storage Considerations

- Each bracket is approximately 600-900 bytes (uncompressed JSONL)
- 1 million brackets ≈ 600-900 MB
- 10 million brackets ≈ 6-9 GB
- Default 75 GB limit ≈ 8-12 million brackets

**Note**: The filter tool can read both compressed (`.jsonl.gz`) and uncompressed (`.jsonl`) files, so you can manually compress the output file with gzip if needed to save disk space.

## Workflow Example

### Pre-Tournament

```bash
# Generate 10 million brackets overnight
python simulate_brackets.py --max-gb 8

# Post your root hash publicly
# Hash from MANIFEST.txt → Twitter/Discord/GitHub
```

### During Tournament

```bash
# Day 1: Enter Round of 64 results
python remove_non_perfect.py
# (Select games, enter winners)

# Day 2: Enter more results
python remove_non_perfect.py
# (Tool remembers previous results automatically)

# Check remaining champions
# Option 2 in menu: "Show surviving bracket stats"

# Save filtered survivors
# Option 5 in menu: "Save survivors to a new file"
```

### Post-Tournament

```bash
# Share proof
# - MANIFEST.txt
# - Original bracket file
# - Filtered survivors file
# - Verification instructions
```

## Requirements

- Python 3.7+
- Standard library only (no external dependencies)
- Sufficient disk space (see Storage Considerations)

## Troubleshooting

### Generator runs slowly

- Reduce `--max-upsets` to save fewer brackets
- Check available disk space
- Ensure no other I/O intensive processes running

### Filter tool says "No candidates found"

- This means none of your saved brackets predicted the matchup that occurred
- You may need to manually enter a team name (option M)
- Consider generating brackets with higher `--max-upsets` value

### File not found errors

- Default paths expect `brackets_output/` directory
- Generator creates this automatically
- Use `--input` flag to specify custom locations

## License

This project is provided as-is for educational and entertainment purposes.

## Contributing

Suggestions and improvements welcome! The probability model can be tuned based on more recent historical data.

## Disclaimer

This tool is for entertainment purposes. Perfect bracket odds remain astronomically low (approximately 1 in 9.2 quintillion for a truly random bracket). Even with millions of optimized simulations, a perfect bracket is extremely unlikely.

Good luck! 🏀
