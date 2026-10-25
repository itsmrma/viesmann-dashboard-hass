# Viessmann Heating Dashboard

This Home Assistant Supervisor app automatically discovers and displays ViCare entity states alongside readings from a Viessmann 2701 controller. Open it from the Home Assistant sidebar after installing and starting the app.

## Configuration

In the app's Configuration tab, set:

- **Controller URL**: base URL of the 2701 PHP/XML interface, for example `http://192.0.2.10` (replace with the controller's reachable address).
- **Session cookie**: the current `PHPSESSID` value only. Home Assistant stores it as a password option. Replace it if the controller rejects it.
- **Poll interval**: whole minutes from 1 to 60; the default is 2 minutes.

The controller poller uses GET requests to `index_refresh.php` and `zone_refresh.php?ids=0..6`. It does not perform login, renew the PHP session, or write to the controller. Authentication failures mark the source unavailable/stale and are retried on the next poll.

Restart the app after changing its options. Bump `version` in `config.yaml` before publishing a new image version; the workflow skips version tags already present. The app automatically discovers enabled ViCare sensor, binary sensor, climate, and water heater entities from Home Assistant. It reads entity metadata through the WebSocket registry command and states through the REST API. Both requests are read-only; it does not call services or issue commands.

## Freshness and errors

Each source reports its own last update. 2701 freshness uses the last successful controller poll. ViCare freshness uses the oldest discovered entity `last_updated` value, so a stale reading is not hidden by another entity that updated more recently. A source becomes stale after two configured polling intervals. The last readings remain visible after a failure; before the first successful read, that source is unavailable.

Humidity is omitted when the controller returns an unsupported value. Zone activity uses the seasonal indicator: red in winter or blue in summer means active; gray means inactive. The dashboard does not infer mismatches between readings with different meanings.

## Development

Run the standard-library test suite from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

The app uses a prebuilt multi-architecture GHCR image, published by GitHub Actions after changes reach `main`. The image version follows `version` in `config.yaml`. Home Assistant Supervisor apps require a Supervisor installation; Home Assistant Container/Core is not supported by this package.


## Final release validation

Once a built app is available on the target Home Assistant system, perform one consolidated manual pass on PC, Mac, and iOS: configure the controller URL, session cookie, and polling interval; confirm live readings, independent freshness, stale/unavailable behavior after a controller or entity failure, Ingress navigation, and responsive room-level layout. Confirm no UI action can issue a device command.
