import copy,json,tempfile,unittest
from pathlib import Path
from vamos_importer import build,stage
from apply_reviewed import approved_payloads
from test_importer import fixture

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.db=root/'stage.sqlite';p=root/'source.xlsx'
        fixture(p,{2:{'A2':'Абонементы','C2':'Безнал','D2':'Нал','E2':'QR'},3:{'A3':'Example A.','D3':1200,'E3':800}})
        m={'currency':'RUB','books':[{'source_key':'income','kind':'income','path':str(p)}]}
        r=build(m);stage(r,self.db);e=r['events'][0]
        self.d={'fingerprint':r['fingerprint'],'decisions':[{'record_key':e['record_key'],'action':'receipt','reviewed_issues':e['issues'],'reason':'Verified externally','date':'2026-10-07','site_id':'hall','person_id':'1','membership_id':'1','category_id':'membership_payment','payment_cells':['D3','E3']}]}
    def tearDown(self):self.tmp.cleanup()
    def test_split_payment_exact(self):
        out=approved_payloads(self.db,self.d)
        self.assertEqual(len(out),2);self.assertEqual([p['amount'] for p in out],['1200','800'])
        self.assertNotEqual(out[0]['idempotency_key'],out[1]['idempotency_key'])
    def test_unreviewed_issue_blocks(self):
        d=copy.deepcopy(self.d);d['decisions'][0]['reviewed_issues']=[]
        with self.assertRaises(ValueError):approved_payloads(self.db,d)
    def test_other_batch_blocks(self):
        d=copy.deepcopy(self.d);d['fingerprint']='wrong'
        with self.assertRaises(ValueError):approved_payloads(self.db,d)
    def test_nonpayment_cell_blocks(self):
        d=copy.deepcopy(self.d);d['decisions'][0]['payment_cells']=['A3']
        with self.assertRaises(ValueError):approved_payloads(self.db,d)
    def test_same_cell_twice_blocks(self):
        d=copy.deepcopy(self.d);d['decisions'][0]['payment_cells']=['D3','D3']
        with self.assertRaises(ValueError):approved_payloads(self.db,d)
    def test_date_mismatch_blocks(self):
        d=copy.deepcopy(self.d);d['decisions'][0]['date']='2026-10-08'
        with self.assertRaises(ValueError):approved_payloads(self.db,d)
    def test_ignored_does_not_deliver(self):
        d=copy.deepcopy(self.d);d['decisions'][0]['action']='skip'
        self.assertEqual(approved_payloads(self.db,d),[])

if __name__=='__main__':unittest.main()
