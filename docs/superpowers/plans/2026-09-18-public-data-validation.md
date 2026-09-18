# Public battery data validation implementation plan

Goal: test accessible user-provided public datasets, run reproducible entity-isolated experiments, and synchronize evidence to GitHub without representing estimated labels as measured ground truth.

Architecture: independent research pipeline under research/public_battery; existing production NASA/manual inference remains unchanged. Raw downloads stay outside Git. Commit small provenance records, audit summaries, feature definitions, predictions, metrics and reproducible scripts.

- [x] Merge reviewed BMS/translation fixes PR 4 into dev.
- [x] Verify IVST, Iontech-linked primary dataset, Oxford accessibility and license; record exact URLs, revisions and SHA256.
- [x] Inspect schemas, timestamps, units, identities, label construction and missing fields. Test actual data against existing BMS checker without inventing metadata.
- [x] Derive charging-session capacity proxy labels with explicit integration/SOC filters. Never label these as laboratory-measured SOH. Exclude target-derived features.
- [x] Compare train-mean, ridge and random-forest baselines; hold out entire vehicles in predetermined split, no row-wise leakage; save all candidates, no model cherry-picking.
- [x] Where Oxford is accessible, run a separately scoped cell experiment; otherwise record specific blocker without fabricated results.
- [x] Verify pipeline logic, outputs, baseline app tests, review evidence; publish code/records and reviewable results to repository.

Experiment boundary: regression against SOC/Ah-derived capacity is proxy agreement only. No safety/RUL validity follows from it. No raw large/private identifiers are committed.
