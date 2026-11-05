from itertools import product
from math import log
from fractions import Fraction as F

# Arbitrary finite offered values are realizable with nondecreasing quality,
# strictly increasing prices, costs, and positive margins by making the price
# increment sufficiently large; model here uses only market values/margins.
values=(-3,-2,-1,1,2,3)
actions=list(product(values,repeat=2))
checked=transitions=improving=equilibria=0
for n in (2,3):
 for offered in product(actions,repeat=n):
  if any(set(offered[i])&set(offered[j]) for i in range(n) for j in range(i+1,n)): continue
  flat=[0]+[x for pair in offered for x in pair]
  gap=min(abs(x-y) for i,x in enumerate(flat) for j,y in enumerate(flat) if i<j and x!=y)
  margins=[(F(1+i,1), F(3+i,1)) for i in range(n)]
  C=2+(log(n+2)-log(1))/gap
  def state(s):
   vals=[offered[i][s[i]] for i in range(n)]
   ranked=sorted([(0,-1)]+[(v,i) for i,v in enumerate(vals)],reverse=True)
   winner=ranked[0][1]; second=ranked[1][0]
   margin=1 if winner<0 else float(margins[winner][s[winner]])
   phi=log(margin)+C*second
   payoff=[F(0) if winner!=i else margins[i][s[i]] for i in range(n)]
   return phi,payoff
  for s in product(range(2),repeat=n):
   checked+=1
   phi,payoff=state(s)
   equilibrium=True
   for i in range(n):
    t=list(s);t[i]=1-t[i];newphi,newpay=state(t);transitions+=1
    if newpay[i]>payoff[i]:
     equilibrium=False;improving+=1
     assert newphi>phi, (n,offered,s,i,phi,newphi)
   if equilibrium:
    equilibria+=1
    top=sorted(range(n),key=lambda i:max(offered[i]),reverse=True)
    dominant=top[0]; v1=max(offered[dominant]); v2=max(offered[top[1]])
    if v1>0:
     eligible=[j for j in range(2) if offered[dominant][j]>max(0,v2)]
     assert s[dominant]==max(eligible),(n,offered,s,dominant)
print('profiles',checked,'transitions',transitions,'improving',improving,'equilibria',equilibria)
