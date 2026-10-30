# Issue #30 verification

## Behavior

- Zone activity comes from `index_refresh.php`, with the zone detail as a fallback. Class tokens are normalized; missing/unrecognized indicators remain unknown rather than inactive. The overview distinguishes confirmed activity and reports the detected zone count correctly.
- The header refresh reads only the 2701. Manual and scheduled reads share a single-flight poller. Progress, busy, success and failure feedback preserve existing readings; the endpoint enforces the Ingress peer and requires the dashboard request header.
- Charts cover active-zone counts, measured/target room temperatures, optional humidity, and selected ViCare readings grouped by category/native unit. Tables expose the latest 20 samples. Unknown values break curves, zero remains valid, and charts wait for two real samples.
- In-memory history retains up to 24 hours and 1,440 samples per source. It fills without browser tabs and resets on restart. ViCare history samples Home Assistant states and does not force a cloud update.
- App version: **0.1.8**, with English Home Assistant release notes.

## Reproduction and automated verification

Before the fix, `python -m unittest discover -s tests -p test_client_http.py` failed with `AssertionError: False is not true`: an index response with a red zone and a detail response without the activity field incorrectly yielded `active=False`. The same test passes after the fix. Additional tests cover a gray summary overriding red details, a blue summary, detail-only fallback, compound CSS classes, and unknown indicators.

- `python -m unittest discover -s tests -p 'test_*.py'`: 18 tests; pass. The release comparison is enabled with `RELEASE_BASE_REF=origin/main` after committing.
- `npm run test:ui -- --screenshots=after --evidence-dir=docs/issue-30`: all browser checks pass, including 320–1280px layouts, themes/palettes, both languages, chart gaps/timestamps/units/tables, unknown zone status, and refresh progress, deduplication, Ingress-relative routing, failure/retry behavior. No browser errors or device-write requests.
- `git diff --check`: pass.
- Docker image build and Ruby YAML validation were not run locally: Docker and Ruby are unavailable on this workstation.

## Visual evidence

All captures use **synthetic data**. Before captures show the previous UI; after captures include an eight-sample synthetic history to demonstrate the charts. These are browser regression captures, not live controller measurements.

| View | Before | After |
| --- | --- | --- |
| Overview, desktop | [Screenshot](before/overview-desktop.png) | [Screenshot](after/overview-desktop.png) |
| Room, desktop | [Screenshot](before/room-desktop.png) | [Screenshot](after/room-desktop.png) |
| System, desktop | [Screenshot](before/system-desktop.png) | [Screenshot](after/system-desktop.png) |
| Overview, mobile | [Screenshot](before/overview-mobile.png) | [Screenshot](after/overview-mobile.png) |
| Room, mobile | [Screenshot](before/room-mobile.png) | [Screenshot](after/room-mobile.png) |
| System, mobile | [Screenshot](before/system-mobile.png) | [Screenshot](after/system-mobile.png) |

Rendered desktop and mobile captures were inspected for chart labels, legends, spacing and refresh-button visibility. Physical-device and live-controller scenarios are collected in the existing [final release validation](../../addon/viesmann_dashboard/DOCS.md#final-release-validation), to be run once on the installed release across PC/Mac/iOS. CI is not awaited.
