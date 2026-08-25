# Contributing

1. Preserve existing CLI command names and documented JSON fields.
2. Do not include databases or personal data in commits, fixtures, or release archives.
3. Use only the Python standard library unless a dependency is explicitly approved.
4. Run `python3 -m py_compile tools/*.py` and `./tests/regression.sh` before submitting changes.
5. Update `CHANGELOG.md`, `VERSION`, help metadata, and capabilities together when interfaces change.
