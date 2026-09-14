"""Canonical-unit BMS CSV quality checks. Does not make battery safety or health predictions."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED=['battery_id','timestamp','pack_voltage','pack_current','SOC','cell_voltage_max',
          'cell_voltage_min','temperature_max','temperature_min','charge_status']
META=['battery_id','battery_chemistry','rated_capacity_ah','current_sign_convention',
      'voltage_unit','current_unit','temperature_unit','soc_unit','data_origin']
UNITS={'voltage_unit':'V','current_unit':'A','temperature_unit':'degC','soc_unit':'%'}
BOUNDS={'pack_voltage':(0,2000),'pack_current':(-10000,10000),'SOC':(0,100),
        'cell_voltage_max':(0,10),'cell_voltage_min':(0,10),'temperature_max':(-60,150),'temperature_min':(-60,150)}

def validate(telemetry,metadata,max_gap_s=30):
    if not np.isfinite(max_gap_s) or max_gap_s<=0: raise ValueError('max_gap_s must be positive')
    t=telemetry.copy().reset_index(drop=True);m=metadata.copy().reset_index(drop=True)
    issues=[];reject=set();fatal=False
    def issue(row,severity,code,field,detail):
        issues.append({'csv_row':row,'severity':severity,'code':code,'field':field,'detail':detail})
        if severity=='error' and row>=2:reject.add(row-2)
    missing_t=[c for c in REQUIRED if c not in t]
    missing_m=[c for c in META if c not in m]
    for field in missing_t:issue(0,'error','missing_telemetry_column',field,'Required column absent');fatal=True
    for field in missing_m:issue(0,'error','missing_metadata_column',field,'Required metadata absent');fatal=True
    if t.empty:issue(0,'error','empty_input','','No telemetry rows');fatal=True
    if m.empty:issue(0,'error','empty_metadata','','No metadata rows');fatal=True
    bad_ids=set()
    if not missing_m:
        for _,r in m.iterrows():
            b=r.battery_id
            if pd.isna(b) or not str(b).strip():
                issue(0,'error','empty_metadata_id','battery_id','ID required');fatal=True;continue
            problems=[]
            if m.battery_id.eq(b).sum()!=1:problems.append('duplicate battery_id')
            for field,unit in UNITS.items():
                if r[field]!=unit:problems.append(f'{field} must be {unit}; no inferred conversion')
            if r.current_sign_convention not in ('discharge_positive','charge_positive'):problems.append('unknown current sign convention')
            try:
                cap=float(r.rated_capacity_ah)
                if not np.isfinite(cap) or cap<=0:problems.append('invalid rated capacity')
            except (ValueError,TypeError):problems.append('invalid rated capacity')
            if pd.isna(r.battery_chemistry) or str(r.battery_chemistry).strip().lower() in ('','unknown'):
                problems.append('battery chemistry unknown')
            if pd.isna(r.data_origin) or not str(r.data_origin).strip():problems.append('data origin not declared')
            if problems:
                bad_ids.add(b);issue(0,'error','invalid_metadata','battery_id',f'{b}: '+ '; '.join(problems))
    if fatal:reject.update(t.index)
    if not missing_t and not missing_m and not fatal:
        t['_parsed_time']=pd.Series(pd.NaT,index=t.index,dtype='datetime64[ns, UTC]')
        t['pack_current_raw']=t['pack_current'].copy()
        for c in BOUNDS:t[c]=pd.to_numeric(t[c],errors='coerce').astype(float)
        for idx,row in t.iterrows():
            line=idx+2;b=row.battery_id
            if pd.isna(b) or b not in set(m.battery_id):
                issue(line,'error','unknown_battery_id','battery_id','No matching metadata');continue
            if b in bad_ids:issue(line,'error','metadata_rejected','battery_id','Invalid metadata for this cell/pack')
            raw=str(row.timestamp)
            if not re.search(r'(Z|[+-]\d{2}:?\d{2})$',raw):
                issue(line,'error','timestamp_timezone_missing','timestamp','Explicit Z or UTC offset required')
            else:
                parsed=pd.to_datetime(raw,utc=True,errors='coerce')
                if pd.isna(parsed):issue(line,'error','timestamp_invalid','timestamp','Cannot parse timestamp')
                else:t.at[idx,'_parsed_time']=parsed
            for c,(low,high) in BOUNDS.items():
                value=pd.to_numeric(row[c],errors='coerce')
                if not np.isfinite(value):issue(line,'error','numeric_missing_or_invalid',c,'Finite numeric value required')
                elif value<low or value>high or (c in ('pack_voltage','cell_voltage_max','cell_voltage_min') and value==0):
                    issue(line,'error','plausibility_range',c,'Broad ingestion range exceeded; not a safety threshold')
                t.at[idx,c]=value
            for maxcol,mincol in [('cell_voltage_max','cell_voltage_min'),('temperature_max','temperature_min')]:
                if t.at[idx,maxcol]<t.at[idx,mincol]:issue(line,'error','extrema_inverted',maxcol,'Maximum below minimum')
            if row.charge_status not in ('charging','discharging','idle','unknown'):
                issue(line,'error','invalid_charge_status','charge_status','Unknown enum')
            elif row.charge_status=='unknown':issue(line,'warning','unknown_charge_state','charge_status','Segment classification unavailable')
            mm=m[m.battery_id==b]
            if len(mm)==1 and mm.iloc[0].current_sign_convention in ('discharge_positive','charge_positive'):
                raw_current=t.at[idx,'pack_current'];factor=1 if mm.iloc[0].current_sign_convention=='discharge_positive' else -1
                normalized=raw_current*factor;t.at[idx,'pack_current']=normalized
                if (row.charge_status=='discharging' and normalized<-.5) or (row.charge_status=='charging' and normalized>.5):
                    issue(line,'warning','current_status_mismatch','pack_current','Current sign and state disagree; normalized discharge positive')
            if 'mileage' in t:
                v=pd.to_numeric(row.mileage,errors='coerce')
                if not np.isfinite(v) or v<0:issue(line,'warning','mileage_missing_or_invalid','mileage','Optional analysis unavailable')
        valid_times=t._parsed_time.notna()
        dup=t.loc[valid_times].duplicated(['battery_id','_parsed_time'],keep=False)
        for idx in dup.index[dup]:issue(idx+2,'error','duplicate_timestamp','timestamp','All conflicting duplicate records quarantined')
        for b,g in t[valid_times].groupby('battery_id'):
            times=pd.to_datetime(g._parsed_time,utc=True)
            if not times.is_monotonic_increasing:issue(0,'warning','out_of_order_input','timestamp',str(b)+' input not chronological; accepted output sorted')
            gg=g.assign(_dt=times).sort_values('_dt');deltas=gg._dt.diff().dt.total_seconds()
            for idx in deltas.index[deltas>max_gap_s]:issue(idx+2,'warning','time_gap','timestamp',f'Gap exceeds {max_gap_s} seconds; do not integrate across gap')
        if 'mileage' not in t:issue(0,'warning','mileage_column_absent','mileage','Strongly recommended')
    accepted=t.loc[~t.index.isin(reject)].copy()
    rejected=telemetry.reset_index(drop=True).loc[lambda x:x.index.isin(reject)].copy()
    if '_parsed_time' in accepted:
        accepted['timestamp']=pd.to_datetime(accepted['_parsed_time'],utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        accepted=accepted.sort_values(['battery_id','timestamp']).drop(columns=['_parsed_time'])
    accepted['source_csv_row']=accepted.index+2
    rejected['source_csv_row']=rejected.index+2
    normalized_metadata=m.loc[~m.battery_id.isin(bad_ids)].copy() if 'battery_id' in m else m.copy()
    if 'current_sign_convention' in normalized_metadata:
        normalized_metadata['current_sign_convention']='discharge_positive'
    issue_frame=pd.DataFrame(issues,columns=['csv_row','severity','code','field','detail'])
    errors=int(issue_frame.severity.eq('error').sum());warnings=int(issue_frame.severity.eq('warning').sum())
    summary={'input_rows':len(telemetry),'accepted_rows':len(accepted),'rejected_rows':len(rejected),
        'error_count':errors,'warning_count':warnings,'warnings_need_review':warnings>0,'schema_ready':len(accepted)>0 and errors==0,
        'synthetic_fixture_present':bool(m.get('data_origin',pd.Series(dtype=str)).eq('synthetic_fixture').any()),
        'source_provenance':'Input data_origin declarations are not independent verification',
        'output_current_convention':'discharge_positive','output_time':'UTC with explicit Z',
        'model_inference_performed':False,'scope':'Core telemetry + metadata only; full cell/probe/events tables not validated in V0.2',
        'interpretation':'Data quality screening only; not a battery safety pass or vehicle SOH/RUL validation'}
    return {'accepted':accepted,'rejected':rejected,'issues':issue_frame,'normalized_metadata':normalized_metadata,'summary':summary}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--telemetry',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--max-gap-s',type=float,default=30)
    a=p.parse_args();r=validate(pd.read_csv(a.telemetry,dtype={'battery_id':str}),pd.read_csv(a.metadata,dtype={'battery_id':str}),a.max_gap_s)
    r['summary']['input_sha256']={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.telemetry,a.metadata]}
    a.output.mkdir(parents=True,exist_ok=True)
    for key in ['accepted','rejected','issues','normalized_metadata']:r[key].to_csv(a.output/f'{key}.csv',index=False,encoding='utf-8-sig')
    (a.output/'summary.json').write_text(json.dumps(r['summary'],indent=2),encoding='utf-8')
    print(json.dumps(r['summary'],indent=2))
    return 0 if r['summary']['schema_ready'] else 2

if __name__=='__main__':raise SystemExit(main())
