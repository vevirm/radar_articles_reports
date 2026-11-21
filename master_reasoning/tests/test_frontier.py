import unittest
from master_reasoning.frontier import reconstruct, enrich_frontiers
from master_reasoning.graphics import frontier_map
from master_reasoning.infer import _index
from test_master import evidence,claim,bridge

class FrontierRecombinationTests(unittest.TestCase):
    def test_cross_sector_chain_and_negative_branch_are_reconstructed(self):
        x=evidence(1,claim('a.alpha','action','builds','expands','2026-01-01'))
        y=evidence(2,claim('b.beta','diagnosis','assesses','becomes_conditional','2026-02-01'))
        z=evidence(3,claim('c.gamma','diagnosis','measures','becomes_contested','2026-03-01'))
        q=evidence(4,claim('d.delta','action','restricts','becomes_contested','2026-01-15'))
        edges=[bridge('t1','a.alpha','b.beta'),bridge('t2','b.beta','c.gamma'),
               {**bridge('t3','d.delta','b.beta'), 'relation':'constrains'}]
        obj={'id':'I1','category':'disruptions','subject':'b.beta',
             'proof':[{'object':'a.alpha','date':'2026-01-01','source_family':x.source_family,'scope':x.claims[0]['scope']},
                      {'object':'b.beta','date':'2026-02-01','source_family':y.source_family,'scope':y.claims[0]['scope']}]}
        reconstruction=reconstruct(obj,_index([x,y,z,q]),edges,14)
        self.assertIsNotNone(reconstruction)
        self.assertIn('d.delta',reconstruction['nodes'])
        self.assertIn('c.gamma',reconstruction['nodes'])
        self.assertEqual(reconstruction['metrics']['n_domains'],4)
        self.assertEqual(reconstruction['metrics']['tensions'],1)
        self.assertIn('constraint',reconstruction['pattern'])
        self.assertGreater(frontier_map({**obj,'frontier':reconstruction}).getbuffer().nbytes,3000)

    def test_unverified_observation_never_adds_fake_network_node(self):
        a=evidence(1,claim('a.alpha','action','builds','expands','2026-01-01'))
        b=evidence(2,claim('b.beta','diagnosis','assesses','becomes_conditional','2026-02-01'))
        bad=evidence(3,claim('c.gamma','diagnosis','assesses','becomes_contested','2026-02-05'),kind='review')
        item={'subject':'b.beta','proof':[{'object':'a.alpha','date':'2026-01-01','source_family':a.source_family,'scope':a.claims[0]['scope']},
                      {'object':'b.beta','date':'2026-02-01','source_family':b.source_family,'scope':b.claims[0]['scope']}]}
        result=reconstruct(item,_index([a,b,bad]),[bridge('e1','a.alpha','b.beta'),bridge('e2','b.beta','c.gamma')])
        self.assertNotIn('c.gamma',result['nodes'])

    def test_no_arbitrary_four_claim_threshold(self):
        a=evidence(1,claim('a.alpha','action','funds','expands','2026-01-01'))
        b=evidence(2,claim('b.beta','diagnosis','assesses','becomes_conditional','2026-02-01'))
        item={'subject':'b.beta','proof':[{'object':'a.alpha','date':'2026-01-01','source_family':a.source_family,'scope':a.claims[0]['scope']},
                      {'object':'b.beta','date':'2026-02-01','source_family':b.source_family,'scope':b.claims[0]['scope']}]}
        result=reconstruct(item,_index([a,b]),[bridge('e1','a.alpha','b.beta')],14)
        self.assertEqual(result['metrics']['breadth'],2)
        self.assertEqual(len(result['proof']),2)
        self.assertNotIn('measured causal effect',result['epistemic_status'])

if __name__=='__main__':unittest.main()
