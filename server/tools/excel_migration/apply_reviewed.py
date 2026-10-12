"""Validate reviewed facts and call an adapter supplied by the Vamos project.

An adapter exports create_adapter() and implements:
  transaction() -> context manager, including rollback and commit
  assert_reference(kind, product_id) -> raise if tenant/reference is invalid
  deliver_once(idempotency_key, source_fingerprint, payload) -> bool

deliver_once MUST insert the business row and its unique migration ledger entry
in the same database transaction. The actual product schema owns this method.
"""
import argparse, importlib, json, sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path
from vamos_importer import canonical_json, digest

def approved_payloads(db_path, decisions):
    with closing(sqlite3.connect(db_path)) as db:
        batches=db.execute('SELECT fingerprint FROM migration_batches').fetchall()
        if len(batches)!=1:raise ValueError('expected one complete import batch')
        fingerprint=batches[0][0]
        found={k:json.loads(p) for k,p in db.execute('SELECT record_key,payload_json FROM migration_events')}
        sheets={(s['source_key'],s['index']):s for (raw,) in db.execute('SELECT payload_json FROM migration_sheets') for s in [json.loads(raw)]}
    if decisions.get('fingerprint')!=fingerprint:raise ValueError('review decisions refer to a different source batch')
    payloads=[];used=set();reviewed=set()
    for decision in decisions['decisions']:
        record=decision['record_key']
        if record in reviewed:raise ValueError('duplicate event decision')
        reviewed.add(record)
        if record not in found:raise ValueError('unknown event key')
        e=found[record]
        if decision['action']=='skip':continue
        if not str(decision.get('reason','')).strip():raise ValueError('explain the review decision')
        if sorted(set(decision.get('reviewed_issues',[])))!=e['issues']:raise ValueError('all event issues must be explicitly reviewed')
        event_date=date.fromisoformat(decision['date']).isoformat()
        if e['date'] and e['date']!=event_date:raise ValueError('date differs from confirmed manifest')
        sheet=sheets[(e['location']['source_key'],e['location']['sheet_index'])]
        import re
        match=re.match(r'^\s*(\d{1,2})[.,](\d{1,2})(?:[.,](\d{4}))?(?:\s|$)',sheet['name'])
        if match:
            d=date.fromisoformat(event_date)
            if (d.day,d.month)!=(int(match[1]),int(match[2])) or (match[3] and d.year!=int(match[3])):raise ValueError('review date contradicts sheet label')
        site=decision.get('site_id')
        if not isinstance(site,str) or not site.strip():raise ValueError('site_id is required')
        if e['site_id'] and e['site_id']!=site:raise ValueError('site differs from confirmed manifest')
        base={'event_key':record,'source_fingerprint':fingerprint,'source':e['location'],'date':event_date,'site_id':site,'review_reason':decision['reason']}
        if decision['action']=='attendance':
            if e['location']['kind']!='group_row' or 'SERVICE_OR_COMBINED_PERSON_ROW' in e['issues']:raise ValueError('not an attendance row')
            for name in ['student_id','teacher_id','session_id']:
                if not isinstance(decision.get(name),str) or not decision[name].strip():raise ValueError(name+' is required')
            payloads.append({**base,'kind':'attendance','student_id':decision['student_id'],'teacher_id':decision['teacher_id'],'session_id':decision['session_id'],
                             'membership_id':decision.get('membership_id'),'revision_id':decision.get('revision_id'),'balance_mode':decision.get('balance_mode'),
                             'idempotency_key':digest({'event':record,'fact':'attendance'})})
        elif decision['action'] in ['receipt','expense']:
            if decision['action']=='expense' and e['location']['kind']!='expense_row':raise ValueError('expense must come from the expense workbook')
            if decision['action']=='receipt' and e['location']['kind']=='expense_row':raise ValueError('expense cannot become receipt')
            person=decision.get('person_id')
            category=decision.get('category_id')
            if not isinstance(category,str) or not category.strip():raise ValueError('category_id is required')
            source_payments={p['cell']:(channel,p['amount']) for channel,ps in e['payments'].items() for p in ps}
            selected=decision.get('payment_cells',[])
            if not isinstance(selected,list) or not selected:raise ValueError('explicit payment cells required')
            if e['location']['kind']=='group_row' and not decision.get('primary_payment_evidence'):raise ValueError('group receipt requires explicit primary evidence confirmation')
            for cell in selected:
                cellkey=(e['location']['source_key'],e['location']['sheet_index'],cell)
                if cellkey in used:raise ValueError('payment cell selected twice')
                used.add(cellkey)
                if cell not in source_payments:raise ValueError('not a validated payment cell; formulas cannot become receipts')
                channel,amount=source_payments[cell]
                if Decimal(amount)<=0:raise ValueError('zero/refund requires a separate reviewed adjustment flow')
                payloads.append({**base,'kind':decision['action'],'person_id':person,'category_id':category,'currency':e['currency'],'amount':amount,'channel':channel,'cell':cell,
                                 'membership_id':decision.get('membership_id'),'title':decision.get('title'),'section':e['section'],
                                 'idempotency_key':digest({'source':cellkey,'fact':'payment'})})
        else:raise ValueError('unsupported review action')
    # Same reviewed person/day/site/channel/amount may be overlapping evidence.
    groups={}
    for payload in payloads:
        if payload['kind']!='receipt' or not payload.get('person_id'):continue
        candidate=(payload['person_id'],payload['date'],payload['site_id'],payload['channel'],Decimal(payload['amount']))
        groups.setdefault(candidate,[]).append(payload)
    for group in groups.values():
        if len(group)<2:continue
        keys=sorted(p['idempotency_key'] for p in group)
        confirmations=decisions.get('distinct_payment_confirmations',[])
        if not any(sorted(x.get('idempotency_keys',[]))==keys and str(x.get('reason','')).strip() for x in confirmations):
            raise ValueError('possible overlapping receipts: select one source or explicitly confirm distinct real payments')
    return payloads

def deliver(payloads, adapter):
    inserted=0
    with adapter.transaction():
        for p in payloads:
            adapter.assert_reference('site',p['site_id'])
            for kind,field in [('student','student_id'),('teacher','teacher_id'),('session','session_id'),('person','person_id'),('category','category_id')]:
                if kind=='category' and p['kind']!='expense':continue
                if p.get(field):adapter.assert_reference(kind,p[field])
            inserted+=bool(adapter.deliver_once(p['idempotency_key'],p['source_fingerprint'],p))
    return inserted

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage-db',type=Path,required=True);p.add_argument('--decisions',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--adapter',help='project module:factory; omit for dry run')
    args=p.parse_args()
    payloads=approved_payloads(args.stage_db,json.loads(args.decisions.read_text(encoding='utf-8')))
    args.out.write_text(''.join(canonical_json(x)+'\n' for x in payloads),encoding='utf-8')
    if args.adapter:
        module,factory=args.adapter.split(':',1)
        adapter=getattr(importlib.import_module(module),factory)()
        print(canonical_json({'delivered':deliver(payloads,adapter),'reviewed_facts':len(payloads)}))
    else:print(canonical_json({'dry_run':True,'reviewed_facts':len(payloads)}))

if __name__=='__main__':main()
