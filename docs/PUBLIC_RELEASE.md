# Public release checklist

Before publishing a release:

1. Run `./tests/regression.sh`.
2. Run `./tests/public_release.sh`.
3. Update `VERSION`, `CHANGELOG.md`, and `RELEASE_NOTES.md`.
4. Run `./scripts/package_release.sh`.
5. Verify the generated SHA-256 checksum.
6. Publish the code archive, checksum, and release notes.
7. Never upload a live database, export file, API token, user journal, or agent transcript containing personal data.

## Repository hygiene

Do not commit:

- `*.db`, `*.db-wal`, `*.db-shm`
- exported wellness JSON
- API tokens
- user-specific prompt paths
- real chat IDs, names, meals, weights, notes, or other personal records

## Donation setup

Donation links are intentionally not hard-coded. Repository maintainers can add GitHub Sponsors, Ko-fi, or another donation provider after creating their own account. Keep donations optional and separate from medical or outcome claims.
