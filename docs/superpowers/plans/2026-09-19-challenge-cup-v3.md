# Challenge Cup V3 execution plan

Goal: re-extract and audit raw data, reproduce frozen V2 experiments, verify artifacts, deliver academic evidence and sync only the new research branch.
Spec: research/public_battery/V3_PROTOCOL.md and user supplied sections 1-15 plus expanded GitHub section 14.

- [x] Record protected remote refs; create isolated worktree from 2f49614.
- [x] Read-only audit 20 CSV/archive hashes, re-extract and compare V2, generate anonymous public data and field dictionaries.
- [x] Train all frozen configurations and five group folds with V2 dependency versions; save primary models and CV predictions.
- [x] Independently recompute every metric and model reload prediction; run 12 research tests and full suite; compare V2 at specified tolerances.
- [x] Generate ten PNG/SVG/CSV figures and two DOCX reports; render and inspect every page; scan consistency.
- [x] Audit permission/privacy, configure path-specific LFS, generate manifest/hash evidence ZIP.
- [ ] Commit/push only experiment/challenge-cup-evidence-v3; create non-overwriting annotated tag; verify remote branch, tag, LFS objects and protected refs.

Constraints: no main/dev/V2 modifications, no PR/merge/force push. No private identifiers, secrets or machine-specific paths in new public artifacts. Source archive data is read only.
Review focus: invalid timestamps cannot bridge sessions; entity splits remain disjoint; preprocessing fits train only; metrics independently match predictions; publication scans include DOCX/ZIP content and LFS verification.
