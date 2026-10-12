"""Extract label suggestions from the approved DOCX; stdlib only."""
import json, sys, zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from vamos_importer import key
with zipfile.ZipFile(sys.argv[1]) as z:
    root=ET.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
result={}
for role,table in zip(['teacher','student'],root.findall('.//w:body/w:tbl',ns)):
    variants=defaultdict(set)
    for row in table.findall('w:tr',ns)[1:]:
        cells=row.findall('w:tc',ns)
        text=lambda c:''.join(t.text or '' for t in c.findall('.//w:t',ns))
        canon=text(cells[0])
        for v in [canon]+text(cells[1]).split('; '):variants[key(v)].add(canon)
    result[role]={k:next(iter(v)) for k,v in variants.items() if len(v)==1}
Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print({role:len(values) for role,values in result.items()})
