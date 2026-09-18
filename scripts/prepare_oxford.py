"""Oxford C1dc adapter. Raw data retained; no fabricated vehicle/BMS fields or measured current."""
import gzip, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT=Path(__file__).resolve().parents[1]
RATED_AH=.740
FEATURES=['cycle','voltage_60s_v','voltage_120s_v','voltage_300s_v','voltage_600s_v','voltage_mean_v','voltage_slope_v_per_s','temperature_mean_c','temperature_rise_c']

def relative_seconds(t):
    t=np.asarray(t,dtype=float).reshape(-1)
    if len(t)<2 or not np.isfinite(t[0]) or not 700000<t[0]<800000:
        raise ValueError('Expected observed MATLAB serial-day format; inspect new source version')
    return (t-t[0])*86400.

def capacity_ah(q):
    q=np.asarray(q,dtype=float).reshape(-1)
    if len(q)<2 or not np.isfinite(q[[0,-1]]).all():raise ValueError('Invalid capacity endpoints')
    value=(q[0]-q[-1])/1000.
    if not 0<value<1.5:raise ValueError('Invalid C1dc sign or capacity')
    return float(value)

def voltage_temperature_features(t,v,temp):
    a=np.column_stack([t,v,temp]);a=a[np.isfinite(a).all(axis=1)&(a[:,0]>=0)&(a[:,0]<=600)]
    a=a[np.argsort(a[:,0],kind='stable')];a=a[np.unique(a[:,0],return_index=True)[1]]
    if len(a)<3 or a[0,0]>30 or a[-1,0]<570 or np.diff(a[:,0]).max()>60:raise ValueError('Insufficient 600s coverage')
    grid=np.arange(60.,601.,10.);v,temp=[np.interp(grid,a[:,0],a[:,i]) for i in [1,2]]
    return dict(zip(FEATURES[1:],[float(v[0]),float(v[6]),float(v[24]),float(v[-1]),float(v.mean()),float(np.polyfit(grid,v,1)[0]),float(temp.mean()),float(temp[-1]-temp[0])]))

def threshold_interval(cycles,capacities,threshold=.8*RATED_AH):
    pairs=sorted(zip(cycles,capacities));prior=None
    for c,q in pairs:
        if q<=threshold:return prior,int(c),False
        prior=int(c)
    return prior,None,True

def main():
    raw=ROOT/'data/raw/oxford';dest=ROOT/'data/processed/oxford';dest.mkdir(parents=True,exist_ok=True)
    timeseries=raw/'processed_timeseries';timeseries.mkdir(exist_ok=True)
    mat=loadmat(raw/'Oxford_Battery_Degradation_Dataset_1.mat',simplify_cells=True)
    rows=[];issues=[];counts={};phases={}
    for cell in sorted(k for k in mat if not k.startswith('__')):
        output=timeseries/f'{cell}_C1dc.csv.gz';count=0
        with gzip.open(output,'wt',encoding='utf8',newline='') as stream:
            for key,record in sorted(mat[cell].items(),key=lambda x:int(x[0][3:])):
                for phase in record:phases[phase]=phases.get(phase,0)+1
                if 'C1dc' not in record:issues.append({'battery_id':cell,'cycle':int(key[3:]),'issue':'missing_C1dc','count':1});continue
                cycle=int(key[3:]);d=record['C1dc'];arrays={k:np.asarray(d[k],dtype=float).reshape(-1) for k in ['t','v','q','T']}
                if len({len(x) for x in arrays.values()})!=1:raise ValueError(f'{cell}/{key}: unequal lengths')
                t=relative_seconds(arrays['t']);ts=pd.DataFrame({'time_s':t,'voltage_v':arrays['v'],'charge_mah':arrays['q'],'temperature_c':arrays['T'],'source_time_matlab_days':arrays['t']})
                bad=~np.isfinite(ts).all(axis=1)|(ts.time_s<0)
                if bad.any():issues.append({'battery_id':cell,'cycle':cycle,'issue':'nonfinite_or_negative_time_removed','count':int(bad.sum())})
                ts=ts[~bad].sort_values('time_s',kind='stable');dupes=int(ts.time_s.duplicated().sum())
                if dupes:issues.append({'battery_id':cell,'cycle':cycle,'issue':'duplicate_time_keep_first','count':dupes})
                ts=ts.drop_duplicates('time_s',keep='first')
                q=capacity_ah(arrays['q']);features={};reason=''
                try:features=voltage_temperature_features(ts.time_s.to_numpy(),ts.voltage_v.to_numpy(),ts.temperature_c.to_numpy())
                except ValueError as e:reason=str(e);issues.append({'battery_id':cell,'cycle':cycle,'issue':reason,'count':1})
                rows.append({'dataset_id':'oxford_degradation_1','battery_id':cell,'cycle':cycle,'source_cycle_key':key,'phase':'C1dc','capacity_ah':q,'rated_capacity_ah':RATED_AH,'soh_pct':q/RATED_AH*100,'sample_count':len(ts),'discharge_duration_s':float(ts.time_s.max()),'feature_eligible':not reason,'exclusion_reason':reason,**features})
                ts.insert(0,'battery_id',cell);ts.insert(1,'cycle',cycle);ts.to_csv(stream,index=False,header=count==0,float_format='%.10g');count+=len(ts)
        counts[cell]=count
        print('processed',cell,len(mat[cell]),count,flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(dest/'cycles.csv',index=False)
    summaries=[]
    for cell,g in frame.groupby('battery_id'):
        low,high,censored=threshold_interval(g.cycle,g.capacity_ah)
        summaries.append({'battery_id':cell,'characterisation_records':len(g),'first_capacity_ah':g.capacity_ah.iloc[0],'last_capacity_ah':g.capacity_ah.iloc[-1],'last_observed_drive_cycle':int(g.cycle.max()),'illustrative_threshold_ah':.592,'threshold_crossing_lower_exclusive':low,'threshold_crossing_upper_inclusive':high,'right_censored':censored})
    pd.DataFrame(summaries).to_csv(dest/'battery_summary.csv',index=False)
    pd.DataFrame(issues,columns=['battery_id','cycle','issue','count']).to_csv(dest/'cleaning_issues.csv',index=False)
    quality={'battery_count':len(counts),'cycle_rows':len(frame),'timeseries_rows':sum(counts.values()),'timeseries_rows_by_cell':counts,'raw_phase_record_counts':phases,'feature_eligible_rows':int(frame.feature_eligible.sum()),'cleaning_issue_entries':len(issues),'time_conversion':'Observed raw t is MATLAB serial days, despite README seconds: (t-t0)*86400; original values retained','current':'Not observed in characterisation file; not fabricated or used as feature','capacity':'-(q_last-q_first)/1000 Ah; C1dc q is signed accumulated mAh','soh_denominator_ah':RATED_AH,'rul':'No exact EOL/RUL labels: diagnostic observations are sparse, retain crossing interval at illustrative 80% rated threshold','split':'Cell1..Cell6 training, Cell7/Cell8 untouched test; no random row splitting','trained_model_integrated_in_api':False}
    (dest/'data_quality.json').write_text(json.dumps(quality,indent=2),encoding='utf8')
    print(json.dumps(quality,indent=2),flush=True)

if __name__=='__main__':main()
