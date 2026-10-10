import tempfile,unittest
from pathlib import Path
from trajectory_engine.journeys import discover,_stage
from trajectory_engine.presentation import write_page

class JourneyTests(unittest.TestCase):
    @staticmethod
    def e(i,title,date,typ='unclassified',subject=''):
        return {'evidence_id':str(i),'title':title,'claim_text':title,'publication_date':date,
                'event_date':None,'source_url':'https://example.org/'+str(i),
                'origin_sheet':'Historical findings' if date and date<'2026' else 'All publication data',
                'source_family':'example.org','source_quality':'not_verified_in_database',
                'evidence_type':typ,'classification_basis':'lexical_hint_not_verified','subject':subject}
    def test_does_not_treat_proposal_as_observed_outcome(self):
        p=self.e(1,'Commission proposes quantum programme','2023-01-01','proposed_action')
        self.assertEqual(_stage(p),'expectation')
    def test_no_history_is_not_claimed_success(self):
        records=[self.e(i,'Quantum computing machine planned '+str(i),'2026-01-'+str(i).zfill(2),'proposed_action') for i in range(1,10)]
        records +=[self.e(i,'Bio innovation funding programme '+str(i),'2026-02-'+str(i-9).zfill(2)) for i in range(10,19)]
        j=discover(records,n_topics=2,min_members=3)
        self.assertTrue(j)
        self.assertTrue(all('Earlier benchmark not found' in t['verdict'] for t in j))
        self.assertTrue(all('failure' not in t['reason'] for t in j))
    def test_prior_source_and_later_proposal_do_not_prove_outcome(self):
        a=[self.e(i,'Chip sovereignty and semiconductor strategy '+str(i),'2023-06-'+str(i).zfill(2),'proposed_action') for i in range(1,8)]
        a +=[self.e(i,'Chip sovereignty and semiconductor strategy revised '+str(i),'2026-06-'+str(i-7).zfill(2),'proposed_action') for i in range(8,15)]
        a +=[self.e(i,'Climate adaptation programme '+str(i),'2026-09-'+str(i-14).zfill(2)) for i in range(15,22)]
        j=discover(a,n_topics=2,min_members=4)
        self.assertTrue(any(x['count_older']>0 for x in j))
        self.assertFalse(any('achieved' in x['verdict'].lower() for x in j))
    def test_source_links_and_prompt_are_present(self):
        items=[self.e(i,'Quantum computers research '+str(i),'2022-01-'+str(i).zfill(2),'prediction') for i in range(1,8)]
        items +=[self.e(i,'Quantum hardware testing '+str(i),'2026-04-'+str(i-7).zfill(2),'observation') for i in range(8,15)]
        items +=[self.e(i,'Green energy wind power '+str(i),'2026-05-'+str(i-14).zfill(2)) for i in range(15,22)]
        j=discover(items,n_topics=2,min_members=4)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'index.html';write_page(p,j,items)
            page=p.read_text()
            self.assertIn('What was expected',page)
            self.assertIn('What happened',page)
            self.assertIn('Original source',page)
            self.assertIn('COPY',page.upper())

if __name__=='__main__':unittest.main()
