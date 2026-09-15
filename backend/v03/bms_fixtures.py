"""Generate plainly-labelled software test fixtures, NOT measured vehicle data."""
from pathlib import Path
import pandas as pd

def create(root):
    out=root/'data/sample/bms/synthetic_fixtures';out.mkdir(exist_ok=True)
    m=pd.DataFrame([{'battery_id':'SYNTHETIC_PACK_001','battery_chemistry':'LFP','rated_capacity_ah':100,
        'current_sign_convention':'discharge_positive','voltage_unit':'V','current_unit':'A',
        'temperature_unit':'degC','soc_unit':'%','data_origin':'synthetic_fixture'}])
    rows=[]
    for i in range(12):
        rows.append({'battery_id':'SYNTHETIC_PACK_001',
            'timestamp':(pd.Timestamp('2026-01-01T00:00:00+08:00')+pd.Timedelta(seconds=i*10)).isoformat(),
            'pack_voltage':320-i*.1,'pack_current':10.,'SOC':60-i*.01,
            'cell_voltage_max':3.4,'cell_voltage_min':3.3,'temperature_max':30,'temperature_min':25,
            'charge_status':'discharging','mileage':100+i*.01})
    good=pd.DataFrame(rows)
    bad=pd.concat([good,good.iloc[[0]]],ignore_index=True)
    bad.loc[2,'SOC']=140;bad.loc[3,'timestamp']='2026-01-01T00:00:30'
    bad.loc[4,'cell_voltage_min']=3.5
    bad['pack_current']=bad.pack_current.astype(str);bad.loc[5,'pack_current']='missing'
    bad.loc[9,'pack_current']='-10';bad.loc[11,'timestamp']='2026-01-01T00:05:00+08:00'
    for name,df in [('metadata',m),('good_telemetry',good),('bad_telemetry',bad)]:
        df.to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    (root/'data/sample/bms/metadata_v02_template.csv').write_text(','.join(m.columns)+'\n',encoding='utf-8-sig')
    print('Created synthetic-only fixtures: 12 clean rows; 13 rows with 6 intentionally invalid rows')

if __name__=='__main__':create(Path(__file__).resolve().parents[2])
