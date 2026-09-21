# Data Manifest

## Files included in the public portfolio repository

### Raw / prepared input

- `raw/pagespeed_input_before.csv`
  - prepared PageSpeed URL/device jobs
  - semicolon-delimited to match the original collection script

### Processed / analytical artifacts

- `processed/pmb_widyatama_crawl_analysis.xlsx`
  - primary analysis workbook
  - includes crawl inventory, PageSpeed input/raw/baseline sheets, dashboard, and root-cause targets

- `processed/root_cause_targets.csv`
  - cleaned target list used by the batch root-cause collector

- `analysis_scope.csv`
  - compact summary of portfolio scope

## Files generated when the analysis pipeline is executed

Examples include:

- `pagespeed_results_before.csv`
- `pagespeed_results_clean.csv`
- `root_cause_batch_runs_before.csv`
- `root_cause_batch_results_before.csv`
- `root_cause_batch_runs_before_repaired.csv`
- `root_cause_batch_results_before_repaired.csv`
- `root_cause_image_repair_qc.csv`
- `root_cause_template_summary_before.csv`
- `root_cause_template_rootcause_matrix_before.csv`
- `template_remediation_priority_before.csv`
- `template_remediation_priority_before_final.csv`
- `remediation_backlog_before.csv`
- `sprint1_page_evidence_before.csv`
- `sprint1_pilot_pages_before.csv`
- `sprint1_pilot_deep_diagnostic_before.csv`
- `sprint1_pilot_resource_evidence_before.csv`
- `sprint1_implementation_spec_before.csv`

## Publishing guidance

- Do not publish `.env`
- Do not publish API keys or login credentials
- Do not publish private institutional data
- Keep public datasets limited to website-analysis evidence suitable for a portfolio
