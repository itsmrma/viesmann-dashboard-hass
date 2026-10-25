# Viessmann Home Assistant Dashboard

A read-only Home Assistant project to bring the status of a Viessmann Vitocal heat pump, managed through ViCare, together with readings from a Viessmann 2701 controller.

The goal is to make the combined heating and cooling status easier to understand and to assess whether a dedicated Home Assistant integration or dashboard is a viable option.

## Scope

The initial phase is **read-only**:

- Parse and display available data from ViCare and the existing PHP-based Home Assistant scrapers for the 2701.
- Make no changes to either device or service.
- Expose no controls or services that can change operating modes, setpoints, schedules, or other device settings.

The project will first check whether it can reuse Home Assistant's official ViCare integration and the user's existing scraper entities instead of duplicating data collection.

## Project status

Planning is tracked in the [Wayfinder project map](https://github.com/itsmrma/viesmann-dashboard-hass/issues/1). The next step is to identify the relevant 2701 scraper entities and their values, units, and update frequency. Please redact credentials and personal data from any configuration shared for that work.

No Home Assistant integration or dashboard implementation is available yet.

## Development planning

Project-specific agent skill and issue-tracker configuration is in [`AGENTS.md`](AGENTS.md) and [`docs/agents/`](docs/agents/). The installed Matt Pocock skills are recorded in [`skills-lock.json`](skills-lock.json).

## Safety boundary

Any future write-capable control is outside the current scope and requires a separate explicit scope decision. The viability prototype must remain observational.
