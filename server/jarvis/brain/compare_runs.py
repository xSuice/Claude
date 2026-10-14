#!/usr/bin/env python3
"""Compare measured user-supplied run results on identical cases.

JSON shape: {"cases":[{"id":"coding-1","passed":true,"quality":0.9,
"rework_minutes":3,"elapsed_seconds":35,"api_input_tokens":null,
"api_output_tokens":null,"pro_quota":null},...]}
Quality rubric must be fixed and independently assessed BEFORE running both versions.
No metrics are automatically fabricated.
"""
import argparse
import json
from pathlib import Path


def validated(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,dict) or not isinstance(data.get('cases'),list) or not data['cases']:
        raise ValueError('cases must be a nonempty list')
    result={}
    for row in data['cases']:
        if not isinstance(row,dict) or type(row.get('id')) is not str or not row['id'] or row['id'] in result:
            raise ValueError('case ids required and unique')
        if type(row.get('passed')) is not bool:raise ValueError('passed must be independently assessed boolean')
        q=row.get('quality')
        if q is not None and (type(q) not in (float,int) or not 0<=q<=1):raise ValueError('quality must be 0..1')
        for k in ('rework_minutes','elapsed_seconds','api_input_tokens','api_output_tokens'):
            v=row.get(k)
            if v is not None and (type(v) not in (float,int) or v<0):raise ValueError(f'invalid {k}')
        result[row['id']]=row
    return result


def diff(before,after):
    if set(before)!=set(after):raise ValueError('comparison requires identical case IDs')
    ids=sorted(before)
    def mean(records,key):
        values=[records[x].get(key) for x in ids]
        return sum(values)/len(values) if all(v is not None for v in values) else None
    def count(records):return sum(bool(records[x]['passed']) for x in ids)
    def tokens(records):
        return (sum(records[x]['api_input_tokens']+records[x]['api_output_tokens'] for x in ids)
                if all(type(records[x].get(k)) in (int,float)
                       for x in ids for k in ('api_input_tokens','api_output_tokens')) else None)
    a,b=count(before),count(after)
    ta,tb=tokens(before),tokens(after)
    q0,q1=mean(before,'quality'),mean(after,'quality')
    quality_gate=(b>=a and q1>=q0) if q0 is not None and q1 is not None else None
    return {'case_count':len(ids),'success_before':a,'success_after':b,
            'mean_quality_before':q0,'mean_quality_after':q1,
            'quality_gate_pass':quality_gate,
            'rework_minutes_before':mean(before,'rework_minutes'),
            'rework_minutes_after':mean(after,'rework_minutes'),
            'elapsed_seconds_before':mean(before,'elapsed_seconds'),
            'elapsed_seconds_after':mean(after,'elapsed_seconds'),
            'api_tokens_before':ta,'api_tokens_after':tb,
            'api_token_delta':None if ta is None or tb is None else tb-ta,
            'claude_pro_quota':'not measurable from this report',
            'decision':('candidate meets supplied quality threshold' if quality_gate is True else
                        'rollback / investigate quality regression' if quality_gate is False else
                        'unmeasured quality: undecided; obtain independent quality scores'),
            'caveat':'Based on externally supplied case results; correctness of pass/quality labels is not automatically verified.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',required=True)
    parser.add_argument('--after',required=True)
    args=parser.parse_args()
    print(json.dumps(diff(validated(args.before),validated(args.after)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
