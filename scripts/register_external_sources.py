"""Build a factual dataset catalogue; linked resources are NOT counted as acquired data."""
import hashlib,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    path=ROOT/'data/raw/source_intake/iontech.txt';text=path.read_text(encoding='utf8')
    matches=list(re.finditer(r'^\s*###\s+(\d+)\.\s*(.+)$',text,re.M));entries=[]
    chosen={40:'downloaded_and_processed',14:'already_have_NASA_subset',7:'candidate_dynamic_lab_profiles',26:'candidate_lifetime_benchmark',32:'candidate_larger_cell_population',44:'candidate_retired_cells_version_needs_review',49:'candidate_second_life_storage'}
    for i,m in enumerate(matches):
        section=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        links=[{'label':a,'url':b} for a,b in re.findall(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',section)]
        entries.append({'index':int(m[1]),'title':m[2].strip(),'links':links,'status':chosen.get(int(m[1]),'catalogued_not_downloaded'),'license':'verify_original_publisher_before_use'})
    dest=ROOT/'data/source_notes';dest.mkdir(exist_ok=True)
    record={'catalogue_url':'https://github.com/shiyunliu-battery/Iontech','retrieved_date':'2026-09-18','snapshot_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'entry_count':len(entries),'catalogue_is_not_a_dataset':True,'entries':entries}
    (dest/'iontech_catalogue.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    registry={'updated':'2026-09-18','sources':[
      {'id':'ivst_300_ev','url':'https://ivstskl.changan.com.cn/?p=2697','status':'awaiting_user_application','acquired_vehicles':0,'publisher_advertised_vehicles':300,'sample_application_url':'https://ivstskl.changan.com.cn/?p=2799','full_application_url':'https://ivstskl.changan.com.cn/?p=3152','terms_url':'https://ivstskl.changan.com.cn/?p=2758','license_note':'Academic use; special terms prohibit unauthorized redistribution and external services. No application submitted and no personal information invented.'},
      {'id':'iontech','url':'https://github.com/shiyunliu-battery/Iontech','status':'catalogued','entries':len(entries),'acquired_entities':None,'note':'Do not count catalogue entries as acquired batteries; selected original source #40 separately recorded.'},
      {'id':'oxford_degradation_1','url':'https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac','status':'downloaded_processed_experimented','acquired_cells':8,'characterisation_discharge_records':519,'raw_path':'data/raw/oxford','processed_path':'data/processed/oxford','results_path':'data/demo/results/oxford','license':'ODbL-1.0 / DbCL-1.0; retain author notices'},
      {'id':'road_ev_20','url':'https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles','discovered_via':'Iontech entry 40','status':'downloaded_processed_capacity_proxy_experiment','acquired_vehicle_archives':20,'team_collected':False,'raw_path':'data/raw/road_ev','processed_path':'data/processed/road_ev','license_note':'Original repository includes MIT LICENSE; retain original notice and required paper citation; capacity labels are algorithmic proxies, not independent reference tests.'}
    ]}
    (dest/'external_sources.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2),encoding='utf8')
    print('registered',len(entries),'Iontech entries and 4 source records')
if __name__=='__main__':main()
