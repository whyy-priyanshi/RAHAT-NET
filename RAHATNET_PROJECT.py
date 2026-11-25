"""
RAHAT-NET: Rule-Based Disaster Relief Resource Allocation & Coordination System
Bennett University | Computational Thinking and Programming (2026CSAE100)

A rule-based decision-support aid (NOT ML/AI). Final relief decisions are always
made by trained disaster-management personnel.

Modules
  1. Area Data Entry & Validation
  2. Priority Score Calculator
  3. Ranking & Sorting
  4. Resource Allocation & Shortage Detection
  5. Conflict Detection
  6. Report Generation & File Storage
"""

import csv
from datetime import datetime

# ----------------------------------------------------------------------------
# Priority-score weights (Section 6 of the proposal)
# ----------------------------------------------------------------------------
W_SEVERITY = 0.35
W_URGENCY = 0.35
W_POPULATION = 0.20
W_RESOURCE = 0.10

MIN_LEVEL = 1
MAX_LEVEL = 5


# ============================================================================
# MODULE 1 - AREA DATA ENTRY & VALIDATION
# ============================================================================
def get_non_empty_text(prompt):
    """Keep asking until the user types a non-blank text value."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  [!] Input cannot be blank. Please try again.")


def get_unique_name(prompt, existing_names):
    """Non-empty area name that has not been used already (case-insensitive)."""
    while True:
        name = get_non_empty_text(prompt)
        if name.lower() in existing_names:
            print(f"  [!] '{name}' has already been entered. Use a different name.")
        else:
            return name


def get_positive_integer(prompt):
    """Keep asking until the user types a whole number greater than 0."""
    while True:
        raw = input(prompt).strip().replace(",", "")
        try:
            value = int(raw)
        except ValueError:
            print("  [!] Please enter a whole number (digits only).")
            continue
        if value <= 0:
            print("  [!] Value must be greater than 0.")
        else:
            return value


def get_non_negative_integer(prompt):
    """Keep asking until the user types a whole number greater than or equal to 0."""
    while True:
        raw = input(prompt).strip().replace(",", "")
        try:
            value = int(raw)
        except ValueError:
            print("  [!] Please enter a whole number (digits only).")
            continue
        if value < 0:
            print("  [!] Value cannot be negative.")
        else:
            return value


def get_level_in_range(prompt, low, high):
    """Keep asking until the user types a whole number between low and high."""
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  [!] Please enter a whole number between {low} and {high}.")
            continue
        if low <= value <= high:
            return value
        print(f"  [!] Value must be between {low} and {high}.")


def collect_area_data():
    """Ask for N, then read and validate N area records. Returns a list of dicts."""
    print("\n--- STEP 1: ENTER AFFECTED-AREA DATA ---")
    n = get_positive_integer("Enter number of affected areas (N): ")

    areas = []
    used_names = set()
    for i in range(1, n + 1):
        print(f"\nArea {i} of {n}")
        name = get_unique_name("  Area name                    : ", used_names)
        used_names.add(name.lower())
        population = get_positive_integer("  Population affected          : ")
        severity = get_level_in_range(
            f"  Severity ({MIN_LEVEL}-{MAX_LEVEL})                : ", MIN_LEVEL, MAX_LEVEL)
        urgency = get_level_in_range(
            f"  Urgency  ({MIN_LEVEL}-{MAX_LEVEL})                : ", MIN_LEVEL, MAX_LEVEL)
        required = get_positive_integer("  Resource required (units)    : ")

        areas.append({
            "name": name,
            "population": population,
            "severity": severity,
            "urgency": urgency,
            "resource_required": required,
        })
    return areas


# ============================================================================
# MODULE 2 - PRIORITY SCORE CALCULATOR
# ============================================================================
def calculate_priority_scores(areas):
    """
    Add a 'priority_score' (0-100) to every area dict.

    Each factor is first converted to a 0-100 score:
        severity_score   = severity / 5 * 100
        urgency_score    = urgency / 5 * 100
        population_score = population / max_population * 100
        resource_score   = resource_required / max_resource_required * 100
    Priority = 0.35*sev + 0.35*urg + 0.20*pop + 0.10*res
    """
    if not areas:
        return areas

    max_population = max(a["population"] for a in areas)
    max_resource = max(a["resource_required"] for a in areas)

    for a in areas:
        a["severity_score"] = a["severity"] / MAX_LEVEL * 100
        a["urgency_score"] = a["urgency"] / MAX_LEVEL * 100
        a["population_score"] = a["population"] / max_population * 100
        a["resource_score"] = a["resource_required"] / max_resource * 100

        a["priority_score"] = (
            W_SEVERITY * a["severity_score"]
            + W_URGENCY * a["urgency_score"]
            + W_POPULATION * a["population_score"]
            + W_RESOURCE * a["resource_score"]
        )
    return areas


# ============================================================================
# MODULE 3 - RANKING & SORTING
# ============================================================================
def rank_areas(areas):
    """Return areas sorted from highest to lowest priority, with a 'rank' added.
    Ties on the rounded score share the same rank (sorted() is stable, so tied
    areas keep their entry order)."""
    ranked = sorted(areas, key=lambda a: a["priority_score"], reverse=True)
    prev_score, prev_rank = None, 0
    for position, a in enumerate(ranked, start=1):
        score = round(a["priority_score"], 2)
        a["rank"] = prev_rank if score == prev_score else position
        prev_score, prev_rank = score, a["rank"]
    return ranked


def display_ranking(ranked_areas):
    """Print the ranking table (used before allocation)."""
    print("\n" + "=" * 60)
    print("PRIORITY RANKING")
    print("=" * 60)
    print(f"{'Rank':<6}{'Area':<22}{'Priority Score':>15}")
    print("-" * 60)
    for a in ranked_areas:
        print(f"{a['rank']:<6}{a['name'][:20]:<22}{a['priority_score']:>15.2f}")
    print("=" * 60)


# ============================================================================
# MODULE 4 - RESOURCE ALLOCATION & SHORTAGE DETECTION
# ============================================================================
def allocate_resources(ranked_areas, total_inventory):
    """
    Greedy allocation in ranked order. Adds 'allocated', 'shortfall' and
    'shortage' (bool) to each area. Returns (areas, remaining_inventory,
    shortage_areas).
    """
    remaining = total_inventory
    shortage_areas = []

    for a in ranked_areas:
        give = min(a["resource_required"], remaining)
        a["allocated"] = give
        a["shortfall"] = a["resource_required"] - give
        a["shortage"] = a["shortfall"] > 0
        remaining -= give
        if a["shortage"]:
            shortage_areas.append(a)

    return ranked_areas, remaining, shortage_areas


# ============================================================================
# MODULE 5 - CONFLICT DETECTION
# ============================================================================
def detect_conflicts(ranked_areas, total_inventory):
    """Return a list of warning strings that need coordinator attention."""
    warnings = []

    total_required = sum(a["resource_required"] for a in ranked_areas)
    if total_required > total_inventory:
        warnings.append(
            f"Total requirement ({total_required}) exceeds total inventory "
            f"({total_inventory}); shortfall of {total_required - total_inventory} units."
        )

    # Tied priority scores (compared at 2-decimal precision) - use a set to find repeats
    seen, tied_scores = set(), set()
    for a in ranked_areas:
        s = round(a["priority_score"], 2)
        if s in seen:
            tied_scores.add(s)
        seen.add(s)
    for s in sorted(tied_scores, reverse=True):
        names = [a["name"] for a in ranked_areas if round(a["priority_score"], 2) == s]
        warnings.append(
            f"Tie on priority score {s:.2f}: {', '.join(names)}. "
            "Coordinator should decide the order manually."
        )

    # A higher-ranked area partly served while a later area got nothing is expected,
    # but an area receiving ZERO resources is worth an explicit flag.
    for a in ranked_areas:
        if a["allocated"] == 0:
            warnings.append(f"{a['name']} (rank {a['rank']}) received NO resources.")

    if total_required < total_inventory:
        warnings.append(
            f"Surplus: {total_inventory - total_required} units remain after meeting all requirements."
        )
    return warnings


# ============================================================================
# MODULE 6 - REPORT GENERATION & FILE STORAGE
# ============================================================================
def build_report(ranked_areas, total_inventory, remaining, shortage_areas, warnings):
    """Build the full text report as a single string."""
    line = "=" * 86
    sub = "-" * 86
    out = []
    out.append(line)
    out.append("RAHAT-NET  -  RELIEF ALLOCATION SUMMARY REPORT")
    out.append(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}")
    out.append("Planning aid only - final decisions rest with authorised personnel.")
    out.append(line)
    out.append(f"{'Rank':<5}{'Area':<20}{'Score':>8}{'Required':>10}{'Allocated':>11}"
               f"{'Shortfall':>11}  Status")
    out.append(sub)
    for a in ranked_areas:
        status = "SHORTAGE" if a["shortage"] else "Fully served"
        out.append(f"{a['rank']:<5}{a['name'][:18]:<20}{a['priority_score']:>8.2f}"
                   f"{a['resource_required']:>10}{a['allocated']:>11}"
                   f"{a['shortfall']:>11}  {status}")
    out.append(sub)

    total_required = sum(a["resource_required"] for a in ranked_areas)
    total_allocated = sum(a["allocated"] for a in ranked_areas)
    out.append(f"Total inventory : {total_inventory}")
    out.append(f"Total required  : {total_required}")
    out.append(f"Total allocated : {total_allocated}")
    out.append(f"Inventory left  : {remaining}")

    out.append("")
    out.append("SHORTAGE AREAS")
    if shortage_areas:
        for a in shortage_areas:
            pct = a["allocated"] / a["resource_required"] * 100
            out.append(f"  - {a['name']}: short by {a['shortfall']} units "
                       f"({pct:.0f}% of requirement met)")
    else:
        out.append("  None - all areas fully served.")

    out.append("")
    out.append("CONFLICTS / WARNINGS")
    if warnings:
        for w in warnings:
            out.append(f"  ! {w}")
    else:
        out.append("  None.")
    out.append(line)
    return "\n".join(out)


def save_report_txt(report_text, filename):
    """Write the report to a TXT file; returns True on success."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_text + "\n")
        return True
    except OSError as err:
        print(f"  [!] Could not save TXT file: {err}")
        return False


def save_report_csv(ranked_areas, filename):
    """Write the ranked/allocated table to a CSV file; returns True on success."""
    fields = ["rank", "name", "population", "severity", "urgency",
              "resource_required", "priority_score", "allocated", "shortfall", "shortage"]
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for a in ranked_areas:
                row = dict(a)
                row["priority_score"] = f"{a['priority_score']:.2f}"
                writer.writerow(row)
        return True
    except OSError as err:
        print(f"  [!] Could not save CSV file: {err}")
        return False


def ask_yes_no(prompt):
    """Return True for yes, False for no; re-ask on anything else."""
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  [!] Please answer y or n.")


def offer_to_save(report_text, ranked_areas):
    if not ask_yes_no("\nSave report to file? (y/n): "):
        print("Report not saved.")
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"rahatnet_report_{stamp}"
    choice = ""
    while choice not in ("1", "2", "3"):
        choice = input("Format: 1) TXT   2) CSV   3) Both  -> ").strip()
        if choice not in ("1", "2", "3"):
            print("  [!] Enter 1, 2 or 3.")
    if choice in ("1", "3") and save_report_txt(report_text, base + ".txt"):
        print(f"  Saved: {base}.txt")
    if choice in ("2", "3") and save_report_csv(ranked_areas, base + ".csv"):
        print(f"  Saved: {base}.csv")


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 60)
    print(" RAHAT-NET : Disaster Relief Resource Allocation System")
    print(" (Rule-based planning aid - not an official authority)")
    print("=" * 60)

    # Module 1
    areas = collect_area_data()

    # Modules 2 & 3
    calculate_priority_scores(areas)
    ranked = rank_areas(areas)
    display_ranking(ranked)

    # Module 4
    print("\n--- STEP 2: RESOURCE INVENTORY ---")
    inventory = get_non_negative_integer("Enter total available resource inventory (units): ")
    ranked, remaining, shortage_areas = allocate_resources(ranked, inventory)

    # Module 5
    warnings = detect_conflicts(ranked, inventory)

    # Module 6
    report = build_report(ranked, inventory, remaining, shortage_areas, warnings)
    print("\n" + report)
    offer_to_save(report, ranked)

    print("\nThank you for using RAHAT-NET. Stay safe.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nProgram interrupted. Exiting.")
