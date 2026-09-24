#!/usr/bin/env python3
"""Build LinuxToys' static Myket category-affinity table from the public sample."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import pandas as pd

MIN_PAIR_SUPPORT = 30
SHRINKAGE_K = 100.0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('myket_csv', type=Path)
    ap.add_argument('app_info_csv', type=Path)
    ap.add_argument('-o','--output',type=Path,default=Path('myket_affinity.json'))
    ap.add_argument('--diagnostics',type=Path)
    args=ap.parse_args()
    apps=pd.read_csv(args.app_info_csv)
    events=pd.read_csv(args.myket_csv)
    merged=events.merge(apps[['app_name','category_en']],on='app_name',how='left')
    memberships=(merged.dropna(subset=['category_en'])[['user_id','category_en']].drop_duplicates())
    matrix=pd.crosstab(memberships.user_id,memberships.category_en).astype(bool)
    total_users=matrix.shape[0]; support=matrix.sum(); rows=[]
    for source in sorted(matrix.columns):
        for target in sorted(matrix.columns):
            if source==target: continue
            co=int((matrix[source]&matrix[target]).sum())
            p_source=support[source]/total_users; p_target=support[target]/total_users; p_pair=co/total_users
            confidence=co/support[source]
            lift=p_pair/(p_source*p_target) if p_pair else 0.0
            npmi=(math.log(lift)/-math.log(p_pair)) if p_pair and lift>0 and p_pair<1 else 0.0
            reliability=co/(co+SHRINKAGE_K)
            shrunk=max(0.0,math.log(lift))*reliability if lift>1 else 0.0
            rows.append((source,target,int(support[source]),int(support[target]),co,confidence,lift,npmi,reliability,shrunk))
    cols=['source','target','source_users','target_users','co_users','confidence','lift','npmi','reliability','shrunk_log_lift']
    df=pd.DataFrame(rows,columns=cols)
    eligible=df[(df.co_users>=MIN_PAIR_SUPPORT)&(df.lift>1)&(df.npmi>0)].copy()
    max_shrunk=float(eligible.shrunk_log_lift.max()); max_npmi=float(eligible.npmi.max())
    eligible['affinity_raw']=0.75*(eligible.shrunk_log_lift/max_shrunk)+0.25*(eligible.npmi/max_npmi)
    eligible['affinity']=eligible.affinity_raw/float(eligible.affinity_raw.max())
    lookup={(r.source,r.target):r.affinity for r in eligible.itertuples()}
    df['affinity']=[lookup.get((a,b),0.0) for a,b in zip(df.source,df.target)]
    table={}
    for source in sorted(matrix.columns):
        values=eligible[eligible.source==source].sort_values('affinity',ascending=False)
        table[source]={r.target:round(float(r.affinity),6) for r in values.itertuples() if r.affinity>=0.05}
    payload={'schema':1,'method':{'users':int(total_users),'interactions':int(len(events)),'categorized_interactions':int(merged.category_en.notna().sum()),'categories':int(len(matrix.columns)),'minimum_pair_support':MIN_PAIR_SUPPORT,'shrinkage_k':SHRINKAGE_K,'formula':'0.75 * normalized(max(0, ln(lift)) * support/(support+100)) + 0.25 * normalized(max(0, NPMI)); final positive scores normalized to 0..1','minimum_stored_affinity':0.05},'category_support':{k:int(v) for k,v in support.sort_index().items()},'affinity':table}
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.diagnostics: df.to_csv(args.diagnostics,index=False)

if __name__=='__main__': main()
