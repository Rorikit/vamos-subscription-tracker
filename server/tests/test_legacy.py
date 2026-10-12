import unittest,json,zlib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models.legacy import LegacyBatch,LegacySource,LegacySheet,LegacyRecord
from app.routers.legacy import summary,records,record,sheet,file
class LegacyTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine("sqlite:///:memory:");Base.metadata.create_all(self.engine);self.db=Session(self.engine)
  self.db.add(LegacyBatch(fingerprint="batch",summary_json="{}"));self.db.flush()
  self.db.add(LegacySource(source_key="groups",fingerprint="batch",filename="clean.xlsx",original_filename="original.xlsx",metadata_json="{}",original_blob=b"original",standardized_blob=b"clean"));self.db.flush()
  self.db.add(LegacySheet(source_key="groups",sheet_index=1,name="07.10",proposed_date="2026-10-07",cell_count=1,metadata_json="{}",cells_compressed=zlib.compress(b'[{"address":"B5","value":"name"}]')))
  self.db.add(LegacyRecord(record_key="key",source_key="groups",sheet_index=1,sheet_name="07.10",row=5,kind="group_row",date="2026-10-07",label="Example",status="review",payload_json='{"cells":{}}'));self.db.commit()
 def tearDown(self):self.db.close();self.engine.dispose()
 def test_counts_and_raw_preserved(self):
  s=summary(self.db);self.assertEqual((s["sources"],s["sheets"],s["records"],s["raw_cells"]),(1,1,1,1))
  self.assertEqual(sheet("groups",1,self.db)["cells"][0]["address"],"B5")
 def test_record_filters_and_details(self):
  self.assertEqual(records(source_key="groups",search="Example",date_from="2026-10-01",date_to=None,page=1,page_size=50,db=self.db)["total"],1)
  self.assertEqual(record("key",self.db),{"cells":{}})
 def test_original_download_exact(self):self.assertEqual(file("groups",True,self.db).body,b"original")
 def test_bad_date_rejected(self):
  from fastapi import HTTPException
  with self.assertRaises(HTTPException):records(source_key=None,search=None,date_from="bad",date_to=None,page=1,page_size=50,db=self.db)
if __name__=="__main__":unittest.main()
