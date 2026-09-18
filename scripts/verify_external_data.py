"""Verify saved external-data provenance, counts and research model reproducibility."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
ROOT=Path(__file__).resolve().parents[1]
def main():
    checked=0
    for source in ['oxford','road_ev']:
        manifest=json.loads((ROOT/f'data/source_notes/{source}/provenance.json').read_text(encoding='utf8'))
        for entry in manifest['files']:
            path=ROOT/f'data/raw/{source}'/entry['file']
            assert path.stat().st_size==entry['bytes'],str(path)
            with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
            assert digest==entry['sha256'],str(path)
            checked+=1
    road=ROOT/'data/processed/road_ev'
    q=json.loads((road/'data_quality.json').read_text(encoding='utf8'))
    sessions=pd.read_csv(road/'charging_sessions.csv');vehicles=pd.read_csv(road/'vehicle_summary.csv')
    assert len(vehicles)==q['vehicle_count']==20
    assert len(sessions)==q['session_count']
    assert int(sessions.rows.sum())==int(vehicles.normalized_rows.sum())==q['normalized_rows']
    assert q['raw_rows']==q['normalized_rows']+q['invalid_rows']+q['duplicate_timestamp_rows_quarantined']
    assert int(sessions.capacity_proxy_ah.notna().sum())==q['capacity_proxy_sessions']
    assert len(list((ROOT/'data/raw/road_ev/normalized').glob('*.csv.gz')))==20
    cells=pd.read_csv(ROOT/'data/processed/oxford/cycles.csv')
    assert cells.battery_id.nunique()==8 and len(cells)==519
    predictions=pd.read_csv(ROOT/'data/demo/results/oxford/holdout_predictions.csv')
    for path in (ROOT/'model/experiments/oxford').glob('*.joblib'):
        saved=joblib.load(path)
        assert not set(saved['train_ids'])&set(saved['test_ids'])
        test=cells[cells.battery_id.isin(saved['test_ids']) & cells.feature_eligible]
        p=saved['model'].predict(test[saved['features']])
        expected=predictions[predictions.model==path.stem]
        assert list(zip(test.battery_id,test.cycle))==list(zip(expected.battery_id,expected.cycle))
        np.testing.assert_allclose(p,expected.predicted_soh_pct,rtol=1e-10)
    print(json.dumps({'verified_raw_files':checked,'road_vehicles':20,'road_rows':q['normalized_rows'],'oxford_cells':8,'oxford_records':len(cells),'saved_models_reproduced':4,'capacity_proxy_range_ah':sessions.capacity_proxy_ah.agg(['min','median','max']).to_dict()},indent=2))
if __name__=='__main__':main()
