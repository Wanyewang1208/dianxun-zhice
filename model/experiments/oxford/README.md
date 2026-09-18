# Oxford research models

Research only; production API is unchanged. Regenerate with `python scripts/benchmark_oxford.py`. Train: Cell1–Cell6; test: Cell7–Cell8. Features use only the first 600 seconds of C1dc voltage/temperature and cycle count. Capacity and full discharge duration are excluded from inputs.

Models are trusted local joblib artifacts; do not load untrusted pickle/joblib files. Source dataset and derived tables retain Oxford ODbL-1.0 / DbCL-1.0 notices under data/source_notes/oxford. See docs/EXTERNAL_DATA_INTAKE.md and data/demo/results/oxford/experiment.json for results and limitations. These models are not calibrated for vehicle packs.
