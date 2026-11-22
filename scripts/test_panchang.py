import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

import panchang


class PanchangMathTests(unittest.TestCase):
    def test_tithi_uses_moon_sun_elongation(self):
        self.assertEqual(panchang.tithi_index(10.0, 0.0), 0)
        self.assertEqual(panchang.tithi_index(12.0, 0.0), 1)
        self.assertEqual(panchang.tithi_index(359.9, 0.0), 29)

    def test_nakshatra_segments(self):
        self.assertEqual(panchang.angular_index(0.0, 27), 0)
        self.assertEqual(panchang.angular_index(360.0 / 27, 27), 1)
        self.assertEqual(panchang.angular_index(359.999, 27), 26)

    def test_daytime_periods_are_ordered_and_inside_sunrise_sunset(self):
        zone = ZoneInfo("Asia/Kolkata")
        day = date(2027, 1, 1)
        sunrise = datetime(2027, 1, 1, 6, 30, tzinfo=zone)
        sunset = datetime(2027, 1, 1, 17, 55, tzinfo=zone)
        values = panchang.calculate_day_periods(day, sunrise, sunset)
        self.assertIsNotNone(values["rahuKalam"])
        self.assertIsNotNone(values["yamagandam"])
        self.assertIsNotNone(values["gulikaKalam"])
        self.assertIsNotNone(values["abhijitMuhurta"])
        self.assertIsNotNone(values["brahmaMuhurta"])

    def test_invalid_sunrise_sunset_rejected(self):
        zone = ZoneInfo("Asia/Kolkata")
        day = date(2027, 1, 1)
        sunrise = datetime(2027, 1, 1, 7, 0, tzinfo=zone)
        sunset = datetime(2027, 1, 1, 6, 0, tzinfo=zone)
        with self.assertRaises(ValueError):
            panchang.calculate_day_periods(day, sunrise, sunset)


if __name__ == "__main__":
    unittest.main()
