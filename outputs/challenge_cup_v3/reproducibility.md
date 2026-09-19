# V3 复现命令

```sh
python -m venv .venv-v3
# Activate the environment, then:
python -m pip install -r research/public_battery/requirements-v3.lock
git lfs pull
python -m research.public_battery.audit_v3 --self-test
python -m research.public_battery.validation_v3 --source research/public_battery/data/v3/session_features.csv --output research/public_battery/results/v3 --models-dir outputs/challenge_cup_v3/04_models
python -m research.public_battery.verify_v3 --source research/public_battery/data/v3/session_features.csv
python -m research.public_battery.report_v3 --source research/public_battery/data/v3/session_features.csv --output outputs/challenge_cup_v3 --verification outputs/challenge_cup_v3/08_tests_and_verification/verification.json --figures-only
python research/public_battery/report_v3/check_figure_data.py --result research/public_battery/results/v3 --source research/public_battery/data/v3/session_features.csv --output outputs/challenge_cup_v3 --verification outputs/challenge_cup_v3/08_tests_and_verification/verification.json --record
python -m research.public_battery.report_v3 --source research/public_battery/data/v3/session_features.csv --output outputs/challenge_cup_v3 --verification outputs/challenge_cup_v3/08_tests_and_verification/verification.json
# Render and inspect every DOCX page; record documents_pending=false only after inspection.
python -m research.public_battery.package_v3
```
