"""Evidence-set logic on evaluator-side FACTS.

An observation carries facts (evaluator metadata, never in a template). A cause is
SUPPORTED by a set of observations if some `requires` alternative is fully covered by their facts
and no `refuted_by` fact is present. Valid proof sets are the MINIMAL covers (no removable member):
every alternative is found, and padding can never be a proof.
"""
from itertools import combinations


def facts_of(obs_keys, facts):
    out = set()
    for k in obs_keys:
        out |= set(facts.get(k, ()))
    return out


def supported(cause, obs_keys, facts):
    have = facts_of(obs_keys, facts)
    if have & set(cause.get('refuted_by', ())):
        return False
    return any(set(alt) <= have for alt in cause.get('requires', ()))


def minimal_covers(cause, all_keys, facts):
    """All minimal observation sets that support `cause` (antichain)."""
    keys = sorted(all_keys)
    found = []
    for size in range(1, len(keys) + 1):
        for combo in combinations(keys, size):
            s = frozenset(combo)
            if any(m <= s for m in found):
                continue  # superset of a smaller proof => padding
            if supported(cause, s, facts):
                found.append(s)
    return found
