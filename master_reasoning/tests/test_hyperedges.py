import unittest
from master_reasoning.hyperedges import attach_hyperedges

class ConjunctiveRulesTests(unittest.TestCase):
    def setUp(self):
        self.rule={'id':'H_TEST','inputs':['a','b','c'],'title':'An emergent outcome',
            'mechanism':'The three inputs are mutually necessary.',
            'emergence':'The joint arrangement changes the system.',
            'counter':'Substitution prevents the outcome.',
            'test':'Measure all three necessary conditions.',
            'status':'conjectural'}
    def item(self,present,tag):
        proofs=[dict(object=i,source_family='publisher '+i) for i in present]
        return dict(category='trends',proof=proofs[:2],
            frontier=dict(focus='b',proof=proofs,nodes=present,edges=[],title=tag))
    def test_genuine_and_gate_needs_all_verified_anchor_nodes(self):
        yes=self.item(['a','b','c'],'yes'); no=self.item(['a','b'],'no')
        d={'trends':[yes,no]};stats=attach_hyperedges(d,[self.rule])
        self.assertEqual(stats['trends'],1)
        self.assertEqual(yes['frontier']['conjunction']['id'],'H_TEST')
        self.assertNotIn('conjunction',no['frontier'])
    def test_repeated_rule_cannot_fill_whole_chapter(self):
        arr=[self.item(['a','b','c'],str(i)) for i in range(5)]
        d={'trends':arr};stats=attach_hyperedges(d,[self.rule])
        self.assertEqual(stats['trends'],1)
        self.assertEqual(sum('conjunction' in x['frontier'] for x in arr),1)

if __name__=='__main__':unittest.main()
