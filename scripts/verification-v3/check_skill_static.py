from pathlib import Path
import ast,json,os,re,subprocess
root=Path(os.environ['LOCALAPPDATA'])/'hermes/profiles/kimi-supervisor/skills'
rows=[]
for skill in root.rglob('SKILL.md'):
    base=skill.parent;t=skill.read_text(encoding='utf-8-sig')
    refs=sorted(set(re.findall(r'(?<![\w/])((?:references|templates|scripts|assets)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)',t)))
    row={'skill':str(skill.relative_to(root)), 'unresolved_path_mentions':[r for r in refs if not (base/r).exists()], 'python_checked':0,'python_errors':[]}
    scripts=base/'scripts'
    if scripts.is_dir():
        for p in scripts.rglob('*.py'):
            row['python_checked']+=1
            try:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
            except Exception as e:row['python_errors'].append({'path':str(p.relative_to(base)),'type':type(e).__name__})
    rows.append(row)
out={'scope':'Metadata, explicit local references and Python AST only; does not prove external-service functionality','skills':rows}
p=Path('C:/Users/andre/Documents/kimi-solo-dev/V3-SKILL-STATIC-CHECK.json');p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'skills':len(rows),'python_scripts':sum(r['python_checked'] for r in rows),'python_errors':sum(len(r['python_errors']) for r in rows),'unresolved_path_mentions':sum(len(r['unresolved_path_mentions']) for r in rows),'affected':[{k:r[k] for k in ('skill','unresolved_path_mentions','python_errors')} for r in rows if r['unresolved_path_mentions'] or r['python_errors']]},ensure_ascii=False,indent=2))
