"""Decode NASA discharge operations without fabricating missing BMS fields."""
import json
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat
from .core import CELL_IDS,early_features,RATED_CAPACITY_AH,EOL_CAPACITY_AH,eol_cycle

def prepare(root):
    dest=root/'data/processed'; dest.mkdir(parents=True,exist_ok=True)
    rows=[]; series=[]; issues=[]; counts=[]
    for battery in CELL_IDS:
        cycles=loadmat(root/f'data/raw/{battery}.mat',simplify_cells=True)[battery]['cycle']
        k=0; operation_counts={}
        for operation_index,c in enumerate(cycles,1):
            kind=c['type']; operation_counts[kind]=operation_counts.get(kind,0)+1
            if kind!='discharge': continue
            k+=1; d=c['data']
            start=c['time']; dt=datetime(*[int(x) for x in start[:5]])+timedelta(seconds=float(start[5]))
            capacity=float(d['Capacity'])
            arrays={dest_name:np.asarray(d[source_name],dtype=float).reshape(-1)
                    for source_name,dest_name in [('Time','time_s'),('Voltage_measured','voltage_v'),
                    ('Current_measured','current_a'),('Temperature_measured','temperature_c')]}
            if len({len(v) for v in arrays.values()})!=1:
                issues.append({'battery_id':battery,'cycle':k,'issue':'signal_length_mismatch','count':1})
                continue
            ts=pd.DataFrame(arrays)
            for name in ['time_s','voltage_v','current_a','temperature_c']:
                bad=int((~np.isfinite(ts[name])).sum())
                if bad: issues.append({'battery_id':battery,'cycle':k,'issue':'nonfinite_'+name,'count':bad})
            invalid=(~np.isfinite(ts).all(axis=1))|(ts.time_s<0)
            ts=ts.loc[~invalid].sort_values('time_s',kind='stable')
            dupe=int(ts.time_s.duplicated().sum())
            if dupe: issues.append({'battery_id':battery,'cycle':k,'issue':'duplicate_time_keep_first','count':dupe})
            ts=ts.drop_duplicates('time_s',keep='first')
            ts.insert(0,'battery_id',battery); ts.insert(1,'cycle',k)
            ts.insert(2,'operation_index',operation_index)
            ts.insert(3,'cycle_start_time',dt.isoformat(timespec='milliseconds'))
            series.append(ts)
            usable=True; reason=''
            try:
                feat=early_features(d)
            except ValueError as e:
                usable=False; reason=str(e); feat={}
                issues.append({'battery_id':battery,'cycle':k,'issue':reason,'count':1})
            if not np.isfinite(capacity) or not 0<capacity<3:
                usable=False; reason='invalid_capacity'
                issues.append({'battery_id':battery,'cycle':k,'issue':reason,'count':1})
            rows.append({'battery_id':battery,'cycle':k,'operation_index':operation_index,
                         'cycle_start_time':dt.isoformat(timespec='milliseconds'),
                         'capacity_ah':capacity,'rated_capacity_ah':RATED_CAPACITY_AH,
                         'soh_pct':capacity/RATED_CAPACITY_AH*100,
                         'ambient_temperature_c':float(c['ambient_temperature']),
                         'sample_count':len(ts),'discharge_duration_s':float(ts.time_s.max()),
                         'feature_eligible':usable,'exclusion_reason':reason,**feat})
        counts.append({'battery_id':battery,**operation_counts})
    frame=pd.DataFrame(rows).sort_values(['battery_id','cycle'])
    signals=pd.concat(series,ignore_index=True)
    assert not frame.duplicated(['battery_id','cycle']).any()
    assert not signals.duplicated(['battery_id','cycle','time_s']).any()
    frame.to_csv(dest/'cycles.csv',index=False,encoding='utf-8-sig')
    signals.to_csv(dest/'discharge_timeseries.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(issues,columns=['battery_id','cycle','issue','count']).to_csv(dest/'cleaning_issues.csv',index=False,encoding='utf-8-sig')
    summary=[]
    for b,g in frame.groupby('battery_id'):
        end=eol_cycle(g.cycle,g.capacity_ah)
        summary.append({'battery_id':b,'discharge_cycles':len(g),'eligible_cycles':int(g.feature_eligible.sum()),
                        'capacity_first_ah':float(g.capacity_ah.iloc[0]),'capacity_last_ah':float(g.capacity_ah.iloc[-1]),
                        'capacity_min_ah':float(g.capacity_ah.min()),'eol_threshold_ah':EOL_CAPACITY_AH,
                        'first_eol_cycle':end,'right_censored':end is None,'last_observed_cycle':int(g.cycle.max())})
    pd.DataFrame(summary).to_csv(dest/'battery_summary.csv',index=False,encoding='utf-8-sig')
    report={'cycle_rows':len(frame),'timeseries_rows':len(signals),'eligible_rows':int(frame.feature_eligible.sum()),
            'excluded_cycles':int((~frame.feature_eligible).sum()),'cleaning_issue_entries':len(issues),
            'operations':counts,'timestamp_timezone':'unspecified in NASA source; not converted to UTC',
            'cycle_definition':'1-based discharge operation index within each battery, not equivalent-full-cycle count',
            'early_window':'t <= 600 s only; grid 60..600 s; last-value hold <=30 s at endpoint'}
    (dest/'data_quality.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    return frame

if __name__=='__main__': prepare(Path(__file__).resolve().parents[2])
