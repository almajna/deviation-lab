#!/usr/bin/env python3
"""Privacy-safe archive schema metadata only; do not emit values or rows."""
import hashlib,json,re,sys,tarfile
from pathlib import Path,PurePosixPath
path=Path(sys.argv[1]); target=Path(sys.argv[2])
if hashlib.sha256(path.read_bytes()).hexdigest()!='e185bfd037fa9fa5727dbae0eb8eba421dfb5011dfec6f4dc60b111d51e7a85f':
    raise SystemExit('source digest mismatch')
out=[]; count=0; total=0
with tarfile.open(path,'r:gz') as arc:
    for member in arc:
        count+=1; total+=member.size
        name=PurePosixPath(member.name)
        if name.is_absolute() or '..' in name.parts or member.issym() or member.islnk():
            safe_name=name.name if re.fullmatch(r'[A-Za-z0-9_.-]+',name.name) else 'redacted-name'
            out.append({'basename':safe_name,'size':member.size,'error':'unsafe-member',
                        'absolute':name.is_absolute(),'parent_component':'..' in name.parts,
                        'symlink':member.issym(),'hardlink':member.islnk(),
                        'link_target_sha256':hashlib.sha256(member.linkname.encode()).hexdigest()})
            target.write_text(json.dumps({'source_sha256':'e185bfd037fa9fa5727dbae0eb8eba421dfb5011dfec6f4dc60b111d51e7a85f','members':out},indent=2,sort_keys=True)+'\n')
            raise SystemExit('unsafe archive member')
        if count>15000 or total>350_000_000 or member.size>50_000_000:
            raise SystemExit('archive bounds exceeded')
        if not member.isfile() or not name.name.endswith('_report.json') or '_combined' in name.parts:
            continue
        safe_name=name.name if re.fullmatch(r'[A-Za-z0-9_.-]+',name.name) else 'redacted-name'
        rec={'basename':safe_name,'size':member.size}
        stream=arc.extractfile(member)
        try:
            parsed=json.load(stream)
            rec['valid_json']=True
            rec['root_type']=type(parsed).__name__
            if isinstance(parsed,dict):
                rec['keys']=sorted(k for k in parsed if isinstance(k,str) and re.fullmatch(r'[A-Za-z0-9_]+',k))
        except json.JSONDecodeError as e:
            rec.update(valid_json=False,error='JSONDecodeError',line=e.lineno,column=e.colno,offset=e.pos)
        except UnicodeError:
            rec.update(valid_json=False,error='UnicodeError')
        out.append(rec)
target.write_text(json.dumps({'source_sha256':'e185bfd037fa9fa5727dbae0eb8eba421dfb5011dfec6f4dc60b111d51e7a85f','members':out},indent=2,sort_keys=True)+'\n')
