# Contributing to Weight Tracker

Contributions, bug fixes, documentation improvements, and installation reports are welcome.

Weight Tracker handles private wellness information, so protecting user data and maintaining compatibility are priorities.

## Before Making Changes

Please open a GitHub Issue for significant changes before beginning major work. Small bug fixes and documentation corrections can be submitted directly.

## Development Rules

1. Preserve existing CLI command names and documented JSON fields unless a compatibility change has been discussed.
2. Never include private or runtime data in commits, tests, bug reports, or release archives.
3. Use synthetic data for examples and tests.
4. Keep the Python core dependency-free unless adding a dependency has been explicitly discussed and approved.
5. Avoid breaking stable user-facing interfaces when implementation details can change instead.

Private data includes databases, backups, exports, API tokens, chat IDs, names, real wellness histories, and personal notes.

## Testing

Before submitting a change, run these three commands:

    python3 -m py_compile tools/*.py
    ./tests/regression.sh
    ./tests/public_release.sh

All tests should pass.

## Interface Changes

When changing a public command, JSON field, capability, or documented interface, update the relevant documentation, tests, help metadata, capabilities, CHANGELOG, and VERSION when appropriate.

Do not silently break an existing interface.

## Submitting a Change

1. Fork the repository.
2. Create a branch for the change.
3. Make and test the change.
4. Commit it with a concise description.
5. Push the branch to your fork.
6. Open a Pull Request against the main branch.

Describe what changed and why. Reference an existing GitHub Issue when applicable.

## Privacy Check

Before submitting anything, run:

    ./tests/public_release.sh

Never attach a real Weight Tracker database or user export to a GitHub Issue or Pull Request.

## License

By contributing to Weight Tracker, you agree that your contribution may be distributed under the project's MIT License.
