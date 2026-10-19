"""Both Stuff exports must retain their distinct scopes after every rebuild."""
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


@unittest.skipUnless(shutil.which('node'), 'Node.js is required to exercise workbook.js')
class StuffCombinedWorkbookTests(unittest.TestCase):
    def test_browser_download_uses_historical_archive_and_sidecars(self):
        page = (ROOT / 'stuff/index.html').read_text(encoding='utf-8')
        self.assertIn('downloadMainExcel', page)
        self.assertIn('downloadCombinedExcel', page)
        self.assertIn('includeHistorical:!mainOnly', page)
        self.assertIn('source_merit_ranking.xlsx', page)
        self.assertIn('main_radar_stuff.xlsx', page)

    def test_workbook_preserves_main_historical_and_deep_scan_details(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'combined.xlsx'
            main_out = Path(td) / 'main.xlsx'
            script = r'''
const fs = require('fs');
const Merit = require('./source_merit.js');
const Workbook = require('./stuff/workbook.js');
const data = {
  strand_a: [{title:'Main example record',link:'https://example.test/main',source:'European Commission',date:'2026-01-01',summary:'Main finding'}],
  strand_b:[],strand_c:[],frontier_evidence:[],strategic_pathways:[]
};
const key = 'historical:id:historical-1';
const extras = {
  historical:{last_updated:'2026-02-01',items:[{id:'historical-1',title:'Old historical evidence',date:'2020-02-01',source:'Archive'}]},
  reader:{records:{[key]:{profile:'deep-reader-v2-authoritative',reader_what:'Verified historical finding'}}},
  admission:{records:{[key]:{decision:'keep'}}},
  corrections:{records:{[key]:{fields:{source:'Corrected archive publisher'}}}}
};
fs.writeFileSync(process.argv[1],Buffer.from(Workbook.buildXlsx(data,Merit,extras,{includeHistorical:true})));
fs.writeFileSync(process.argv[2],Buffer.from(Workbook.buildXlsx(data,Merit,extras,{includeHistorical:false})));
'''
            subprocess.run(['node', '-e', script, str(out), str(main_out)], cwd=ROOT, check=True, capture_output=True, text=True)
            with zipfile.ZipFile(out) as z:
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                names = [s.get('name') for s in wb.findall('x:sheets/x:sheet', NS)]
                self.assertEqual(names, ['All publication data', 'Historical findings', 'Ranked sources', 'Method', 'Shock audit'])
                main = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
                historical = ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
                method = ET.fromstring(z.read('xl/worksheets/sheet4.xml'))
                self.assertEqual(len(main.findall('x:sheetData/x:row', NS)), 2)
                self.assertEqual(len(historical.findall('x:sheetData/x:row', NS)), 2)
                historical_text = ''.join((t.text or '') for t in historical.findall('.//x:t', NS))
                self.assertIn('Old historical evidence', historical_text)
                self.assertIn('Verified historical finding', historical_text)
                self.assertIn('Corrected archive publisher', historical_text)
                self.assertIn('Authoritative', historical_text)
                method_text = ''.join((t.text or '') for t in method.findall('.//x:t', NS))
                self.assertIn('Historical update lifecycle', method_text)
            with zipfile.ZipFile(main_out) as z:
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                names = [s.get('name') for s in wb.findall('x:sheets/x:sheet', NS)]
                self.assertEqual(names, ['All publication data', 'Ranked sources', 'Method', 'Shock audit'])
                main = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
                self.assertEqual(len(main.findall('x:sheetData/x:row', NS)), 2)
                main_text = ''.join((t.text or '') for t in main.findall('.//x:t', NS))
                self.assertIn('Main example record', main_text)
                self.assertNotIn('Old historical evidence', main_text)


if __name__ == '__main__':
    unittest.main()
