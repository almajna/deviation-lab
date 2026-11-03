"""Frozen contingent policy templates; never receive a world/outcome object."""
from fractions import Fraction
from deviation.markets.numeric import project_rational
from deviation.markets.policies import SignalFollowing, base_action, candidates
from deviation.simulator.policies import optimize


class Template:
    def __init__(self, bias=0, trade_weight=0, *, noop=False, report_timing="immediate"):
        self.bias,self.weight,self.noop=bias,trade_weight,noop
        self.timing=report_timing

    def act(self,p):
        D=p['limits']['report_denominator']
        signal=p['own_signal']
        weights=p['own_utility_view'].get(p['markets'][p['market_id']]['task_id'],{})
        favorite=next(iter(sorted(weights)),None)
        if self.bias and favorite is not None and not (self.timing=='delayed' and p['stage']=='REPORT_COMMIT'):
            target=2 if p['markets'][p['market_id']]['model_id']==favorite else 0
            signal=project_rational([(D-self.bias)*n+self.bias*D*int(k==target) for k,n in enumerate(signal)],D)
        if p['stage']=='REPORT_COMMIT':
            a=base_action(p,'report_distribution')
            a.update(counts=list(signal),denominator=D,report_token=p['report_token']);return a
        if self.noop:return base_action(p,'no_op')
        if p['mechanism']!='lmsr':
            if p['mechanism']=='interactive-pool' and p['own_last_report']!=signal and p['own_cash']>=p['limits']['fee']:
                a=base_action(p,'update_distribution');a.update(counts=list(signal),denominator=D);return a
            return base_action(p,'no_op')
        P=p['limits']['price_denominator'];mid=p['market_id']
        def external(override=None):
            values={t['task_id']:{} for t in p['public_tasks']}
            for m,b in p['markets'].items():
                dist=override if m==mid and override is not None else b['price_counts']
                values[b['task_id']][b['model_id']]=Fraction(dist[1]+2*dist[2],2*P)
            allocation=optimize(p['public_tasks'],p['reservations'],p['reservation_budget'],values)
            return sum(p['own_utility_view'].get(c['task_id'],{}).get(c['model_id'],0) for c in allocation)
        before=external() if self.weight else 0
        best=None;best_key=(Fraction(0),0,(0,0,0))
        for c in candidates(p):
            d=c['share_delta']
            cash=sum(Fraction(n,D)*x for n,x in zip(p['own_signal'],d))-c['charge']-c['fee']
            value=cash+(self.weight*(external(c['price_counts_after'])-before) if self.weight else 0)
            key=(value,-sum(abs(x) for x in d),tuple(-x for x in d))
            if key>best_key:best,best_key=c,key
        if best is None:return base_action(p,'no_op')
        a=base_action(p,'trade_shares');a.update(share_delta=best['share_delta'],max_net_debit=best['max_net_debit']);return a


def policy(spec):
    if spec['kind']=='honest':return SignalFollowing()
    if spec['kind']=='no-action':return Template(noop=True)
    return Template(spec['bias'],spec['trade_weight'],report_timing=spec.get('report_timing','immediate'))
