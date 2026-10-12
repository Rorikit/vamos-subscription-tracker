import json,zlib
from urllib.parse import quote
from fastapi import APIRouter,Depends,Query,HTTPException,Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.legacy import LegacySource,LegacySheet,LegacyRecord,LegacyBatch,LegacyPerson
router=APIRouter(prefix="/legacy-history",tags=["legacy-history"])

@router.get("/summary")
def summary(db:Session=Depends(get_db)):
    batches=db.query(LegacyBatch).all()
    return {"sources":db.query(LegacySource).count(),"sheets":db.query(LegacySheet).count(),"records":db.query(LegacyRecord).count(),
            "raw_cells":db.query(func.coalesce(func.sum(LegacySheet.cell_count),0)).scalar(),
            "people":db.query(LegacyPerson).count(),"batches":[json.loads(b.summary_json) for b in batches],
            "files":[{"source_key":s.source_key,"filename":s.original_filename} for s in db.query(LegacySource).all()]}

@router.get("/records")
def records(source_key:str|None=None,search:str|None=None,date_from:str|None=None,date_to:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    from datetime import date
    for value in [date_from,date_to]:
        if value:
            try:date.fromisoformat(value)
            except ValueError:raise HTTPException(422,"Некорректная дата")
    query=db.query(LegacyRecord)
    if source_key:query=query.filter(LegacyRecord.source_key==source_key)
    if search:query=query.filter(LegacyRecord.label.contains(search,autoescape=True))
    if date_from:query=query.filter(LegacyRecord.date>=date_from)
    if date_to:query=query.filter(LegacyRecord.date<=date_to)
    count=query.count()
    rows=query.order_by(LegacyRecord.date.desc(),LegacyRecord.source_key,LegacyRecord.sheet_index,LegacyRecord.row).offset((page-1)*page_size).limit(page_size).all()
    return {"total":count,"items":[{"record_key":r.record_key,"source_key":r.source_key,"sheet":r.sheet_name,"sheet_index":r.sheet_index,"row":r.row,"date":r.date,"label":r.label,"kind":r.kind,"status":r.status} for r in rows]}

@router.get("/records/{record_key}")
def record(record_key:str,db:Session=Depends(get_db)):
    row=db.get(LegacyRecord,record_key)
    if not row:raise HTTPException(404,"Запись не найдена")
    return json.loads(row.payload_json)

@router.get("/sheets/{source_key}/{sheet_index}")
def sheet(source_key:str,sheet_index:int,db:Session=Depends(get_db)):
    row=db.query(LegacySheet).filter_by(source_key=source_key,sheet_index=sheet_index).first()
    if not row:raise HTTPException(404,"Лист не найден")
    return {"metadata":json.loads(row.metadata_json),"cells":json.loads(zlib.decompress(row.cells_compressed))}

@router.get("/files/{source_key}")
def file(source_key:str,original:bool=True,db:Session=Depends(get_db)):
    row=db.get(LegacySource,source_key)
    if not row:raise HTTPException(404,"Книга не найдена")
    name=row.original_filename if original else row.filename
    return Response(content=row.original_blob if original else row.standardized_blob,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":"attachment; filename*=UTF-8''"+quote(name)})
