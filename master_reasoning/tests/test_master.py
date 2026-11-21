"""Self-contained safeguards for the isolated master inference workflow."""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from master_reasoning.adapter import Evidence
from master_reasoning.core import _verified, _weight, _same_scope, generate_scenarios
from master_reasoning.infer import _compatible, _index, congestion_disruptions, topological_trends
from master_reasoning.main import find_input


def claim(subject, kind, mech, direction, at, status='operating', level='eu'):
    return dict(object=subject, kind=kind, mechanism=mech, direction=direction,
        status=status, status_date=at, scope={'level':level,'countries':[]},
        text='A documented intervention or assessment of '+subject, merit=100,
        confidence='high', provisional=False, claim_id='test:'+subject+':'+at)


def evidence(num, claim_, kind='deep_scan_authoritative_keep', publisher=None):
    name=publisher or 'publisher '+str(num)
    return Evidence(id=str(num),source_type='live',title='Evidence '+str(num),
      publisher=name,url='https://example.com/'+str(num),date=claim_['status_date'],
      source_family=name,quality_class=kind,admission='keep',aboutness='eu',
      geography='eu',confidence='high',qualification='',source_key='work:'+str(num),
      claims=(claim_,))


def bridge(num, source,target):
    return dict(id=num,**{'from':source,'to':target},relation='enables',
      condition='Deployment reaches the same affected population',
      risk_if_absent='Infrastructure is underused',indicator='Independently measured downstream use')


class EvidenceGateTests(unittest.TestCase):
    def test_unverified_cannot_aggregate_into_support(self):
        v=evidence(1,claim('a','action','funds','expands','2026-02-12'))
        weak=[evidence(i,claim('a','action','funds','expands','2026-02-12'),
                 'review') for i in range(2,1002)]
        self.assertGreater(_weight(v,v.claims[0]),0)
        self.assertTrue(all(_weight(e,e.claims[0])==0 for e in weak))
        self.assertTrue(all(not _verified(e,e.claims[0]) for e in weak))

    def test_three_distinct_works_and_families_required(self):
        x=evidence(1,claim('a','action','funds','expands','2026-01-01'))
        y=evidence(2,claim('b','action','builds','expands','2026-02-01'))
        z=evidence(3,claim('c','diagnosis','assesses','contracts','2026-03-01'))
        self.assertTrue(_compatible([(x,x.claims[0]),(y,y.claims[0]),(z,z.claims[0])]))
        duplicate=evidence(4,z.claims[0],publisher=x.publisher)
        self.assertFalse(_compatible([(x,x.claims[0]),(y,y.claims[0]),(duplicate,duplicate.claims[0])]))
        far=evidence(4,claim('c','diagnosis','assesses','contracts','2015-03-01'))
        self.assertFalse(_compatible([(x,x.claims[0]),(y,y.claims[0]),(far,far.claims[0])]))

    def test_incompatible_geography_rejected(self):
        eu=claim('a','diagnosis','assesses','contracts','2026-01-01')
        ext=claim('b','diagnosis','assesses','contracts','2026-01-01',level='external')
        self.assertFalse(_same_scope(eu,ext))

    def test_verified_topological_three_anchor_motif(self):
        es=[evidence(1,claim('a','action','funds','expands','2026-01-01')),
            evidence(2,claim('b','action','builds','expands','2026-02-01')),
            evidence(3,claim('z','diagnosis','assesses','contracts','2026-03-01'))]
        ix=_index(es); edges=[bridge('b1','a','z'),bridge('b2','b','z')]
        self.assertEqual(len(topological_trends(ix,edges)),1)
        shocks=congestion_disruptions(ix,edges)
        self.assertEqual(len(shocks),1)
        self.assertEqual(len(shocks[0]['proof']),3)
        es[1]=evidence(2,es[1].claims[0],kind='review')
        self.assertEqual(len(congestion_disruptions(_index(es),edges)),0)

    def test_no_congestion_without_adverse_diagnosis(self):
        es=[evidence(1,claim('a','action','funds','expands','2026-01-01')),
            evidence(2,claim('b','action','builds','expands','2026-02-01')),
            evidence(3,claim('z','diagnosis','assesses','expands','2026-03-01'))]
        self.assertEqual(congestion_disruptions(_index(es),[bridge('1','a','z'),bridge('2','b','z')]),[])

    def test_all_eight_scenarios_unique_and_unprobabilistic(self):
        axes=[dict(id=x, name=x,high='open',low='closed',object_tags=[x],
                   high_implication='high',low_implication='low',high_test='up',low_test='down')
              for x in ('ARCH','OPEN','SCALE')]
        worlds=generate_scenarios([],axes,'test')
        self.assertEqual(len(worlds),8)
        self.assertEqual(len({w['id'] for w in worlds}),8)
        self.assertTrue(all(w['relative_likelihood'] is None for w in worlds))
        self.assertTrue(all(w['verified_proxy_diagnostic']['state']=='coverage_gap' for w in worlds))

    def test_input_autodiscovery_prefers_canonical_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sub=root/'stuff';sub.mkdir()
            good=sub/'source_merit_ranking.xlsx';good.write_bytes(b'test')
            self.assertEqual(find_input(root,'stuff/source_merit_ranking.xlsx'),good)
            good.unlink()
            with self.assertRaises(FileNotFoundError):
                find_input(root,'stuff/source_merit_ranking.xlsx')


if __name__=='__main__':unittest.main()

class XLSXInputFormatTests(unittest.TestCase):
    def test_shared_string_and_nonstandard_worksheet_path(self):
        from zipfile import ZipFile
        from master_reasoning._xlsx_rows import as_dicts
        namespace='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        with tempfile.TemporaryDirectory() as temp:
            filename=Path(temp)/'format.xlsx'
            with ZipFile(filename,'w') as z:
                z.writestr('xl/workbook.xml',f'<workbook xmlns="{namespace}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="7" r:id="rId99"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId99" Type="test" Target="worksheets/sheet7.xml"/></Relationships>')
                z.writestr('xl/sharedStrings.xml',f'<sst xmlns="{namespace}"><si><t>claim</t></si><si><t>Verified</t></si></sst>')
                z.writestr('xl/worksheets/sheet7.xml',f'<worksheet xmlns="{namespace}"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row><row r="2"><c r="A2" t="s"><v>1</v></c></row></sheetData></worksheet>')
            self.assertEqual(list(as_dicts(str(filename),1)),[{'claim':'Verified'}])

class OutcomePresentationTests(unittest.TestCase):
    def test_report_keeps_rulebook_separate(self):
        from master_reasoning.report import write_report
        from docx import Document
        sample=dict(title='Converging change: a + b -> z',
            inference='A new interaction reshapes z.',
            second_order='A second-order consequence is visible.',
            decision='Monitor actual use.',
            conditions=['Adoption reaches institutions','Interoperability is achieved'],
            rule='T2_CONVERGENT_CAUSAL_TOPOLOGY',priority=74,
            source_families=3,counter_explanation='Rival mechanism.',
            disconfirmation_test='A specified test.',
            caveat='Verified does not imply causal effect.',proof=[])
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'report.docx'
            sections={key:[sample] for key in ('trends','disruptions','risks','opportunities')}
            sections['scenarios']=[]
            write_report(dest,sections,{},[],[{'display':'merit.xlsx'},{'display':'relevance.xlsx'}])
            rendered='\n'.join(p.text for p in Document(dest).paragraphs)
            self.assertIn('A new interaction reshapes z.',rendered)
            self.assertIn('Strategic implication',rendered)
            self.assertNotIn('EVIDENCE-GATED REVIEW PRIORITY',rendered)
            self.assertNotIn('T2_CONVERGENT_CAUSAL_TOPOLOGY',rendered)
            self.assertNotIn('Rival mechanism.',rendered)
            self.assertNotIn('A specified test.',rendered)

class CounterforceLogicTests(unittest.TestCase):
    """Counter-trend observations and modeled gates must not be conflated."""
    def test_requires_two_independent_verified_opposing_diagnoses(self):
        from master_reasoning.counterforces import attach_counterforces
        from master_reasoning.infer import _index,topological_trends
        a=evidence(11,claim('a','action','funds','expands','2026-01-01'))
        b=evidence(12,claim('b','action','builds','expands','2026-01-15'))
        z=evidence(13,claim('z','diagnosis','measures','expands','2026-02-01'))
        o1=evidence(14,claim('z','diagnosis','evaluates','contracts','2026-02-12'))
        o2=evidence(15,claim('z','diagnosis','assesses','contracts','2026-02-15'))
        edges=[bridge('b1','a','z'),bridge('b2','b','z')]
        base=topological_trends(_index([a,b,z,o1,o2]),edges)[0]
        with_both=attach_counterforces([base],[a,b,z,o1,o2],edges)
        assert with_both[0]['counterforces'][0]['kind']=='counter_direction'
        self.assertEqual(len(with_both[0]['counterforces'][0]['proof']),2)
        single=topological_trends(_index([a,b,z,o1]),edges)[0]
        attach_counterforces([single],[a,b,z,o1],edges)
        self.assertNotIn('counter_direction',[c['kind'] for c in single['counterforces']])
        lead=evidence(15,claim('z','diagnosis','assesses','contracts','2026-02-15'),kind='review')
        unverified=topological_trends(_index([a,b,z,o1,lead]),edges)[0]
        attach_counterforces([unverified],[a,b,z,o1,lead],edges)
        self.assertNotIn('counter_direction',[c['kind'] for c in unverified['counterforces']])

    def test_mismatched_region_cannot_support_counter_trend(self):
        from master_reasoning.counterforces import attach_counterforces
        from master_reasoning.infer import _index,topological_trends
        a=evidence(1,claim('a','action','builds','expands','2026-01-01'))
        b=evidence(2,claim('b','action','funds','expands','2026-02-01'))
        z=evidence(3,claim('z','diagnosis','assesses','expands','2026-03-01'))
        opp=evidence(4,claim('z','diagnosis','measures','contracts','2026-04-01',level='external'))
        edges=[bridge('e1','a','z'),bridge('e2','b','z')]
        t=topological_trends(_index([a,b,z,opp]),edges)
        attach_counterforces(t,[a,b,z,opp],edges)
        self.assertNotIn('counter_direction',[cf['kind'] for cf in t[0]['counterforces']])

    def test_report_contains_graphics_and_readable_counterforce(self):
        from master_reasoning.report import write_report
        from docx import Document
        from zipfile import ZipFile
        sample=dict(title='Converging change: a + b -> z',subject='z',
            network_path=['a','z','b'],inference='A and B combine on Z.',
            second_order='The receiving point changes.',decision='Track the interface.',
            proof=[],counterforces=[dict(kind='conversion_brake',title='Shared gate',
               inference='A verified stress at the receiver could prevent both pathways from scaling.',
               proof=[],network_route=['a','z'])])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'out.docx'
            sections={key:[sample] for key in ('trends','disruptions','risks','opportunities')}
            sections['scenarios']=[]
            write_report(path,sections,{},[],[{'display':'merit'},{'display':'relevance'}])
            d=Document(path)
            text='\n'.join(p.text for p in d.paragraphs)
            self.assertIn('Countertrends and forces that could stop this trajectory',text)
            self.assertIn('Shared gate',text)
            with ZipFile(path) as pkg:
                img=[n for n in pkg.namelist() if n.startswith('word/media/')]
                self.assertGreaterEqual(len(img),5)
