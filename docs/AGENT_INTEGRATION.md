# AI agent integration

Weight Tracker is designed so an AI agent does not need to memorize its command surface.

## Discovery flow

At the start of a wellness-related session, after an upgrade, or after an unknown-command error:

```bash
weight_tracker capabilities
```

For detailed command metadata:

```bash
weight_tracker help --json
weight_tracker help COMMAND
```

The tracker, not the agent, should be the source of truth for stored values, milestones, reports, and trends.

## Identity

Every user-specific command needs an identity:

```bash
weight_tracker --chat-id USER_ID status
```

`USER_ID` is an opaque stable identifier. Prefer a platform prefix when multiple systems may share a database, such as `telegram:12345`, `discord:...`, or `local:alice`. Bare numeric identifiers are supported; existing legacy `telegram:<numeric-id>` records remain discoverable from bare numeric input for compatibility.

Never substitute one user's ID for another.

## Recommended behavior

1. Interpret the user's natural-language request.
2. Use `capabilities` or help when the correct command is uncertain.
3. Log high-confidence data through the tracker.
4. Use tracker-generated reports rather than recalculating them in the agent.
5. For charts or programmatic processing, request complete JSON history, for example:

```bash
weight_tracker --chat-id USER_ID --json weights all
```

6. Never conclude that a capability is unavailable solely because a default list command returns a limited number of rows.

## Prompt template

`prompts/wellness_agent.md` is a generic reference prompt. Adapt the launcher path and platform-specific identity instructions in the host agent configuration rather than editing core tracker logic.
