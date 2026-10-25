# Viessmann Home Assistant Dashboard

A read-only Home Assistant app (add-on) combining ViCare entities exposed by Home Assistant with direct polling of a Viessmann 2701 controller.

## Current implementation

The Supervisor app is in [`addon/viesmann_dashboard`](addon/viesmann_dashboard). It provides a browser dashboard through Home Assistant Ingress, polls the 2701 PHP/XML interface, and discovers ViCare entities automatically through the Supervisor Home Assistant API. The first version is observational only: it does not send device commands or change settings.

For configuration and local test instructions, see [`addon/viesmann_dashboard/DOCS.md`](addon/viesmann_dashboard/DOCS.md).

## Scope

- Read `index_refresh.php` and `zone_refresh.php?ids=<zone-id>` with a user-configured PHP session cookie.
- Show room temperature, target temperature, humidity when available, season, and zone activity.
- Automatically discover enabled reading entities from Home Assistant's official ViCare integration.
- Mark each source fresh, stale, or unavailable independently; stale begins after two configured polling intervals.
- Ship the poller and GUI together as a Home Assistant Supervisor app.

The initial release supports Supervisor installations only. Write-capable controls and support for Container/Core installations are out of scope.

## Development planning

Planning decisions are recorded in the [Wayfinder map](https://github.com/itsmrma/viesmann-dashboard-hass/issues/1). Agent and issue-tracker conventions are in [`AGENTS.md`](AGENTS.md) and [`docs/agents/`](docs/agents/); installed Matt Pocock skills are recorded in [`skills-lock.json`](skills-lock.json).

## License

This project is licensed under the [MIT License](LICENSE).

## Safety boundary

Write-capable controls remain outside this implementation and require a separate explicit scope decision.
