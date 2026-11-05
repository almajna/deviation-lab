from fractions import Fraction as F
from itertools import product
# x = exp(beta/10), so the paper's bounded-rational market shares are rational for integer x.
# Candidate utilities follow the paper's Eqs 3-4 with values [[1/10,0],[-3/5,-7/10]],
# positive margins [[1/10,3/10],[1/20,1/10]] and V0=0.
values=((F(1,10),F(0)),(-F(3,5),-F(7,10)))
margin=((F(1,10),F(3,10)),(F(1,20),F(1,10)))
for x in (3,4,10,100):
 x=F(x); e=((x,F(1)),(x**-6,x**-7))
 def U(s,i):
  d=1+e[0][s[0]]+e[1][s[1]]
  return margin[i][s[i]]*e[i][s[i]]/d
 s=(1,0); p1=U(s,0)-U((0,0),0);p2=U(s,1)-U((1,1),1)
 assert p1>0 and p2>0
 assert 3+x+3*x**-6-x**-5>0 and 2*x-4-x**-6>0
 print('x=',x,'P1 advantage',float(p1),'P2 advantage',float(p2))
print('For x>=3 the inequality witnesses hold strictly. In strict argmax at (high,low),')
print('provider1 ties V0, has U=0 and may deviate to low for U=1/10; hence not NE.')
