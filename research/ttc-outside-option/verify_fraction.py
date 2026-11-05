"""Exact checker. See PROTOCOL.md; bounded synthetic examples, not real-world evidence."""
from fractions import Fraction as F
from itertools import combinations, combinations_with_replacement, product
import hashlib
from pathlib import Path

ZERO = F(0)
EXAMPLE = [
    {'q': (F(2), F(21,10)), 'p': (F(1), F(22,10)), 'c': (F(1,2), F(12,10))},
    {'q': (F(1,5), F(1,5)), 'p': (F(1), F(2)), 'c': (F(1,2), F(1))},
]

def value(g, i, action): return g[i]['q'][action]-g[i]['p'][action]
def margin(g, i, action): return g[i]['p'][action]-g[i]['c'][action]
def outcome(g, profile):
    values = [ZERO] + [value(g, i, a) for i, a in enumerate(profile)]
    assert len(set(values)) == len(values)
    winner = max(range(len(values)), key=values.__getitem__)-1
    return winner, tuple(margin(g,i,a) if winner==i else ZERO for i,a in enumerate(profile))
def delta(g):
    values = [[ZERO]] + [[value(g,i,a) for a in (0,1)] for i in range(len(g))]
    return min(abs(x-y) for i in range(len(values)) for j in range(i) for x in values[i] for y in values[j])
def potential(g,profile,C):
    values = [ZERO]+[value(g,i,a) for i,a in enumerate(profile)]
    wi=max(range(len(values)),key=values.__getitem__)
    mu=F(1) if wi==0 else margin(g,wi-1,profile[wi-1])
    return mu+C*sorted(values)[-2]
def deviation(profile,i):
    return tuple(1-x if j==i else x for j,x in enumerate(profile))
def is_ne(g,profile):
    utilities=outcome(g,profile)[1]
    return all(outcome(g,deviation(profile,i))[1][i]<=utilities[i] for i in range(len(g)))
def characterization(g,profile):
    maxima=[max(value(g,i,a) for a in (0,1)) for i in range(len(g))]
    d=max(range(len(g)),key=maxima.__getitem__)
    if maxima[d] < ZERO: return True
    threshold=max([ZERO]+[maxima[i] for i in range(len(g)) if i!=d])
    eligible=[a for a in (0,1) if value(g,d,a)>threshold]
    assert eligible
    if profile[d]!=max(eligible): return False
    realized=max([ZERO]+[value(g,i,profile[i]) for i in range(len(g)) if i!=d])
    return not any(margin(g,d,a)>margin(g,d,profile[d]) and value(g,d,a)>realized for a in (0,1))
def admissible(g):
    for z in g:
        if not (ZERO <= z['q'][0] <= z['q'][1] and ZERO < z['c'][0] < z['c'][1] and z['p'][0]<z['p'][1] and ZERO<z['p'][0]-z['c'][0]<z['p'][1]-z['c'][1]): return False
    values=[[value(g,i,a) for a in (0,1)] for i in range(len(g))]
    return all(x!=ZERO for row in values for x in row) and all(x!=y for i in range(len(g)) for j in range(i) for x in values[i] for y in values[j])

assert admissible(EXAMPLE)
for profile in product((0,1),repeat=2):
    w,u=outcome(EXAMPLE,profile)
    changes=[outcome(EXAMPLE,deviation(profile,i))[1][i]-u[i] for i in range(2)]
    print('counterexample profile',profile,'values',tuple(value(EXAMPLE,i,a) for i,a in enumerate(profile)),'winner',w,'utilities',u,'deviation_delta',tuple(changes),'NE',is_ne(EXAMPLE,profile))
old,new=(1,0),(0,0)
assert outcome(EXAMPLE,new)[1][0]-outcome(EXAMPLE,old)[1][0]==F(1,2)
assert value(EXAMPLE,1,0)==F(-4,5)
assert margin(EXAMPLE,0,old[0])==F(1) and margin(EXAMPLE,0,new[0])==F(1,2)
assert is_ne(EXAMPLE,new)
assert max(a for a in (0,1) if value(EXAMPLE,0,a)>max(value(EXAMPLE,1,k) for k in (0,1)))==1
print('paper_potential_change=ln(1/2)<0, independent of C; paper_theta1=1; actual_NE_theta1=0')

qgrid=tuple(F(x,2) for x in range(5))
mgrid=tuple(F(x,4) for x in range(1,5))
specs=[]
for q, m in product(combinations_with_replacement(qgrid,2),combinations(mgrid,2)):
    c=(F(1,4),F(1,2));p=(c[0]+m[0],c[1]+m[1]);specs.append({'q':q,'p':p,'c':c})
games=profiles=deviations=improving=ne_count=0
for pair in product(specs,repeat=2):
    if not admissible(pair): continue
    games+=1
    margins=[F(1)]+[margin(pair,i,a) for i in range(2) for a in (0,1)]
    C=1+(max(margins)-min(margins))/delta(pair)
    for profile in product((0,1),repeat=2):
        profiles+=1
        actual=is_ne(pair,profile); expected=characterization(pair,profile)
        assert actual==expected,(pair,profile,actual,expected)
        ne_count+=actual
        old_u=outcome(pair,profile)[1]
        for i in range(2):
            deviations+=1; new=deviation(profile,i)
            if outcome(pair,new)[1][i]>old_u[i]:
                improving+=1
                assert potential(pair,new,C)>potential(pair,profile,C),(pair,profile,new,C)
print('complete_family specs',len(specs),'legal_games',games,'profiles',profiles,'NE_profiles',ne_count,'deviations',deviations,'profitable_deviations',improving)
print('corrected_potential_and_equilibrium_characterization PASS')
print('script_sha256',hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
