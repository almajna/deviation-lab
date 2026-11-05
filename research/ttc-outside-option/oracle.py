"""Exact welfare maximization with perfectly rational users and independent actions.

All inputs are finite rational values and margins. Cross-provider values and
the outside value must not tie. Unlike the published model, negative margins
are accepted; an outside option is considered only if it is attainable.
"""
from numbers import Rational


def maximize(values, margins, outside):
    """Return (max welfare, tuple of actions, winner index or None).

    Each provider supplies a nonempty list of values and associated margins.
    The allocation scan is linear in total actions under unit-cost comparisons.
    Tie validation uses a hash table and is expected linear time and space;
    rational arithmetic has additional bit costs. Not a finite-beta solver.
    """
    if not isinstance(outside,Rational) or not values or len(values)!=len(margins):
        raise ValueError('need an outside value and at least one provider')
    n=len(values); mins=[]; argmins=[]; owner={}
    for i,(vs,ms) in enumerate(zip(values,margins)):
        if not vs or len(vs)!=len(ms):
            raise ValueError('empty or misaligned actions')
        for v,m in zip(vs,ms):
            if not isinstance(v,Rational) or not isinstance(m,Rational):
                raise ValueError('values and margins must be rational')
            if v==outside or (v in owner and owner[v]!=i):
                raise ValueError('outside or cross-provider value tie')
            owner[v]=i
        a=min(range(len(vs)),key=vs.__getitem__)
        mins.append(vs[a]);argmins.append(a)
    first=second=None
    for i,x in enumerate(mins):
        if first is None or x>mins[first]:
            first,second=i,first
        elif second is None or x>mins[second]:
            second=i
    outside_feasible=mins[first]<outside
    best=outside if outside_feasible else None
    best_winner=None
    best_action=None
    for i,(vs,ms) in enumerate(zip(values,margins)):
        rival=second if i==first else first
        threshold=outside if rival is None else max(outside,mins[rival])
        for action,(value,margin) in enumerate(zip(vs,ms)):
            if value>threshold:
                welfare=value+margin
                if best is None or welfare>best:
                    best=welfare;best_winner=i;best_action=action
    if best is None:
        raise AssertionError('a finite tie-free profile must have an outcome')
    profile=argmins.copy()
    if best_winner is not None:
        profile[best_winner]=best_action
    return best,tuple(profile),best_winner
