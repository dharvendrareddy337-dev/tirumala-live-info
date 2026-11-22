"""Astronomical comparison against manually transcribed TTD calendar cells.

Requires Skyfield and a locally downloaded JPL DE421 file. Set EPHEMERIS_PATH.
"""
import json
import os
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import panchang

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "ttd_2027_reference.json"
IST = ZoneInfo("Asia/Kolkata")


@unittest.skipUnless(os.environ.get("EPHEMERIS_PATH"), "EPHEMERIS_PATH is not configured")
class TTDCalendarComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ephemeris = os.environ["EPHEMERIS_PATH"]
        cls.reference = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_manually_transcribed_ttd_reference_dates(self):
        for entry in self.reference["entries"]:
            with self.subTest(date=entry["date"]):
                day = date.fromisoformat(entry["date"])
                events = panchang.calculate_solar_events(day, self.ephemeris)
                sunrise = events["sunrise"]
                self.assertIsNotNone(sunrise, "Tirumala sunrise could not be calculated")
                positions = panchang.calculate_sidereal_longitudes(sunrise, self.ephemeris)
                tithi_number = panchang.tithi_index(positions["moon"], positions["sun"])
                nakshatra_number = panchang.angular_index(positions["moon"], 27)
                self.assertIn(entry["tithi"], panchang.TITHI_NAMES[tithi_number])
                self.assertEqual(entry["nakshatra"], panchang.NAKSHATRA_NAMES[nakshatra_number])

                transitions = panchang.calculate_transition_times(sunrise, self.ephemeris)
                expected_tithi = datetime.combine(day, datetime.strptime(entry["tithiEndsLocal"], "%H:%M").time(), tzinfo=IST)
                expected_nakshatra = datetime.combine(day, datetime.strptime(entry["nakshatraEndsLocal"], "%H:%M").time(), tzinfo=IST)
                self.assertIsNotNone(transitions["tithiEndAt"])
                self.assertIsNotNone(transitions["nakshatraEndAt"])
                discrepancies = []
                for label, calculated, expected in (
                    ("Tithi", transitions["tithiEndAt"], expected_tithi),
                    ("Nakshatra", transitions["nakshatraEndAt"], expected_nakshatra),
                ):
                    difference = (calculated - expected).total_seconds()
                    if abs(difference) > 5 * 60:
                        discrepancies.append(
                            f"{label}: calculated {calculated}, TTD {expected}, "
                            f"difference {difference / 60:.1f} minutes"
                        )
                if discrepancies:
                    self.fail(
                        "; ".join(discrepancies)
                        + f"; sunrise={sunrise}; positions={positions}"
                    )


if __name__ == "__main__":
    unittest.main()
