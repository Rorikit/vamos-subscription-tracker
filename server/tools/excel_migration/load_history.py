"""Explicit import into Vamos; one transaction, source keys prevent duplicates."""
import argparse,json,sqlite3,re
from datetime import datetime
from sqlalchemy import select
from app.database import SessionLocal,engine
from app.models import Teacher,Participant,AuditLog,Operator,OperatorRole
from app.models.legacy import LegacyBatch,LegacySource,LegacySheet,LegacyRecord,LegacyPerson
def norm(x):return ' '.join(x.split()).casefold()
BAD={'артём','вера','вячеслав','екатерина','илья','марина','тимофей','тех','фабричная п.','хабаров п.','набокин т.'}

def import_history(path,db):
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as src:
        assert src.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        fingerprint,summary=src.execute('SELECT * FROM batch').fetchone()
        if db.get(LegacyBatch,fingerprint):return {'already_imported':True,'fingerprint':fingerprint}
        if db.query(LegacyBatch).count():raise ValueError('A different history batch is already present; explicit reconciliation required')
        op=db.query(Operator).filter(Operator.role==OperatorRole.ADMIN,Operator.is_active.is_(True)).first()
        if not op:raise ValueError('An active admin is required')
        db.add(LegacyBatch(fingerprint=fingerprint,summary_json=summary));db.flush()
        for key,name,original_name,meta,original,standard in src.execute('SELECT * FROM sources'):
            db.add(LegacySource(source_key=key,fingerprint=fingerprint,filename=name,original_filename=original_name,metadata_json=meta,original_blob=original,standardized_blob=standard))
        db.flush()
        counts={}
        for source,idx,name,day,n,meta,blob in src.execute('SELECT * FROM sheets'):
            db.add(LegacySheet(source_key=source,sheet_index=idx,name=name,proposed_date=day,cell_count=n,metadata_json=meta,cells_compressed=blob))
        db.flush()
        buffer=[]
        for key,source,idx,sheet,row,kind,day,label,payload in src.execute('SELECT * FROM records'):
            buffer.append(dict(record_key=key,source_key=source,sheet_index=idx,sheet_name=sheet,row=row,kind=kind,date=day,label=label[:255],status='review',payload_json=payload))
            if len(buffer)>=500:db.execute(LegacyRecord.__table__.insert(),buffer);buffer=[]
        if buffer:db.execute(LegacyRecord.__table__.insert(),buffer)
        # Existing records are reused only by exact labels, never by a surname guess.
        indexes={role:{norm(p.full_name):p for p in db.query(cls).all()} for role,cls in [('teacher',Teacher),('student',Participant)]}
        for role,label,variants in src.execute('SELECT * FROM people'):
            person=indexes[role].get(norm(label));resolution='exact_existing' if person else 'created_from_approved_label'
            if not person:
                if role=='student' and (norm(label) in BAD or not re.fullmatch(r'[А-ЯЁа-яё-]+(?: [А-ЯЁ][.])?',label)):
                    resolution='label_requires_review'
                else:
                    cls=Teacher if role=='teacher' else Participant
                    comment='Из Excel. Исходные варианты: '+', '.join(json.loads(variants))
                    if role=='student':comment+='; историческая запись; активность и остатки не подтверждены'
                    person=cls(full_name=label,comment=comment,is_active=(role=='teacher'))
                    db.add(person);db.flush();indexes[role][norm(label)]=person
                    counts[role]=counts.get(role,0)+1
            db.add(LegacyPerson(role=role,label=label,variants_json=variants,product_id=person.id if person else None,resolution=resolution))
        db.flush()
        expected=json.loads(summary)['stats']
        for cls,key in [(LegacySource,'sources'),(LegacySheet,'sheets'),(LegacyRecord,'events')]:
            assert db.query(cls).count()==expected[key]
        db.add(AuditLog(operator_id=op.id,operator_name=op.full_name,action='excel_history_imported',entity_type='legacy_batch',entity_label=fingerprint,after_json=json.dumps({'stats':expected,'created_people':counts},ensure_ascii=False)))
        return {'fingerprint':fingerprint,'created_people':counts,'records':expected['events'],'sheets':expected['sheets'],'raw_cells':expected['raw_cells']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');args=p.parse_args()
    for model in [LegacyBatch,LegacySource,LegacySheet,LegacyRecord,LegacyPerson]:model.__table__.create(engine,checkfirst=True)
    with SessionLocal() as db,db.begin():result=import_history(args.package,db)
    print(json.dumps(result,ensure_ascii=False))
