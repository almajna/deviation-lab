from fractions import Fraction as F
from itertools import product

# All values in the same monetary/quality units. No provider/provider or outside ties.
V0 = F(0)
game = (
    {'q': (F(2), F(41,10)), 'p': (F(1), F(21,5)), 'c': (F(1,2), F(6,5))},
    {'q': (F(5,2), F(27,10)), 'p': (F(23,10), F(43,10)), 'c': (F(13,10), F(7,5))},
)
for x in game:
    assert 0 < x['q'][0] <= x['q'][1]
    assert 0 < x['c'][0] < x['c'][1]
    assert x['p'][0] < x['p'][1]
    assert 0 < x['p'][0]-x['c'][0] < x['p'][1]-x['c'][1]
values = [[g['q'][a]-g['p'][a] for a in range(2)] for g in game]
margins = [[g['p'][a]-g['c'][a] for a in range(2)] for g in game]
ws = [[g['q'][a]-g['c'][a] for a in range(2)] for g in game]
assert all(v != V0 for row in values for v in row)
assert all(a != b for a in values[0] for b in values[1])
def play(s):
    offers=[V0]+[values[i][a] for i,a in enumerate(s)]
    winner=max(range(3),key=offers.__getitem__)-1
    utility=tuple(margins[i][a] if i==winner else F(0) for i,a in enumerate(s))
    welfare=V0 if winner==-1 else ws[winner][s[winner]]
    return winner,utility,welfare
profiles=list(product(range(2),repeat=2)); equilibrium=[]
for s in profiles:
    w,u,sw=play(s)
    deviations=[]
    for i in range(2):
        t=list(s);t[i]=1-t[i]
        deviations.append(play(t)[1][i]-u[i])
    ne=all(d<=0 for d in deviations)
    if ne:equilibrium.append(s)
    print('profile',s,'winner',w,'utility',u,'welfare',sw,'delta',tuple(deviations),'NE',ne)
tstar=tuple(max(range(2),key=lambda a: ws[i][a]) for i in range(2))
assert tstar==(1,1) and play(tstar)[0]==-1
s=equilibrium[0]
poa=max(play(p)[2] for p in profiles)/play(s)[2]
lead_star=max(range(2),key=lambda i:values[i][tstar[i]])
lead_eq=max(range(2),key=lambda i:values[i][s[i]])
Wstar=ws[lead_star][tstar[lead_star]]
Weq=ws[lead_eq][s[lead_eq]]
proof_bound=Wstar/Weq
stated_first_order=F(1)+(Wstar-Weq)/Wstar
assert poa==1 and Wstar==F(29,10) and Weq==F(3,2)
assert proof_bound==F(29,15) and stated_first_order==F(43,29)
print('values',values,'margins',margins,'provider_welfare',ws)
print('tstar',tstar,'equilibrium',s,'actual_poa',poa,'Eq55_beta_inf',proof_bound,'Theorem4_first_order',stated_first_order)
print('Contradicts the displayed exact Eq55 beta-infinity bound; higher-order qualification applies to leading-order theorem display.')
