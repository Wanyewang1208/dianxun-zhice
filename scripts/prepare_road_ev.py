"""Quality-check 20 public on-road charging files and derive explicitly unvalidated capacity proxies."""
import json, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
COLUMNS=['source_row','record_time','soc','pack_voltage_v','charge_current_a','max_cell_voltage_v','min_cell_voltage_v','max_temperature_c','min_temperature_c','available_energy_source_kw','available_capacity_source_ah']

def session_proxy(t,current,soc):
    t=np.asarray(t,dtype=float);current=np.asarray(current,dtype=float);soc=np.asarray(soc,dtype=float)
    if not(len(t)==len(current)==len(soc)) or len(t)<100:return None,'too_short'
    if not np.isfinite(np.column_stack([t,current,soc])).all():return None,'nonfinite'
    if np.any(np.diff(t)<=0) or np.any(np.diff(t)>10):return None,'time_gap'
    if np.any(current>0):return None,'noncharging_sign'
    if np.any(np.diff(soc)<-.1) or np.any(np.diff(soc)>2):return None,'soc_jump_or_reversal'
    delta=soc[-1]-soc[0]
    if delta<20:return None,'soc_span_below_20pp'
    value=float(-np.sum((current[:-1]+current[1:])*.5*np.diff(t))/3600/delta*100)
    return (value,'accepted_proxy') if value>0 else (None,'nonpositive_proxy')

def main():
    raw=ROOT/'data/raw/road_ev';extract=raw/'extracted';extract.mkdir(exist_ok=True)
    dest=ROOT/'data/processed/road_ev';dest.mkdir(parents=True,exist_ok=True)
    normalized=raw/'normalized';normalized.mkdir(exist_ok=True)
    rows=[];summaries=[]
    for n in range(1,21):
        archive=raw/f'#{n}.rar';expected=f'#{n}.csv';file=extract/expected
        members=subprocess.check_output(['tar','-tf',str(archive)],text=True).splitlines()
        if members != [expected]:raise ValueError(f'Unexpected archive members: {members}')
        if not file.exists():subprocess.run(['tar','-xf',str(archive),'-C',str(extract)],check=True)
        frame=pd.read_csv(file);assert len(frame.columns)==len(COLUMNS);original_columns=list(frame.columns);frame.columns=COLUMNS
        frame['timestamp']=pd.to_datetime(frame.record_time.astype(str),format='%Y%m%d%H%M%S',errors='coerce')
        numeric=frame[COLUMNS[2:]].apply(pd.to_numeric,errors='coerce');frame[COLUMNS[2:]]=numeric
        # Preserve every source row in raw CSV. Invalid rows are excluded only from normalized analysis.
        invalid=frame.timestamp.isna()|~np.isfinite(numeric).all(axis=1)|~frame.soc.between(0,100)|~frame.pack_voltage_v.between(0,2000,inclusive='neither')|(frame.max_cell_voltage_v<frame.min_cell_voltage_v)|(frame.max_temperature_c<frame.min_temperature_c)
        good=frame[~invalid].sort_values('timestamp',kind='stable').copy();dupe=good.timestamp.duplicated(keep=False);duplicates=int(dupe.sum());good=good[~dupe].copy()
        secs=(good.timestamp-good.timestamp.iloc[0]).dt.total_seconds();delta=secs.diff();segment=((delta>10)|(delta<=0)).cumsum()
        good.insert(0,'battery_id',f'ROAD_EV_{n:02d}');good['session_id']=segment.to_numpy()
        for sid,g in good.groupby('session_id',sort=False):
            t=(g.timestamp-g.timestamp.iloc[0]).dt.total_seconds().to_numpy();value,status=session_proxy(t,g.charge_current_a,g.soc)
            rows.append({'battery_id':f'ROAD_EV_{n:02d}','session_id':int(sid),'start_time':str(g.timestamp.iloc[0]),'end_time':str(g.timestamp.iloc[-1]),'rows':len(g),'soc_start_pct':float(g.soc.iloc[0]),'soc_end_pct':float(g.soc.iloc[-1]),'capacity_proxy_ah':value,'status':status,'label_type':'current_integral_divided_by_soc_change_not_independent_capacity_test'})
        good.to_csv(normalized/f'ROAD_EV_{n:02d}.csv.gz',index=False,compression={'method':'gzip','compresslevel':1,'mtime':0})
        summary={'battery_id':f'ROAD_EV_{n:02d}','raw_rows':len(frame),'invalid_rows':int(invalid.sum()),'duplicate_timestamp_rows_quarantined':duplicates,'normalized_rows':len(good),'start_time':str(good.timestamp.min()),'end_time':str(good.timestamp.max()),'sessions':int(segment.nunique()),'source_columns':original_columns}
        summaries.append(summary);print('processed',n,len(frame),len(good),flush=True)
    sessions=pd.DataFrame(rows);sessions.to_csv(dest/'charging_sessions.csv',index=False)
    pd.DataFrame([{k:v for k,v in s.items() if k!='source_columns'} for s in summaries]).to_csv(dest/'vehicle_summary.csv',index=False)
    quality={'vehicle_count':20,'raw_rows':sum(s['raw_rows'] for s in summaries),'normalized_rows':sum(s['normalized_rows'] for s in summaries),'invalid_rows':sum(s['invalid_rows'] for s in summaries),'duplicate_timestamp_rows_quarantined':sum(s['duplicate_timestamp_rows_quarantined'] for s in summaries),'session_count':len(sessions),'capacity_proxy_sessions':int(sessions.capacity_proxy_ah.notna().sum()),'status_counts':sessions.status.value_counts().to_dict(),'vehicles':summaries,'timestamp_timezone':'Not specified; preserved as source-local, never labelled UTC','proxy_method':'Negative charging-current trapezoid integral Ah / delta SOC *100; >=100 rows, >=20pp SOC span, <=10s gaps, no positive current or SOC reversal >0.1pp / jump >2pp','method_relation':'Author formula retained, stricter explicit quality filters; not exact reproduction of author statistical labels','available_energy_source_kw':'Source header says kw; ambiguous; not renamed kWh or used for energy/health labels','ground_truth':'No independent measured capacity labels established; no rated Ah denominator confirmed; no SOH/RUL accuracy claim','team_collected':False,'api_changed':False}
    (dest/'data_quality.json').write_text(json.dumps(quality,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps({k:v for k,v in quality.items() if k!='vehicles'},indent=2))

if __name__=='__main__':main()
