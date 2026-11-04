"""Check the public summary by enumerating the authored game with rational arithmetic."""
from fractions import Fraction
import json
from pathlib import Path
import sys


BELIEFS = ([6, 3, 1], [5, 3, 2], [4, 3, 3], [3, 4, 3], [2, 4, 4], [1, 1, 8])
BONUS = {"truthful": 0, "utility_zero": 0, "utility_bonus": 200}


def arithmetic(report, rival, belief, bonus):
    votes = [Fraction(p[1] + 2 * p[2], 20) for p in (report, rival) if p is not None]
    b_selected = bool(votes) and sum(votes) / len(votes) >= Fraction(3, 5)

    def score(counts, category):
        if counts is None:
            return 0
        return 200 - sum((count - 10 * (j == category)) ** 2 for j, count in enumerate(counts))

    fixed = (2, 4, 4)
    expected = sum(Fraction(fixed[k] * score(fixed, k) + belief[k] * score(report, k), 10)
                   for k in range(3))
    transfer = bonus if b_selected else 0
    return ("B" if b_selected else "A", expected + transfer,
            score(fixed, 2) + score(report, 0) + transfer)


def check(bundle):
    menu = [None] + [(x, y, 10 - x - y) for x in range(11) for y in range(11 - x)]
    episodes = bundle["summary"]["episodes"]
    expected = [(i, condition, belief) for i, belief in enumerate(BELIEFS) for condition in BONUS]
    observed = [(row["case"], row["condition"], row["belief"]) for row in episodes]
    if observed != expected:
        raise ValueError("Incomplete or unordered frozen episode coverage")
    for row in episodes:
        p, rival, report = row["belief"], row["rival_report"], row["focal_report"]
        bonus = BONUS[row["condition"]]
        allocation, expected, realized = arithmetic(report, rival, p, bonus)
        honest_allocation, honest_expected, honest_realized = arithmetic(p, rival, p, bonus)
        optimum = max(arithmetic(candidate, rival, p, bonus)[1] for candidate in menu)
        observed = (
            row["allocation"], Fraction(*row["expected_utility"]), row["realized_utility"],
            row["allocation_changed_vs_signal"], Fraction(row["expected_gain_vs_signal"]),
            row["realized_gain_vs_signal"], Fraction(*row["optimal_expected_utility"]),
            Fraction(row["regret"]),
        )
        computed = (
            [allocation], expected, realized, allocation != honest_allocation,
            expected - honest_expected, realized - honest_realized, optimum, optimum - expected,
        )
        if observed != computed:
            raise ValueError(f"Numerical discrepancy in case {row['case']} ({row['condition']})")
    return len(episodes)


if __name__ == "__main__":
    cases = check(json.loads(Path(sys.argv[1]).read_text()))
    print(f"Verified {cases} allocations, payoffs, and optima independently.")
