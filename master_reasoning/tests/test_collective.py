"""Tests for interaction gates and combinations; no fake measured dynamics."""
import unittest
from master_reasoning.collective import interpret, _cycle, _verified_proof, enrich_collective


def p(obj,n,kind='action',at='2026-02-01',verification='workbook_verified'):
    return dict(object=obj,source_family='publisher '+str(n),date=at,kind=kind,
        direction='expands',verification=verification,evidential_weight=.91,
        scope={'level':'eu','countries':[]})

def edge(i,a,b,rel='enables'):
    return dict(id=str(i),**{'from':a,'to':b},relation=rel)

def item(edges,proof,focus='research.interface',conjunction=None,metrics=None):
    f=dict(nodes=sorted({v for e in edges for v in (e['from'],e['to'])}),
        edges=edges,proof=proof,focus=focus,metrics=metrics or {})
    if conjunction:f['conjunction']={'id':'H01'}
    return dict(category='trends',frontier=f)

class CollectiveMechanisms(unittest.TestCase):
    def setUp(self):
        self.links=[edge(1,'science.funding','research.interface'),
                    edge(2,'talent.mobility','research.interface'),
                    edge(3,'research.interface','innovation.implementation'),
                    edge(4,'research.interface','industry.adoption'),
                    edge(5,'security.controls','research.interface','constrains')]
        self.proof=[p('science.funding',1),p('talent.mobility',2),
                    p('research.interface',3,'diagnosis'),p('innovation.implementation',4,'diagnosis'),
                    p('industry.adoption',5,'diagnosis'),p('security.controls',6)]

    def test_compound_adaptation_and_transition_from_verified_anchored_graph(self):
        z=item(self.links,self.proof,conjunction=True,
            metrics={'cut_effects':['innovation.implementation'],'longest_path':2})
        out=interpret(z)
        self.assertIsNotNone(out)
        self.assertEqual(len(out['pattern_ids']),2)
        self.assertIn('conjunctive_threshold',out['pattern_ids'])
        self.assertIn('adaptive_rerouting',out['pattern_ids'])
        self.assertIn('regime',out['narrative'])
        self.assertFalse(out['observed_cycles'])
        self.assertTrue(out['supports_no_measured_threshold'])

    def test_unverified_cannot_support_collective_inference(self):
        proofs=list(self.proof)
        proofs[1]={**proofs[1],'verification':'review','evidential_weight':0}
        self.assertIsNone(interpret(item(self.links,proofs,conjunction=True)))
        self.assertFalse(_verified_proof(proofs))

    def test_duplicate_source_family_rejected(self):
        proofs=list(self.proof)
        proofs[1]={**proofs[1],'source_family':proofs[0]['source_family']}
        self.assertIsNone(interpret(item(self.links,proofs)))

    def test_different_scopes_rejected(self):
        proofs=list(self.proof)
        proofs[1]={**proofs[1],'scope':{'level':'external','countries':[]}}
        self.assertIsNone(interpret(item(self.links,proofs)))

    def test_unspecified_external_scope_cannot_be_laundered(self):
        proofs=[{**p,'scope':{'level':'external','countries':[]}} for p in self.proof]
        self.assertIsNone(interpret(item(self.links,proofs)))

    def test_no_cycle_fabricated_by_a_convergent_configuration(self):
        self.assertFalse(_cycle(self.links))
        self.assertTrue(_cycle(self.links+[edge(6,'innovation.implementation','research.interface')]))

    def test_same_evidence_does_not_automatically_prove_synchronization(self):
        z=item(self.links,self.proof,metrics={'longest_path':2})
        out=interpret(z)
        self.assertIsNotNone(out)
        self.assertNotIn('synchronization',out['concepts_in_play'])
        self.assertIn('conditional',out['model_status'])

    def test_model_can_return_no_lens_instead_of_padding(self):
        l=[edge(1,'science.funding','research.interface')]
        z=item(l,[p('science.funding',1),p('research.interface',2,'diagnosis')])
        self.assertIsNone(interpret(z))

    def test_all_eight_scenarios_get_conditional_dynamics(self):
        items=[dict(axis_states={'ARCH':a,'OPEN':b,'SCALE':c})
            for a in ('high','low') for b in ('high','low') for c in ('high','low')]
        r={'scenarios':items}
        stats=enrich_collective(r)
        self.assertEqual(stats['counts']['scenarios'],8)
        self.assertEqual(len({x['collective_dynamics']['narrative'] for x in items}),8)
        self.assertTrue(all('conditional' in x['collective_dynamics']['model_status'] for x in items))

if __name__=='__main__':unittest.main()
