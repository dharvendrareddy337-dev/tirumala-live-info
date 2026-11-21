# Tirumala Live Info

An independent, mobile-first Tirumala pilgrim companion. This update adds the automatic public-information pipeline and opt-in push-notification wiring.

## What can update automatically

| App area | Public source | Behaviour after setup |
|---|---|---|
| Sarva Darshan approximate waiting time and queue location | TTD News → Breaking News | Checks every 15 minutes; displays the latest TTD-published report and its report date |
| Waiting compartments | TTD News → Breaking News | Displays a number only when TTD publishes one; otherwise shows the published location/description |
| SSD running slot and balance tickets | TTD Current Booking | Checks every 15 minutes; includes TTD's first-come-first-served / status-may-change warning |
| Previous-day pilgrim count | TTD News → Breaking News | Updates when TTD publishes a new daily report |
| Official TTD announcements | TTD News | Collects latest article titles, links and snippets |
| Tirumala weather | Open-Meteo | Refreshes on the 15-minute job; no API key needed |
| Seva, room and luggage guidance | Public TTD FAQ and TTD News | Provides cited guidance and source links, not fake stock counts |

**Important limits:** TTD's public pages used here do not expose a live room-vacancy API or live locker-capacity API. The app therefore does not make up vacant-room, locker-space or DD-token counts. Current room vacancies must be checked on TTD counter display boards / official booking channels. DD information is shown as published guidance, not as a live counter.

## Project structure

- `index.html` — responsive PWA front end.
- `assets/` — original app icon and visual assets.
- `data/live.json` — dated reference snapshot used before backend setup.
- `scripts/update_data.py` — public-source collector, parser, Supabase publisher and FCM alert sender.
- `.github/workflows/update-ttd-data.yml` — scheduled collection every 15 minutes and manual workflow trigger.
- `supabase/schema.sql` — public read-only data snapshot table and private push-token table.
- `app-config.js` — public browser configuration placeholders. Never put server secrets here.
- `service-worker.js` — PWA offline cache and Firebase background-message handler.
- `SETUP-AUTOMATIC-UPDATES.md` — setup guide.

## Quick preview

Open `index.html` using a local web server (not `file://`):

```bash
python -m http.server 8080
```

Open `http://localhost:8080`. The current included JSON is a **dated reference snapshot**, not a live feed. The live backend starts only after the setup below is completed.

## Enable automatic updates

Follow `SETUP-AUTOMATIC-UPDATES.md`. In brief:

1. Create a free Supabase project and run `supabase/schema.sql` once.
2. Put the Supabase project URL and publishable/anon key in `app-config.js`.
3. Create a Firebase Web app and enable Firebase Cloud Messaging; put the public Firebase web config and VAPID public key in `app-config.js`.
4. Upload the project to GitHub and add the server-only GitHub Actions secrets listed in the setup guide.
5. Run **Actions → Update Tirumala public information → Run workflow** once; then the 15-minute schedule takes over.
6. Host the app on HTTPS (GitHub Pages is the low-cost path), open the installed app and tap the notification bell → **Enable all notifications**.

The GitHub workflow fetches the public TTD pages, writes a snapshot to Supabase, and sends FCM alerts when a tracked field or new official TTD article changes. Alerts cover queue/wait changes, SSD slot/balance changes, previous-day pilgrim count changes, new TTD announcements, significant weather changes, and source outage/recovery events. The app reads that snapshot every five minutes while open. Room/locker vacancies and live DD remaining-token counts are excluded because they are not present in the public feeds currently used.

## Data and notification safety

- The app does not log in to TTD, book tickets, submit forms, bypass CAPTCHA, defeat rate limits, or access private systems.
- TTD-published queue time is an approximate report for Sarva Darshan without SSD tokens, not a guarantee for an individual pilgrim.
- Source timestamps and failure states are retained. When a source fails, the last successful value is kept and shown with its timestamp; it is not replaced with a guess.
- Push is opt-in. Firebase web config and VAPID public key are browser-visible values; the Supabase service-role key and Firebase service-account JSON must remain GitHub secrets only.
- This is an independent app and is not affiliated with TTD. Use the official TTD website/app for bookings and critical confirmations.

## Public sources

- TTD Current Booking: https://tirumala.org/Current_Booking.aspx
- TTD Breaking News: https://news.tirumala.org/category/breaking-news/
- TTD News: https://news.tirumala.org/
- TTD FAQ PDF: https://www.tirumala.org/Downloads/MoreFaqs.pdf
- Open-Meteo: https://open-meteo.com/
