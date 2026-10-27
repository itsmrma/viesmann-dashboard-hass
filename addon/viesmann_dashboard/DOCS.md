# Viessmann Dashboard

This Home Assistant Supervisor app automatically discovers and displays ViCare entity states alongside readings from a Viessmann 2701 controller. Open it from the Home Assistant sidebar after installing and starting the app.

## Configuration

In the app's Configuration tab, set:

- **Controller URL**: base URL of the 2701 PHP/XML interface, for example `http://192.0.2.10` (replace with the controller's reachable address).
- **Session cookie**: the current `PHPSESSID` value only. Home Assistant stores it as a password option. Replace it if the controller rejects it.
- **Poll interval**: whole minutes from 1 to 60; the default is 2 minutes.

The controller poller uses GET requests to `index_refresh.php` and `zone_refresh.php?ids=0..6`. It does not perform login, renew the PHP session, or write to the controller. Authentication failures mark the source unavailable/stale and are retried on the next poll.

Restart the app after changing its options. The app automatically discovers enabled ViCare sensor, binary sensor, climate, and water heater entities from Home Assistant. It reads entity metadata through the WebSocket registry command and states through the REST API. Both requests are read-only; it does not call services or issue commands.

## Dashboard views and theme

The overview is generated from live 2701 zones and Home Assistant areas. Rooms appear in this order: Cucina, Sala, Matrimoniale, Cameretta, Armadi, Bagni, then any additional areas alphabetically, with Circuito diretto last. Select a room card to open its dedicated detail view; use **Torna alla panoramica** (or **Back to overview** in English) to return, including when opening a room directly. Adding or renaming zones and areas does not require dashboard configuration.

The temperature and humidity controls are local previews only. The season comes from the 2701 controller and cannot be previewed or changed. Humidity preview is enabled only when the controller reports summer and a zone is linked. Both control panels share the same height, number typography, and slider alignment; they stack on narrow screens.

**Impianto** groups selected ViCare sensors into today's electricity consumption, water temperatures, and heat pump operation (outdoor temperature, compressor power/modulation, circuit pressure). It includes readings assigned to Home Assistant areas. Canonical entity-registry translation keys identify sensors even after renaming; canonical entity-ID suffixes are a fallback when metadata is absent. Multiple matching sensors remain separate and display their source names. Technical diagnostics and historical counters are omitted. Native units are retained, missing sensors are omitted, and unavailable values show a dash. Daily consumption is neither summed nor inferred. Actual availability depends on the device, API plan, and enabled entities in Home Assistant.

The theme selector offers automatic, light, and dark modes. Automatic mode follows the Home Assistant page theme when its background color is readable from Ingress; otherwise it follows the operating system color preference. The selection is remembered in the browser.

In **Impostazioni → Colori della pagina → Personalizzata**, select a background, surface, or accent swatch to open the dashboard's color dialog. Adjust hue, saturation, and lightness or enter a 3- or 6-digit HEX code (with or without `#`). **Applica colore** saves the color on this device; **Annulla** or Escape discards the draft. Light and dark themes retain independent colors. A contrast warning helps identify combinations that may be difficult to read. The dialog supports keyboard navigation and keeps the draft intact during status polling. Short control feedback respects the device's reduced-motion setting.

## Freshness and errors

Each source reports its own last update. 2701 freshness uses the last successful controller poll. ViCare freshness uses the oldest discovered entity `last_updated` value, so a stale reading is not hidden by another entity that updated more recently. A source becomes stale after two configured polling intervals. The last readings remain visible after a failure; before the first successful read, that source is unavailable.

Humidity is omitted when the controller returns an unsupported value. Zone activity uses the seasonal indicator: red in winter or blue in summer means active; gray means inactive. The dashboard does not infer mismatches between readings with different meanings.

## Development

Run the standard-library test suite from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the browser regression checks (Node.js 20 or later):

```sh
npm ci
npx playwright install chromium
npm run test:ui
```

The browser checks serve the production HTML with synthetic read-only API data. They cover room ordering, equal control geometry and typography, mobile overflow, source metadata, missing readings, themes, localization, and synthesized Chromium touch input. Add `-- --screenshots=after` to regenerate the review screenshots. See [issue #22 evidence](../../docs/issue-22/README.md) for before/after captures and verification details.

The app uses a prebuilt multi-architecture GHCR image, published by GitHub Actions after changes reach `main`. The image version follows `version` in `config.yaml`. Home Assistant Supervisor apps require a Supervisor installation; Home Assistant Container/Core is not supported by this package.

## Release notes and Home Assistant branding

For every app change, increase `version` in `config.yaml` and add a matching newest `## x.y.z` section with user-visible changes to `CHANGELOG.md` in this app folder. The workflow skips image tags already published, so every release needs a fresh version. CI checks that app changes advance the version and update the changelog, and that the latest notes match the configured version. To run the comparison locally after committing, set `RELEASE_BASE_REF=origin/main` when running the Python suite.

Home Assistant Supervisor reads `CHANGELOG.md`, `icon.png` (128×128), and `logo.png` (256×256) directly from this folder. The app and its sidebar entry are named **Viessmann Dashboard**; the sidebar uses `panel_icon: mdi:thermometer`. See the official [app presentation](https://developers.home-assistant.io/docs/apps/presentation/) and [configuration](https://contributors.home-assistant.io/apps/reference/configuration/) documentation. After merging and publishing the image, refresh the app store repositories and install the update in Home Assistant to see the new version and branding.


## Final release validation

Once a built app is available on the target Home Assistant system, perform one consolidated manual pass on PC, Mac, and iOS: configure the controller URL, session cookie, and polling interval; confirm live readings, independent freshness, stale/unavailable behavior after a controller or entity failure, Ingress navigation, and responsive room-level layout. Confirm no UI action can issue a device command.

Include the issue #22 scenarios in that same pass: confirm the requested room order and final direct-circuit card; equal temperature/humidity panels; absence of a season preview; winter/summer humidity availability; readable Impianto values matching the enabled ViCare sensors, including area-assigned or renamed entities; portrait/landscape layout, zoom, and native slider drag versus vertical page scrolling in Safari/iOS. Browser emulation and synthesized Chromium touch do not replace this physical-device check.

Include the issue #24 scenarios in that same pass: confirm the 0.1.6 release notes and thermometer app/sidebar icons in Home Assistant; direct room links and the back link under Ingress; stable overview/system/settings headings; all three custom colors, visual sliders, HEX entry, Apply/Cancel/Escape and theme-specific persistence; the iOS keyboard and short viewport; brief button feedback and reduced-motion behavior. These Supervisor and physical-device checks remain pending until the release is installed.

For 0.1.7, also confirm **Viessmann Dashboard** appears in both the app list and sidebar, with the thermometer sidebar icon.
