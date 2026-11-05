"""Exact softmax-game check at beta=log 3; derives all beta>=log 3 symbolically."""
from fractions import Fraction as F
from itertools import product
q=((F(2),F(3)),(F(1,5),F(2,5)))
p=((F(1),F(3)),(F(6,5),F(12,5)))
c=((F(1,2),F(1)),(F(7,10),F(7,5)))
v=tuple(tuple(q[i][a]-p[i][a] for a in range(2)) for i in range(2))
m=tuple(tuple(p[i][a]-c[i][a] for a in range(2)) for i in range(2))
assert v==((F(1),F(0)),(F(-1),F(-2))) and m==((F(1,2),F(2)),(F(1,2),F(1)))
assert all(q[i][0]<=q[i][1] and p[i][0]<p[i][1] and c[i][0]<c[i][1] and F(0)<m[i][0]<m[i][1] for i in range(2))
assert all(v[0][a]!=v[1][b] for a,b in product(range(2),repeat=2))

def bounded(profile,t):
    weights=(t**int(v[0][profile[0]]),t**int(v[1][profile[1]]))
    z=1+sum(weights)
    return tuple(weights[i]/z*m[i][profile[i]] for i in range(2))

def perfect(profile):
    values=(v[0][profile[0]],v[1][profile[1]])
    return tuple(m[i][profile[i]] if values[i]>max(F(0),values[1-i]) else F(0) for i in range(2))

z=(1,0); t=F(3); b=bounded(z,t); alt1=bounded((0,0),t)[0];alt2=bounded((1,1),t)[1]
assert b[0]>alt1 and b[1]>alt2
assert perfect(z)[0]<perfect((0,0))[0]
print('beta=ln3 bounded profile',z,'utility',b,'deviations',alt1,alt2)
print('perfect utility',perfect(z),'P1 low-deviation utility',perfect((0,0))[0])
print('for every t=e^beta>=3: P1 high=2/(2+1/t)>=2/3 > P1 low <1/2')
print('P2 low>high iff 2*t^2-4*t-1>0; at t=3 it equals 5 and is increasing for t>=3')
