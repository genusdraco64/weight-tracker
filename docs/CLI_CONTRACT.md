# CLI Contract

The following command names are stable interfaces:

- Logging: `weight`, `food`, `exercise`, `note`, `observation`, `victory`
- Lists: `weights`, `foods`, `exercises`, `notes`, `observations`, `victories`
- Reports: `status`, `dashboard`, `progress`, `summary`, `trend`, `report`
- Milestones: `milestones`, `next`, `next-milestones`
- Utilities: `undo`, `replace-weight`, `help`, `commands`, `capabilities`, `version`, `doctor`, `init`

Global options:

- `--chat-id ID`
- `--name NAME`
- `--json`

List commands accept an optional integer limit or `all`. Integrations needing complete history must request `all`; they must not infer that the default display limit is the complete dataset.

JSON clients should check:

- application `version`
- `command_schema_version`
- `data_schema_version`

Text output is intended for people. JSON output is the integration contract.
