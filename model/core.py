"""Causal predictors, cell separation, and dataset-specific EOL conventions."""
import numpy as np

RATED_CAPACITY_AH = 2.0
EOL_CAPACITY_AH = 1.4
CELL_IDS = ['B0005', 'B0006', 'B0007', 'B0018']
TRAIN_IDS = ['B0005', 'B0006', 'B0007']
TEST_IDS = ['B0018']
FEATURES = ['cycle', 'voltage_60s_v', 'voltage_120s_v', 'voltage_300s_v',
            'voltage_600s_v', 'voltage_mean_v', 'voltage_slope_v_per_s',
            'current_mean_a', 'current_std_a', 'temperature_mean_c',
            'temperature_rise_c', 'ambient_temperature_c']

def assert_disjoint(train_ids, test_ids):
    if set(train_ids) & set(test_ids):
        raise ValueError('Battery IDs overlap between train and test')
    if not train_ids or not test_ids:
        raise ValueError('Both training and testing IDs are required')

def early_features(data):
    """Use only t<=600 s. Last endpoint uses last observed value, never a future sample.

    An experiment-start window (not normalized to full discharge length) is used.
    Interpolate on a fixed 60..600 second grid; permit <=30 s endpoint hold.
    """
    names = ['Time','Voltage_measured','Current_measured','Temperature_measured']
    arrays = [np.asarray(data[n],dtype=float).reshape(-1) for n in names]
    if len({len(x) for x in arrays}) != 1:
        raise ValueError('Unequal signal lengths')
    a=np.column_stack(arrays)
    a=a[np.isfinite(a).all(axis=1) & (a[:,0]>=0) & (a[:,0]<=600)]
    a=a[np.argsort(a[:,0],kind='stable')]
    if len(a)<3: raise ValueError('Too few finite early samples')
    _,ix=np.unique(a[:,0],return_index=True)
    a=a[ix]
    t=a[:,0]
    if t[0]>30 or t[-1]<570 or np.max(np.diff(t))>60:
        raise ValueError('Insufficient early-window coverage or gap >60 seconds')
    grid=np.arange(60.,601.,10.)
    v,i,temp=[np.interp(grid,t,a[:,j]) for j in (1,2,3)]
    return {'voltage_60s_v':float(v[0]), 'voltage_120s_v':float(v[6]),
            'voltage_300s_v':float(v[24]), 'voltage_600s_v':float(v[-1]),
            'voltage_mean_v':float(v.mean()),
            'voltage_slope_v_per_s':float(np.polyfit(grid,v,1)[0]),
            'current_mean_a':float(i.mean()), 'current_std_a':float(i.std()),
            'temperature_mean_c':float(temp.mean()),
            'temperature_rise_c':float(temp[-1]-temp[0])}

def eol_cycle(cycles, capacities, threshold=EOL_CAPACITY_AH):
    c=np.asarray(cycles,dtype=float); q=np.asarray(capacities,dtype=float)
    idx=np.isfinite(q) & (q<=threshold)
    return int(np.min(c[idx])) if np.any(idx) else None

def estimate_rul(cycles, capacities, window=30, threshold=EOL_CAPACITY_AH):
    """Rolling observed-capacity trend; caller supplies ONLY prefix available now.

    This is a diagnostic-capacity baseline, not an end-to-end BMS RUL model.
    Flat/nondegrading trends abstain. No arbitrary lifetime cap or future smoothing.
    """
    c=np.asarray(cycles,dtype=float); q=np.asarray(capacities,dtype=float)
    mask=np.isfinite(c)&np.isfinite(q); c=c[mask]; q=q[mask]
    if len(c)<window:
        return {'predicted_rul_cycles':None,'status':'insufficient_history','slope_ah_per_cycle':None}
    if q[-1]<=threshold:
        return {'predicted_rul_cycles':0.,'status':'already_at_threshold','slope_ah_per_cycle':None}
    slope,intercept=np.polyfit(c[-window:],q[-window:],1)
    if slope>=-1e-8:
        return {'predicted_rul_cycles':None,'status':'nondegrading_trend','slope_ah_per_cycle':float(slope)}
    value=max(0.,float((threshold-intercept)/slope-c[-1]))
    return {'predicted_rul_cycles':value,'status':'estimated','slope_ah_per_cycle':float(slope)}
