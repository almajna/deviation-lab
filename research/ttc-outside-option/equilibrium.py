"""Exact perfect-rational equilibrium and PoA; see EQUILIBRIUM.md."""
from fractions import Fraction
from oracle import maximize


def analyze(values,margins,outside):
    """Return optimum and one equilibrium, and PoA when equilibrium welfare > 0.

    Providers choose independently from ordered finite actions. Values must be
    rational and have no cross-provider/outside ties. Margins must be positive,
    strictly increasing rationals. This does not implement finite-beta logit.
    """
    optimum,optimal_profile,optimal_winner=maximize(values,margins,outside)
    for row in margins:
        if any(m<=0 for m in row) or any(row[i]>=row[i+1] for i in range(len(row)-1)):
            raise ValueError('each provider needs positive strictly increasing margins')
    n=len(values)
    best_action=[max(range(len(row)),key=row.__getitem__) for row in values]
    max_value=[values[i][a] for i,a in enumerate(best_action)]
    d=max(range(n),key=max_value.__getitem__)
    if max_value[d]<outside:
        equilibrium_profile=tuple(0 for _ in values)
        equilibrium_winner=None
        equilibrium_welfare=outside
    else:
        threshold=outside
        for j in range(n):
            if j!=d and max_value[j]>threshold:threshold=max_value[j]
        safe=max(a for a,v in enumerate(values[d]) if v>threshold)
        equilibrium_profile=best_action.copy();equilibrium_profile[d]=safe
        equilibrium_profile=tuple(equilibrium_profile)
        equilibrium_winner=d
        equilibrium_welfare=values[d][safe]+margins[d][safe]
    if optimum<equilibrium_welfare:
        raise AssertionError('social optimum must dominate the equilibrium')
    poa=Fraction(optimum)/Fraction(equilibrium_welfare) if equilibrium_welfare>0 else None
    return {'optimum':optimum,'optimum_profile':optimal_profile,
            'optimum_winner':optimal_winner,'equilibrium_welfare':equilibrium_welfare,
            'equilibrium_profile':equilibrium_profile,'equilibrium_winner':equilibrium_winner,
            'price_of_anarchy':poa}
