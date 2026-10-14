#!/usr/bin/env python3
"""Print OpenSSH restricted forced-command lines; never writes authorized_keys."""
import argparse
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bin-dir',required=True,type=Path)
    p.add_argument('--person-a-public-key',type=Path,required=True)
    p.add_argument('--person-b-public-key',type=Path)
    a=p.parse_args()
    for identity,key in [('person-a',a.person_a_public_key),('person-b',a.person_b_public_key)]:
        if key is None:continue
        pub=key.read_text(encoding='utf-8').strip()
        parts=pub.split()
        if len(parts)<2 or parts[0] not in ('ssh-ed25519','ecdsa-sha2-nistp256','ssh-rsa') or len(parts[1])<32:
            raise SystemExit('Unrecognized public key: '+str(key))
        shell=a.bin_dir.resolve() / ('mcp-'+identity)
        if not shell.is_file():raise SystemExit('missing installed wrapper: '+str(shell))
        if any(x in str(shell) for x in '\n\r"\\'):
            raise SystemExit('unsafe directory path for SSH command; use simpler path')
        print('restrict,command="'+str(shell)+'" '+parts[0]+' '+parts[1]+' '+identity)
if __name__=='__main__':main()
