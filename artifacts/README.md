# artifacts/

Generated / showcase outputs that are **not** framework source.

```text
artifacts/
└── demo/
    └── output/     # HTML from scripts/demo/ (gitignored; regenerate locally)
```

Regenerate demos:

```powershell
uv run python scripts/demo/run_portfolio_demo.py --full --open
```

See [`scripts/demo/README.md`](../scripts/demo/README.md).
