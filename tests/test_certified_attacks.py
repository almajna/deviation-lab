"""Check proof soundness against enumeration and malicious producer artifacts."""
from copy import deepcopy
from fractions import Fraction
from unittest.mock import patch
import json
import unittest

from deviation.attacks.environments import environment
from deviation.attacks.game import prepare_game, Game
from deviation.attacks.certified import solve, verify
from deviation.attacks.certified.checker import _actions, _step
from deviation.attacks.certified.model import cell_gain, payoff, upper_bound
from deviation.attacks.search import search
from deviation.data.pipeline import digest
from deviation.markets.contracts import Rejection


def game(profile=None, seed=7, mechanism='lmsr', realization=123):
    s, _, model = environment(profile or {'fee':2}, seed, realization_seed=realization)
    return prepare_game(s, 'strategic', mechanism,
                        **(dict(scope='reports', public_report_model=model) if mechanism in {'pool','calibrated-pool','score'} else {}))


def rehash(c):
    c['sha256'] = digest({k:v for k,v in c.items() if k != 'sha256'})
    return c


def enumerate_values(g):
    from deviation.attacks.certified.model import terminal
    if terminal(g):
        return [payoff(g)['utility']]
    return [v for cmd in _actions(g) for v in enumerate_values(_step(g, cmd))]


class TestSoundBounds(unittest.TestCase):
    def test_known_executable_counterexample_has_exact_net_gain(self):
        g = game()
        c = solve(g)
        checked = verify(g,c)
        self.assertEqual(checked['lower'], [203,3])
        self.assertEqual(checked['gap'], [0,1])
        self.assertEqual(c['incumbent_commands'][0]['share_delta'], [0,0,2])
        from deviation.attacks.search import reference
        honest, _ = reference(g,'signal_following')
        self.assertEqual(Fraction(*checked['lower'])-payoff(honest)['utility'], Fraction(11,3))

    def test_independent_cartesian_enumeration_agrees_with_exact(self):
        for mechanism in ['lmsr','interactive-pool','pool','score','calibrated-pool']:
            for seed in [7,17]:
                g = game(seed=seed,mechanism=mechanism)
                optimum = max(enumerate_values(g))
                c = solve(g,max_expansions=1000)
                self.assertEqual(Fraction(*verify(g,c)['lower']), optimum)
                self.assertEqual(c['lower'],c['upper'])
                self.assertEqual(c['lower'],search(g,max_nodes=5000)['selected']['utility'])

    def test_every_partial_bound_encloses_all_continuations(self):
        for mechanism in ['lmsr','interactive-pool','pool']:
            g = game(seed=17,mechanism=mechanism)
            for state in [g]+[_step(g,a) for a in _actions(g)]:
                actual = max(enumerate_values(state))
                for limit in [0,5000]:
                    self.assertGreaterEqual(upper_bound(state,vector_limit=limit),actual)

    def test_anytime_gap_remains_sound_under_truncation(self):
        g = game(seed=17)
        actual = max(enumerate_values(g))
        last_upper, last_lower = None, None
        for cap in [0,1,2,5,100]:
            c = solve(g,max_expansions=cap)
            verify(g,c)
            lo,hi = Fraction(*c['lower']),Fraction(*c['upper'])
            self.assertLessEqual(lo,actual)
            self.assertGreaterEqual(hi,actual)
            if last_lower is not None:
                self.assertGreaterEqual(lo,last_lower)
                self.assertLessEqual(hi,last_upper)
            last_lower,last_upper=lo,hi

    def test_zero_reward_no_manipulation_control_is_exact(self):
        c=solve(game({'fee':2,'external':0}))
        self.assertEqual(c['gap'],[0,1])
        self.assertEqual(c['lower'],[64,1])

    def test_exhausted_static_report_slots_consume_effort_and_complete(self):
        g=game({'fee':2,'effort':3},mechanism='pool')
        g.engine.cfg['action_limit']=0
        c=solve(g)
        self.assertEqual(c['gap'],[0,1])
        verify(g,c)
        self.assertEqual(Fraction(*c['lower']),max(enumerate_values(g)))

    def test_capital_fee_effort_action_and_position_caps(self):
        for profile in [{'capital':0},{'fee':20},{'fee':2,'effort':4}]:
            g=game(profile)
            c=solve(g)
            self.assertEqual(Fraction(*verify(g,c)['lower']),max(enumerate_values(g)))
        g=game()
        g.engine.cfg['action_limit']=0
        c=solve(g)
        self.assertEqual(c['gap'],[0,1])
        verify(g,c)

    def test_endpoints_include_sales_and_rounded_round_trips(self):
        # Initial long inventory; endpoints include both sales and purchases.
        params=((3,2,4),(1,2,0),(1,1,1),3,3,2,1,2,(5,5,5))
        tight,mode=cell_gain(*params,5000)
        loose,_=cell_gain(*params,0)
        self.assertEqual(mode,'endpoint')
        self.assertLessEqual(tight,loose)
        self.assertGreaterEqual(tight,0)
        # A zero-net round trip cannot bypass ceil charges or positive fees.
        from deviation.markets.numeric import quote
        q=[3,2,4];other=[4,2,4]
        self.assertGreaterEqual(quote(q,other,3)['charge']+quote(other,q,3)['charge'],0)

    def test_ambiguous_relaxed_endpoint_is_bounded_not_excluded(self):
        from deviation.markets.numeric import NumericAmbiguity
        args=((0,0,0),(0,0,0),(1,1,1),3,3,2,0,1,(10,10,10))
        with patch('deviation.attacks.certified.model.quote',side_effect=NumericAmbiguity('test')):
            value,_=cell_gain.__wrapped__(*args,5000)
        self.assertGreaterEqual(value,0)
        self.assertLessEqual(value,2)

    def test_multi_identity_long_suffix_stays_bounded(self):
        g=game({'aliases':3,'rounds':2,'quantity':3,'capital':24},seed=17)
        self.assertEqual(len(g.engine.schedule)-g.engine.turn,9)
        c=solve(g,max_expansions=2,vector_limit=100)
        self.assertEqual(verify(g,c)['claim'],'BOUNDED_FINITE_SUBGAME')
        self.assertGreater(Fraction(*c['gap']),0)
        self.assertEqual(c['search']['expansions'],2)


class TestMaliciousCertificates(unittest.TestCase):
    def setUp(self):
        self.g=game()
        self.c=solve(self.g)

    def reject(self,c):
        with self.assertRaises(Rejection):
            verify(self.g,rehash(c))

    def test_changed_lower_upper_gap_and_claim(self):
        for key,value in [('lower',[999,1]),('upper',[0,1]),('gap',[0,2]),('claim','GLOBAL_OPTIMUM')]:
            c=deepcopy(self.c);c[key]=value;self.reject(c)

    def test_recomputed_hash_does_not_legitimize_forged_leaf(self):
        c=deepcopy(self.c);c['nodes'][1]['upper']=[-10000,1];self.reject(c)

    def test_omitted_duplicate_and_unknown_action_branches(self):
        for mutation in ['drop','duplicate','alter']:
            c=deepcopy(self.c);edges=c['nodes'][0]['children']
            if mutation=='drop':edges.pop()
            elif mutation=='duplicate':edges[0]=deepcopy(edges[1])
            else:edges[0]['command']['order_id']='z0/forgery'
            self.reject(c)

    def test_cycles_shared_children_and_unreachable_nodes(self):
        for i in [0,1]:
            c=deepcopy(self.c);c['nodes'][0]['children'][-1]['node']=i;self.reject(c)
        c=deepcopy(self.c);c['nodes'].append(deepcopy(c['nodes'][-1]));self.reject(c)

    def test_truncated_or_infeasible_incumbent(self):
        c=deepcopy(self.c);c['incumbent_commands']=[];self.reject(c)
        c=deepcopy(self.c);c['incumbent_commands'][0]['share_delta']=[999,0,0];self.reject(c)

    def test_source_and_observation_binding(self):
        for key in ['source_sha256','observation_sha256','action_space','version','objective']:
            c=deepcopy(self.c);c[key]='changed';self.reject(c)
        other=game({'fee':2,'external':7})
        with self.assertRaisesRegex(Rejection,'CERT_OBSERVATION'):
            verify(other,self.c)

    def test_schema_rational_bool_and_limit_rejection(self):
        for value in [[True,1],[1,0],[2,2],[1,-1],1.0]:
            c=deepcopy(self.c);c['upper']=value;self.reject(c)
        c=deepcopy(self.c);c['extra']=1;self.reject(c)
        for limit in [-1,True,100_001]:
            with self.assertRaises(Rejection):solve(self.g,max_expansions=limit)
        c=deepcopy(self.c);c['nodes'][0]['children'][0]['node']=True;self.reject(c)
        with self.assertRaises(Rejection):verify(self.g,self.c,max_nodes=1)

    def test_verifier_runs_when_search_and_optimizer_payoff_are_disabled(self):
        with patch('deviation.attacks.search.choices',side_effect=RuntimeError('search called')), \
             patch('deviation.attacks.search.transition',side_effect=RuntimeError('search called')), \
             patch.object(Game,'expected',side_effect=RuntimeError('optimizer payoff called')), \
             patch('deviation.attacks.certified.solver.solve',side_effect=RuntimeError('solve called')):
            self.assertEqual(verify(self.g,self.c)['gap'],[0,1])

    def test_bound_only_certificate_cannot_claim_exact(self):
        c=solve(self.g,max_expansions=0)
        c['upper']=c['lower'];c['gap']=[0,1];c['claim']='EXACT_FINITE_SUBGAME'
        self.reject(c)


class TestInformationBoundary(unittest.TestCase):
    def test_hidden_labels_costs_and_realization_do_not_affect_certificate(self):
        self.assertEqual(solve(game(realization=10)),solve(game(realization=20)))
        s,_,_=environment({'fee':2},7,realization_seed=10)
        g1=prepare_game(s,'strategic','lmsr')
        for row in s['sealed_outcomes']:row.update(quality=1-row['quality'],cost_decimal='999')
        g2=prepare_game(s,'strategic','lmsr')
        self.assertEqual(solve(g1),solve(g2))

    def test_reject_uncontrolled_future_and_invalid_report_horizon(self):
        g=game();g.engine.schedule.append(['h0',g.engine.schedule[-1][1]])
        with self.assertRaisesRegex(Rejection,'CERT_FUTURE_UNCONTROLLED'):solve(g)
        g=game(mechanism='pool');g.report_slots*=2
        with self.assertRaises(Rejection):solve(g)

    def test_no_mutation_and_canonical_json_roundtrip(self):
        g=game();before=deepcopy(g.observation())
        c=solve(g);verify(g,json.loads(json.dumps(c)))
        self.assertEqual(before,g.observation())
        self.assertEqual(c,solve(g))
