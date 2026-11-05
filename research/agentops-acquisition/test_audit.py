"""Synthetic fixtures only; no source benchmark outcomes are included."""
import unittest
from collections import Counter
from unittest.mock import patch
import audit

class Probe(list):
    def __init__(self, values): super().__init__(values); self.reads=Counter()
    def __getitem__(self, n):
        self.reads[n]+=1
        return super().__getitem__(n)

class Contract(unittest.TestCase):
    def test_equal_budget_no_unsampled_second_observations(self):
        agents=[f'a{i}' for i in range(8)]
        for policy in ('adaptive','uniform'):
            pools={a:Probe([(i/10,i/100),(0.5,i/100)]) for i,a in enumerate(agents)}
            audit.select(pools,agents,0,1,'task',policy)
            self.assertEqual(sum(p.reads[0] for p in pools.values()),8)
            self.assertEqual(sum(p.reads[1] for p in pools.values()),4)
            self.assertTrue(all(p.reads[1]<=1 for p in pools.values()))

    def test_rejected_missing_or_invalid_records(self):
        for bad in ({}, {'agent_id':'a','results':[{'condition':'clean'}]},
                    {'agent_id':'a','results':[{'agent_id':'b','condition':'clean'}]},
                    {'agent_id':'a','results':[{'agent_id':'a','condition':'other'}]},
                    {'agent_id':'a','results':[{'agent_id':'a'}]}):
            with self.assertRaises(ValueError): audit.parse_report(bad,{})

    def test_condition_counts_even_for_excluded_outcomes(self):
        rows={}; counts=Counter()
        audit.parse_report({'agent_id':'a','results':[
            {'agent_id':'a','condition':'noisy'},
            {'agent_id':'a','condition':'adversarial'}]},rows,counts)
        self.assertEqual(counts,{'noisy':1,'adversarial':1})
        self.assertEqual(rows,{})

    def test_heldback_outcomes_do_not_change_policy_selections(self):
        agents=[f'a{i}' for i in range(8)]
        tasks=[f't{i}' for i in range(100)]
        rows={(t,a,r):(0.2+int(a[1:])/10,0.01+int(a[1:])/1000)
              for t in tasks for a in agents for r in range(3)}
        ordered=sorted(tasks,key=lambda t:(audit.digest('AOB-QUERY-V1',t),t))
        changed=rows.copy()
        for t in ordered[50:]:
            for a in agents:
                nums=sorted(range(3),key=lambda r:(audit.digest('AOB-REPEAT-V1',t,a,r),r))
                changed[(t,a,nums[2])]=(0.0, 10.0)
        a=audit.aggregate(rows,tasks,agents,'synthetic')
        b=audit.aggregate(changed,tasks,agents,'synthetic')
        for policy in ('adaptive','uniform'):
            self.assertEqual(a['policies'][policy]['agent_selections'],
                             b['policies'][policy]['agent_selections'])
            self.assertEqual(a['policies'][policy]['total_observed_acquisition_cost_usd'],
                             b['policies'][policy]['total_observed_acquisition_cost_usd'])

if __name__=='__main__': unittest.main()
