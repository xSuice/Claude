#!/usr/bin/env python3
"""Read-only local Claude Code config hygiene report, no tokens and no secret values."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path


HOOK_EVENTS=('SessionStart','SessionEnd','UserPromptSubmit','PreToolUse','PostToolUse',
             'PostToolUseFailure','Stop','PreCompact','SubagentStart','SubagentStop')


def analyze(root: Path, include_user=False):
    root=root.resolve(strict=True)
    paths=[root/'.claude'/'settings.json',root/'.claude'/'settings.local.json']
    if include_user:paths.append(Path.home()/'.claude'/'settings.json')
    messages=[]; counts=Counter(); fingerprints=Counter(); loaded_bytes=0; scanned=[]; configs=[]
    files=[root/'CLAUDE.md']
    rules=root/'.claude'/'rules'
    if rules.is_dir():files+=list(rules.rglob('*.md'))[:100]
    for path in files:
        try:
            if path.is_file():loaded_bytes+=path.stat().st_size
        except OSError:pass
    for path in paths:
        if not path.is_file():continue
        scanned.append(str(path))
        try:
            raw=json.loads(path.read_text(encoding='utf-8'))
        except (ValueError,OSError) as e:
            messages.append(f'Invalid/inaccessible settings file: {path.name}: {type(e).__name__}')
            continue
        if not isinstance(raw,dict):messages.append('Invalid settings JSON object');continue
        configs.append(raw)
        hooks=raw.get('hooks',{})
        if not isinstance(hooks,dict):
            messages.append('hooks is not an object');continue
        for event,groups in hooks.items():
            if event not in HOOK_EVENTS:messages.append('Other event present: '+str(event))
            if not isinstance(groups,list):continue
            for group in groups:
                if not isinstance(group,dict):continue
                match=group.get('matcher','')
                for item in group.get('hooks',[]):
                    if not isinstance(item,dict):continue
                    typ=item.get('type','unknown');counts[f'{event}:{typ}']+=1
                    # Internal digest need only duplicates count, never show secrets/commands.
                    name=item.get('command') or item.get('prompt') or item.get('url') or ''
                    if name:fingerprints[(event,match,typ,str(name))]+=1
    duplicate_groups=sum(1 for count in fingerprints.values() if count>1)
    duplicate_extra=sum(x-1 for x in fingerprints.values() if x>1)
    warnings=[]
    if duplicate_extra:warnings.append(f'{duplicate_extra} duplicate hook registrations across reviewed files')
    if loaded_bytes>16000:warnings.append('Large always-loaded instruction footprint; inspect CLAUDE.md and rules')
    for key,value in counts.items():
        if ('prompt' in key or 'agent' in key) and value:
            warnings.append('Model-backed hook exists; inspect actual run frequency and total quota')
            break
    return {'root':str(root),'settings_files_reviewed':scanned,
            'hooks_by_event_and_type':dict(sorted(counts.items())),
            'duplicate_hook_groups':duplicate_groups,'duplicate_hook_entries':duplicate_extra,
            'always_loaded_instruction_bytes_approx':loaded_bytes,
            'warnings':warnings+messages,
            'mcp_configuration_from_settings_files':sum(
              len(x['mcpServers']) for x in configs if isinstance(x.get('mcpServers'),dict)),
            'limits':'Read-only approximation. Does not inspect all Claude CLI registrations, running hooks, or actual token usage. No secrets shown.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--include-user',action='store_true')
    args=p.parse_args()
    print(json.dumps(analyze(args.root,args.include_user),indent=2,ensure_ascii=False))

if __name__=='__main__':main()
