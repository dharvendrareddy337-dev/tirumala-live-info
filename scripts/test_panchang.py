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


    def test_next_transition_is_found_by_bisection(self):
        start = datetime(2027, 1, 1, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        def longitude(moment):
            hours = (moment - start).total_seconds() / 3600
            return (11.5 + 0.5 * hours) % 360
        found = panchang.find_next_angular_transition(start, longitude, 30)
        expected = start.replace(hour=7, minute=0)
        self.assertIsNotNone(found)
        self.assertLessEqual(abs((found - expected).total_seconds()), 1.0)

    def test_next_transition_handles_360_degree_wrap(self):
        start = datetime(2027, 1, 1, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        def longitude(moment):
            hours = (moment - start).total_seconds() / 3600
            return (359.5 + 0.5 * hours) % 360
        found = panchang.find_next_angular_transition(start, longitude, 360)
        expected = start.replace(hour=7, minute=0)
        self.assertIsNotNone(found)
        self.assertLessEqual(abs((found - expected).total_seconds()), 1.0)

    def test_no_transition_returns_none(self):
        start = datetime(2027, 1, 1, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        found = panchang.find_next_angular_transition(start, lambda _moment: 2.0, 30, max_hours=2)
        self.assertIsNone(found)

    def test_invalid_transition_arguments_rejected(self):
        start = datetime(2027, 1, 1, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        with self.assertRaises(ValueError):
            panchang.find_next_angular_transition(start, lambda _moment: 2.0, 0)


if __name__ == "__main__":
    unittest.main()
