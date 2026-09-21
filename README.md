# Widyatama Website Performance Analysis

**From 119 URLs to an Actionable Website Performance Remediation Strategy**

Portfolio project focused on the public admission website of Universitas Widyatama:

**Target:** https://pmb.widyatama.ac.id/

## Project status

This public portfolio release intentionally stops at the **analysis + dashboard** stage.

It covers:

- website crawl and URL inventory
- page-level performance diagnostics
- PageSpeed / Core Web Vitals analysis
- technical SEO review
- template and resource analysis
- root-cause investigation
- remediation prioritization
- dashboard communication

Implementation and production remediation are intentionally outside the scope of this repository version.

## Verified project scope

| Metric | Value |
|---|---:|
| Internal URLs discovered during crawl | 627 |
| Internal HTML URLs retained for audit | 119 |
| PageSpeed API test rows | 174 |
| Pages in PageSpeed baseline analysis | 87 |
| Pages smoke-tested | 43 |

> The counts above summarize different analysis stages and should not be interpreted as the same population.

## Analysis pipeline

`Website → Screaming Frog → Page-Level Data → Performance Diagnostic → Root Cause Analysis → Template Analysis → Prioritization → Remediation Backlog → Dashboard`

## Dashboard

Open `docs/index.html` locally or publish the `/docs` folder with GitHub Pages.

Dashboard sections:

1. Overview
2. Performance
3. SEO
4. Templates
5. Resources

## Repository structure

```text
widyatama-website-performance-analysis/
├── README.md
├── GITHUB_SETUP.md
├── NOTICE.md
├── data/
│   ├── analysis_scope.csv
│   └── DATA_MANIFEST.md
├── docs/
│   └── index.html
├── assets/
│   ├── dashboard-overview.png
│   └── linkedin-cover.png
└── linkedin/
    ├── linkedin-post.md
    ├── linkedin-project-entry.md
    └── upload-checklist.md
```

## What this project demonstrates

- converting a large website crawl into a manageable analytical scope
- structuring performance and technical SEO evidence
- separating symptoms from probable root causes
- prioritizing remediation based on impact and repeatability
- communicating technical findings through an executive-style dashboard
- documenting an end-to-end analysis workflow for reproducibility

## Important note about the raw working files

The original working CSV/XLSX files from the analysis are not duplicated in this export because they are not available in the current chat workspace.

`data/DATA_MANIFEST.md` lists the working files that can be added back to the repository if you still have them locally.

## Suggested GitHub topics

`data-analysis` `web-performance` `technical-seo` `pagespeed` `core-web-vitals` `tableau` `website-audit` `portfolio-project`

## Portfolio framing

This repository is best presented as a **Data Analyst / Web Performance Analysis** case study rather than as a completed production optimization project.

The analytical deliverable is the endpoint: the value comes from turning fragmented website evidence into a structured, prioritized, decision-ready dashboard.


## Reproducibility and source scripts

The repository includes the Python scripts used for the analytical workflow under [`scripts/`](scripts/).

The main public inputs included are:

- `data/raw/pagespeed_input_before.csv`
- `data/processed/root_cause_targets.csv`
- `data/processed/pmb_widyatama_crawl_analysis.xlsx`

The code covers PageSpeed collection, Lighthouse/root-cause diagnostics, image-savings QC, template-level aggregation, priority scoring, remediation backlog construction, and Sprint-1 pilot diagnostics.

See [`scripts/README.md`](scripts/README.md) for the recommended execution order.

### Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate       # Windows

python -m pip install -r requirements.txt
cp .env.example .env
```

Then set `PAGESPEED_API_KEY` inside `.env`.

> `.env`, runtime logs, virtual environments, and `node_modules` are excluded from Git by `.gitignore`.
