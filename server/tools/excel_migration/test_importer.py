import copy, json, sqlite3, tempfile, unittest, zipfile
from contextlib import closing
from pathlib import Path
from decimal import Decimal
from vamos_importer import build, stage, number, XLSX

def fixture(path, rows, sheetname='07.10'):
    """Minimal independent OOXML fixture; never modifies supplied workbooks."""
    from xml.sax.saxutils import escape
    row_xml=[]
    for r, cs in rows.items():
        cells=[]
        for address, spec in cs.items():
            if isinstance(spec,tuple):
                formula, cache=spec
                cells.append(f'<c r="{address}"><f>{escape(formula)}</f>'+('' if cache is None else f'<v>{cache}</v>')+'</c>')
            elif isinstance(spec,(int,float)):
                cells.append(f'<c r="{address}"><v>{spec}</v></c>')
            else:
                cells.append(f'<c r="{address}" t="inlineStr"><is><t>{escape(spec)}</t></is></c>')
        row_xml.append(f'<row r="{r}">'+''.join(cells)+'</row>')
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('xl/workbook.xml',f'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{sheetname}" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(row_xml)+'</sheetData></worksheet>')

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.dir=Path(self.tmp.name)
        self.path=self.dir/'income.xlsx'
        fixture(self.path,{2:{'A2':'Абонементы','C2':'Безнал','D2':'Нал','E2':'QR'},3:{'A3':'Иванова А.','D3':1200,'E3':800},4:{'A4':'Иванова А.','D4':1200},5:{'A5':'Итого','D5':('SUM(D3:D4)',2400)}})
        self.m={'currency':'RUB','books':[{'source_key':'income','kind':'income','path':str(self.path)}]}
    def tearDown(self):self.tmp.cleanup()
    def test_missing_dates_and_unresolved_identity(self):
        r=build(self.m)
        self.assertTrue(all(e['date'] is None and e['status']=='review' for e in r['events']))
        self.assertIn('UNRESOLVED_STUDENT',r['events'][0]['issues'])
        self.assertEqual(r['events'][0]['payments']['qr'][0]['amount'],'800')
    def test_no_automatic_collapse(self):
        r=build(self.m,{'student':{'иванова а.':'Иванова А.'}})
        self.assertEqual(len(r['events']),3)
        self.assertNotEqual(r['events'][0]['record_key'],r['events'][1]['record_key'])
        self.assertIsNone(r['events'][0]['person']['product_id'])
    def test_total_formula_not_money(self):
        r=build(self.m)
        self.assertEqual(r['stats']['recognized_detail_amounts']['income']['cash'],'2400')
        self.assertIn('INVALID_PAYMENT_VALUE',r['events'][2]['issues'])
    def test_exact_decimal(self):
        self.assertEqual(number({'type':'inlineStr','value':'1 234,50'},True),'1234.50')
        for v in ['1,234.50','3.001','NaN']:
            with self.assertRaises(ValueError):number({'type':'inlineStr','value':v},True)
    def test_date_boolean_not_money(self):
        for c in [{'type':'b','value':'1'},{'type':'n','value':'45000','is_date':True},{'type':'n','value':'10','formula':'A1+1'}]:
            with self.assertRaises(ValueError):number(c,True)
    def test_manifest_date_conflict(self):
        m=copy.deepcopy(self.m);m['sheet_dates']={'income':{'1':'2026-10-08'}}
        with self.assertRaises(ValueError):build(m)
    def test_potential_payment_overlap(self):
        m=copy.deepcopy(self.m);m.update(sheet_dates={'income':{'1':'2026-10-07'}},sheet_sites={'income':{'1':'hall-a'}},person_bindings={'student':{'иванова а.':'student-17'}})
        r=build(m)
        self.assertIn('POSSIBLE_OVERLAPPING_PAYMENT',r['events'][0]['issues'])
    def test_atomic_and_idempotent(self):
        r=build(self.m);db=self.dir/'stage.sqlite'
        self.assertTrue(stage(r,db)['inserted']);self.assertFalse(stage(r,db)['inserted'])
        with closing(sqlite3.connect(db)) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM migration_events').fetchone()[0],len(r['events']))
        changed=copy.deepcopy(r);changed['fingerprint']='other'
        with self.assertRaises(ValueError):stage(changed,db)
        with closing(sqlite3.connect(db)) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM migration_batches').fetchone()[0],1)
    def test_transaction_rollback(self):
        r=build(self.m);r['events'].append(copy.deepcopy(r['events'][0]));db=self.dir/'bad.sqlite'
        with self.assertRaises(sqlite3.IntegrityError):stage(r,db)
        with closing(sqlite3.connect(db)) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM migration_sources').fetchone()[0],0)
    def test_new_config_requires_fresh_stage(self):
        r=build(self.m);db=self.dir/'stage.sqlite';stage(r,db)
        m=copy.deepcopy(self.m);m['sheet_dates']={'income':{'1':'2025-10-07'}}
        with self.assertRaises(ValueError):stage(build(m),db)
    def test_rich_text_preserved(self):
        from xml.etree.ElementTree import fromstring
        e=fromstring('<si xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><r><t>Иванова</t></r><r><t> А.</t></r><rPh><t>phonetics</t></rPh></si>')
        self.assertEqual(XLSX.text(e),'Иванова А.')
    def test_group_repeated_blocks(self):
        p=self.dir/'groups.xlsx'
        fixture(p,{2:{'B2':'Макаров'},3:{'B3':'19:00'},4:{'B4':'ФИО ученика','C4':'Абонемент','D4':'Цена аб.','G4':'Нал','H4':'Безнал','I4':'QR'},5:{'B5':'Иванова А.','C5':'8','D5':6200},6:{'B6':'отмена'},12:{'B12':'Макарова'},13:{'B13':'20:00'},14:{'B14':'ФИО ученика','C14':'Абонемент','D14':'Цена аб.','G14':'Нал','H14':'Безнал','I14':'QR'},15:{'B15':'Петров П.','G15':1500}})
        m={'currency':'RUB','books':[{'source_key':'groups','kind':'groups','path':str(p)}]}
        r=build(m);self.assertEqual(len(r['events']),3)
        self.assertEqual(r['events'][0]['teacher']['raw'],'Макаров')
        self.assertEqual(r['events'][2]['teacher']['raw'],'Макарова')
        self.assertEqual(r['events'][0]['payments'],{})
        self.assertIn('SERVICE_OR_COMBINED_PERSON_ROW',r['events'][1]['issues'])

if __name__=='__main__':unittest.main()
