# Viessmann Heating Dashboard

This Home Assistant Supervisor app displays selected ViCare entity states and readings from a Viessmann 2701 controller. Open it from the Home Assistant sidebar after installing and starting the app.

## Configuration

In the app's Configuration tab, set:

- **Controller URL**: base URL of the 2701 PHP/XML interface, for example `http://192.0.2.10` (replace with the controller's reachable address).
- **Session cookie**: the current `PHPSESSID` value only. Home Assistant stores it as a password option. Replace it if the controller rejects it.
- **Poll interval**: whole minutes from 1 to 60; the default is 2 minutes.
- **ViCare entity IDs**: comma-separated entity IDs from Home Assistant's official ViCare integration, for example `sensor.vitocal_flow_temperature,sensor.vitocal_return_temperature`.

The controller poller uses GET requests to `index_refresh.php` and `zone_refresh.php?ids=0..6`. It does not perform login, renew the PHP session, or write to the controller. Authentication failures mark the source unavailable/stale and are retried on the next poll.

Restart the app after changing its options. Bump `version` in `config.yaml` before publishing a new image version; the workflow skips version tags already present. The add-on reads ViCare states through Home Assistant's read-only states API. It does not call services or issue commands. Select entity IDs in the add-on options to choose what appears in the dashboard.

## Freshness and errors

Each source reports its own last update. 2701 freshness uses the last successful controller poll. ViCare freshness uses the oldest selected entity `last_updated` value, so a stale selected reading is not hidden by another entity that updated more recently. A source becomes stale after two configured polling intervals. The last readings remain visible after a failure; before the first successful read, that source is unavailable.

Humidity is omitted when the controller returns an unsupported value. Zone activity uses the seasonal indicator: red in winter or blue in summer means active; gray means inactive. The dashboard does not infer mismatches between readings with different meanings.

## Development

Run the standard-library test suite from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

The app uses a prebuilt multi-architecture GHCR image, published by GitHub Actions after changes reach `main`. The image version follows `version` in `config.yaml`. Home Assistant Supervisor apps require a Supervisor installation; Home Assistant Container/Core is not supported by this package.


## Final release validation

Once a built app is available on the target Home Assistant system, perform one consolidated manual pass on PC, Mac, and iOS: configure the controller URL, session cookie, polling interval, and ViCare entity IDs; confirm live readings, independent freshness, stale/unavailable behavior after a controller or entity failure, Ingress navigation, and responsive room-level layout. Confirm no UI action can issue a device command.
