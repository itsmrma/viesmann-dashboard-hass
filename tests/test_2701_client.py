import unittest

from addon.viesmann_dashboard.viesmann_dashboard.client_2701 import parse_controller_xml


class ControllerXmlTests(unittest.TestCase):
    def test_activity_handles_css_tokens_and_missing_indicators(self):
        for indicator, expected in [("red", True), ("blue", True), ("Gray", False),
                                    ("grey", False), ("term_on RED", True),
                                    ("", None), ("unknown", None)]:
            with self.subTest(indicator=indicator):
                result = parse_controller_xml(
                    f"<response><zone><idx>0</idx><term_on_classname>{indicator}</term_on_classname></zone></response>")
                self.assertIs(result["zones"][0]["active"], expected)

    def test_parses_system_and_zone_readings(self):
        payload = """<?xml version="1.0"?>
        <response>
          <system><hp_mode>1</hp_mode><hp_season>0</hp_season></system>
          <zone><idx>0</idx><name>Living room</name><set_temp>21.0</set_temp>
            <temp_op>20.4</temp_op><hum>48</hum><term_on_classname>red</term_on_classname>
          </zone>
        </response>"""

        result = parse_controller_xml(payload)

        self.assertEqual(result, {
            "season": "winter",
            "zones": [{
                "id": 0,
                "name": "Living room",
                "room_temperature": 20.4,
                "target_temperature": 21.0,
                "humidity": 48.0,
                "active": True,
            }],
        })


if __name__ == "__main__":
    unittest.main()
