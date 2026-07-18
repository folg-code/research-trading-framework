# Local AWS runbook (gitignored content)

Local PowerShell/config smoke scripts for AWS dry-run operators live **here**:

```text
deploy/local_aws_runbook/
```

This directory supersedes the former root `local_aws_runbook/` path (ADR-0022 /
Sprint 029).

## Tracking policy

- This `README.md` is tracked.
- Script/config payloads remain **gitignored** (credentials, machine-local
  overrides, smoke outputs).
- Shared container definitions stay under `deploy/aws/` (and dashboard deploy
  under `apps/dashboard/deploy/`).

## Migration

If you still have a root `local_aws_runbook/` folder, move its contents here and
delete the old directory.
