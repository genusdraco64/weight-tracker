---
name: Installation report
about: Report a successful or unsuccessful beta installation
title: "[INSTALL] "
labels: beta-testing
assignees: ""
---

## Result

- [ ] Installation succeeded
- [ ] Installation failed
- [ ] Installation succeeded with issues

## Weight Tracker version

Run:

weight_tracker version

Paste the output here.

## System

- Operating system:
- Distribution/version:
- Python version:
- Architecture:
- Installation method:

## Verification

Did these commands pass?

weight_tracker doctor
./tests/regression.sh
./tests/public_release.sh

## AI integration

If tested:

- Agent/platform:
- Did capability discovery work?
- Did natural-language logging work?

## Problems encountered

Describe any errors or unexpected behavior.

Do not upload private wellness databases, exports, credentials, or API tokens.

## Notes

Anything else that may help improve installation or documentation.
