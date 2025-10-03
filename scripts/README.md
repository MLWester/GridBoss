# Scripts

Automation and utility scripts for GridBoss.

## Demo Seed Data

`seed_demo.py` populates the database with a demo league, events, and sample results. Run it from the repository root:

```powershell
python scripts/seed_demo.py
```

Add `--dry-run` to preview the changes without committing, or `--json` to emit a machine-readable summary.

The script is idempotent - rerunning it updates the existing demo records without creating duplicates.
