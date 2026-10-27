# Issue #24 verification

Release 0.1.6 adds Home Assistant release notes and thermometer branding, a room back link, an internal color dialog, aligned main-page headings, and short action feedback.

## Visual evidence

| Surface | Before | After |
| --- | --- | --- |
| Room, desktop | [Before](before/room-desktop.png) | [After](after/room-desktop.png) |
| Room, mobile | [Before](before/room-mobile.png) | [After](after/room-mobile.png) |
| System, desktop | [Before](before/system-desktop.png) | [After](after/system-desktop.png) |
| System, mobile | [Before](before/system-mobile.png) | [After](after/system-mobile.png) |
| Overview, mobile | [Before](before/overview-mobile.png) | [After](after/overview-mobile.png) |

The new color dialog: [desktop](after/color-dialog-desktop.png), [320px mobile](after/color-dialog-mobile.png), [dark theme](after/color-dialog-dark.png). Modal screenshots show the viewport so the full-page capture does not imply that the backdrop ends partway down the page. Branding: [icon](../../addon/viesmann_dashboard/icon.png), [logo](../../addon/viesmann_dashboard/logo.png).

## Automated verification

- `npm run test:ui -- --screenshots=after --evidence-dir=docs/issue-24`: all checks pass. Includes the prior room/sensor/touch regressions plus direct-room back navigation, HEX validation and normalization, visual color adjustment, Apply/Cancel/Escape, persistence across reload, independent light/dark colors, polling during editing, focus containment and restoration, and reduced motion. Main-page navigation stays aligned at all nine widths from 320 to 1280px. No browser errors or device writes.
- `RELEASE_BASE_REF=origin/main python -m unittest discover -s tests -p 'test_*.py' -v`: 11 tests pass on Python 3.14. Release checks verify matching current-version notes, PNG sizes, and version/changelog changes relative to the base revision, alongside existing backend regressions.
- `git diff --check`: passes.

The icon was generated with ImageGen and packaged as 128px and 256px PNGs. Home Assistant metadata follows its official [presentation](https://developers.home-assistant.io/docs/apps/presentation/) and [configuration](https://contributors.home-assistant.io/apps/reference/configuration/) contracts.

Docker is unavailable locally; container build remains a CI check. CI is not awaited. Home Assistant Supervisor behavior and physical PC/Mac/iOS checks remain in the single [final release validation](../../addon/viesmann_dashboard/DOCS.md#final-release-validation).
