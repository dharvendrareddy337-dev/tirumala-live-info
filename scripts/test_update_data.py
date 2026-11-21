import unittest
import update_data

class SourceParserTests(unittest.TestCase):
    def test_ttd_current_booking_parser(self):
        html = '''<html><body><div>Running Slot: 12 on 15-Nov-2026</div>
        <div>Balance tickets for 15-Nov-2026: 0</div></body></html>'''
        data = update_data.parse_ttd_current_booking(html)
        self.assertEqual(data['runningSlot'], 12)
        self.assertEqual(data['date'], '2026-11-15')
        self.assertEqual(data['balanceTickets'], 0)

    def test_ttd_breaking_news_parser(self):
        html = '''<html><body><main>
        Total pilgrims who had darshan on 13.11.2026: 70,124
        Tonsures: 32,298 Hundi kanukalu: 4.92 CR
        Present Situation on 14-11-2026: Waiting compartments… outside line at Silathoranam.
        Approx. Darshan time for Sarvadarshanam (without SSD Tokens)…15 H.
        </main></body></html>'''
        data = update_data.parse_breaking_news(html)
        self.assertEqual(data['pilgrimsYesterday'], 70124)
        self.assertEqual(data['pilgrimsDate'], '2026-11-13')
        self.assertEqual(data['reportedFor'], '2026-11-14')
        self.assertEqual(data['approxWaitText'], '15H')
        self.assertIn('Silathoranam', data['queuePosition'])
        self.assertIsNone(data['waitingCompartments'])

    def test_numeric_compartments_parser(self):
        html = '''<html><body>
        Total pilgrims who had darshan on 07.11.2026: 80,367
        Present Situation on 08-11-2026: Waiting Compartments..31
        Approx. Darshan Time for Sarvadarshanam (without SSD Tokens)…15 H.
        </body></html>'''
        data = update_data.parse_breaking_news(html)
        self.assertEqual(data['waitingCompartments'], 31)

    def test_source_status_preserves_last_success_when_fetch_fails(self):
        previous = {"ttdNews": {"ok": True, "checkedAt": "2026-11-14T10:00:00+05:30"}}
        failed = update_data.source_status("ttdNews", False, "https://news.tirumala.org/", previous, "timeout")
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["lastSuccessfulAt"], "2026-11-14T10:00:00+05:30")
        self.assertEqual(failed["note"], "timeout")

    def test_source_status_updates_last_success_on_success(self):
        previous = {"ttdNews": {"ok": True, "checkedAt": "2026-11-13T10:00:00+05:30"}}
        success = update_data.source_status("ttdNews", True, "https://news.tirumala.org/", previous)
        self.assertTrue(success["ok"])
        self.assertTrue(success["lastSuccessfulAt"].startswith("2026-"))
        self.assertEqual(success["lastSuccessfulAt"], success["checkedAt"])

    def test_daily_footfall_change_alert(self):
        old = {"darshan": {"pilgrimsYesterday": 65000, "pilgrimsDate": "2026-11-12"}, "ssd": {}, "news": [], "sources": {}}
        new = {"darshan": {"pilgrimsYesterday": 70124, "pilgrimsDate": "2026-11-13"}, "ssd": {}, "news": [], "sources": {}}
        alerts = update_data.changed_alerts(old, new)
        self.assertTrue(any("daily pilgrim count" in alert for alert in alerts))

    def test_source_outage_alert_only_on_state_change(self):
        old = {"darshan": {}, "ssd": {}, "news": [], "sources": {"ttdNews": {"ok": True}}}
        down = {"darshan": {}, "ssd": {}, "news": [], "sources": {"ttdNews": {"ok": False}}}
        self.assertTrue(any("TTD News source is temporarily unavailable" in a for a in update_data.changed_alerts(old, down)))
        self.assertEqual(update_data.changed_alerts(down, down), [])

    def test_weather_parser(self):
        weather = update_data.parse_weather({'current': {
            'temperature_2m': 21.3, 'apparent_temperature': 20.1,
            'relative_humidity_2m': 62, 'precipitation': 0,
            'weather_code': 2, 'wind_speed_10m': 9,
            'time': '2026-11-14T16:00'
        }})
        self.assertEqual(weather['condition'], 'Partly cloudy')
        self.assertEqual(weather['temperatureC'], 21.3)

if __name__ == '__main__':
    unittest.main()
