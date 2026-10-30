import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from addon.viesmann_dashboard.viesmann_dashboard.app import ControllerPoller
from addon.viesmann_dashboard.viesmann_dashboard.state import DashboardState


class RefreshHistoryTests(unittest.TestCase):
    def test_manual_and_scheduled_polls_cannot_overlap_and_recover_after_failure(self):
        state = DashboardState(120)
        poller = ControllerPoller({"controller_url": "http://controller", "session_cookie": "session"}, state)
        started, release = threading.Event(), threading.Event()

        def fetch():
            started.set()
            release.wait(2)
            return {"zones": []}

        poller.controller.fetch_snapshot = Mock(side_effect=fetch)
        thread = threading.Thread(target=poller.refresh)
        thread.start()
        try:
            self.assertTrue(started.wait(1))
            self.assertFalse(poller.refresh())
            self.assertEqual(poller.controller.fetch_snapshot.call_count, 1)
        finally:
            release.set()
            thread.join()
        poller.controller.fetch_snapshot.side_effect = ValueError("secret")
        with self.assertRaisesRegex(RuntimeError, "2701 poll failed"):
            poller.refresh()
        self.assertNotIn("secret", state.snapshot()["sources"]["2701"]["error"])
        poller.controller.fetch_snapshot.side_effect = None
        poller.controller.fetch_snapshot.return_value = {"zones": []}
        self.assertTrue(poller.refresh())
        self.assertIsNone(state.snapshot()["sources"]["2701"]["error"])

    def test_history_retains_only_successful_samples_for_24_hours_with_a_count_limit(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        state = DashboardState(120, clock=lambda: now)
        state.update_2701({"zones": [{"id": 0, "room_temperature": 20}]})
        state.fail("2701", "offline")
        self.assertEqual(len(state.snapshot()["history"]["2701"]), 1)
        now += timedelta(hours=25)
        self.assertEqual(state.snapshot()["history"]["2701"], [])
        for _ in range(1450):
            state.update_2701({"zones": []})
        self.assertEqual(len(state.snapshot()["history"]["2701"]), 1440)

    def test_vicare_history_keeps_native_units_zero_and_unavailable_gaps(self):
        state = DashboardState(120)
        for value in ["0", "unavailable", "nan", "inf", "1.5"]:
            state.update_vicare([{"entity_id": "sensor.power", "state": value,
                                  "attributes": {"unit_of_measurement": "Wh"}}])
        readings = [sample["readings"][0] for sample in state.snapshot()["history"]["vicare"]]
        self.assertEqual([reading["value"] for reading in readings], [0, None, None, None, 1.5])
        self.assertTrue(all(reading["unit"] == "Wh" for reading in readings))
