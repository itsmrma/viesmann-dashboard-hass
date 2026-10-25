# Issue tracker: GitHub

Issues and specs for this repository live in GitHub Issues at `itsmrma/viesmann-dashboard-hass`. Use the `gh` CLI with `--repo itsmrma/viesmann-dashboard-hass` when the working directory is not a Git clone.

## Conventions

- Create an issue with `gh issue create --repo itsmrma/viesmann-dashboard-hass --title "..." --body "..."`.
- Read an issue with `gh issue view <number> --repo itsmrma/viesmann-dashboard-hass --json number,title,body,labels,comments`.
- Comment with `gh issue comment <number> --repo itsmrma/viesmann-dashboard-hass --body "..."`.
- Apply labels with `gh issue edit <number> --repo itsmrma/viesmann-dashboard-hass --add-label "..."`.
- Close with `gh issue close <number> --repo itsmrma/viesmann-dashboard-hass`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Wayfinding operations

Use one GitHub issue labelled `wayfinder:map` as the map, and GitHub child issues labelled `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task` for tickets. Create children with `gh issue create --parent <map-number> --repo itsmrma/viesmann-dashboard-hass ...` where supported; otherwise link them in the map body and add `Part of #<map-number>` to each child. Use GitHub native issue dependencies for blocking when available; otherwise record `Blocked by: #...` in the child body. The open, unblocked, unassigned children are the frontier.
