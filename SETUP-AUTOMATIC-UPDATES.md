# Activate automatic Tirumala Live Info updates

This project is prepared for a low-cost setup using GitHub Actions + Supabase + Firebase Cloud Messaging. There is no daily manual data entry. You must create/configure the free provider projects once; I cannot create them inside your personal accounts from this chat.

## What will happen after setup

1. GitHub Actions runs `scripts/update_data.py` every 15 minutes.
2. The script reads only public pages from TTD and Open-Meteo.
3. It updates one `latest` JSON row in Supabase.
4. The app reads the latest snapshot every 5 minutes while it is open.
5. If the queue report, SSD balance/running slot, new TTD announcements or weather materially change, the script sends one combined push notification to devices that opted in.
6. If a source does not publish a value or cannot be reached, the app shows that fact and keeps the last saved timestamp.

The 15-minute schedule is a **checking interval**, not a promise that TTD itself will publish new information every 15 minutes.

## Step 1 — Create Supabase (database)

1. Go to [https://supabase.com/](https://supabase.com/) and create a free account/project.
2. In your project open **SQL Editor → New query**.
3. Open this project's `supabase/schema.sql`, copy all of it, paste it into SQL Editor and click **Run**.
4. Open **Project Settings → Data API** (or API settings) and copy:
   - Project URL, similar to `https://YOURPROJECT.supabase.co`
   - Publishable/anon key (use the public browser key, not the service-role key)
5. Open **Project Settings → API Keys** and copy the **service_role** key for the GitHub secret only. Do not paste that key into the app or share it publicly.

## Step 2 — Add the public Supabase values to the app

Open `app-config.js`. Replace only the empty strings for:

```js
supabaseUrl: "https://YOURPROJECT.supabase.co",
supabaseAnonKey: "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY",
```

Save the file. The browser needs only the public anon/publishable key; table permissions are restricted by the included SQL policies.

## Step 3 — Create Firebase Cloud Messaging (push alerts)

1. Go to [https://console.firebase.google.com/](https://console.firebase.google.com/) and create a project.
2. Add a **Web app** to that Firebase project. Copy its Web app config values into the `firebase` object in `app-config.js` (`apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId`, `appId`).
3. Open **Project settings → Cloud Messaging → Web Push certificates** and generate a key pair. Copy the **public VAPID key** into `firebaseVapidKey` in `app-config.js`.
4. Open **Project settings → Service accounts** and generate a private key JSON file for the Firebase service account. Keep this file private. Do not add it to the project ZIP or commit it to GitHub.
5. Ensure the service account has permission to send Firebase Cloud Messaging messages (Firebase Cloud Messaging API / FCM Admin role as appropriate for the project).

Firebase's web push API requires an HTTPS origin and a service worker. GitHub Pages supplies HTTPS after deployment.

## Step 4 — Upload the project to GitHub

1. Create a GitHub repository. For the no-cost GitHub Pages route, make it public.
2. Upload the complete contents of this project folder (including hidden `.github` folder) to the repository's default branch.
3. Check that `.github/workflows/update-ttd-data.yml` is visible in the repository.

## Step 5 — Add server-only GitHub Actions secrets

In your GitHub repository open **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Secret name | Value |
|---|---|
| `SUPABASE_URL` | Same Supabase project URL from Step 1 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service_role key from Step 1 (server only) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Entire contents of the Firebase service-account JSON file |
| `PUBLIC_APP_URL` | Final HTTPS app address, e.g. `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/` |

Do not add these secrets to `app-config.js`, README, issue comments or source code.

## Step 6 — Run the first automatic data update

1. Open the GitHub repository's **Actions** tab.
2. Select **Update Tirumala public information**.
3. Click **Run workflow**.
4. Open the run and confirm it finishes successfully.
5. In Supabase → **Table Editor**, open `live_snapshots`. A row with `id = latest` should exist.

After that, GitHub will try to run the updater every 15 minutes. Scheduled GitHub runs can be delayed by GitHub; they are not exact real-time jobs.

## Step 7 — Publish the PWA on HTTPS

1. In the GitHub repository open **Settings → Pages**.
2. Under Build and deployment choose **Deploy from a branch**.
3. Choose the default branch and `/ (root)` then Save.
4. Wait until GitHub Pages shows the published HTTPS address.
5. Open that address on your Android phone in Chrome.
6. Use Chrome menu → **Install app** or **Add to Home screen**.

If you host at a different path or custom domain, set `PUBLIC_APP_URL` to the exact root URL with its trailing slash.

## Step 8 — Enable alerts on your phone

1. Open the installed Tirumala Live Info app while online.
2. Tap the bell button in the top-right corner.
3. Tap **Enable all notifications** and allow notifications when Android/Chrome asks.
4. The app registers the FCM token in Supabase. That token table is not publicly readable.
5. To receive alerts when the app is closed, keep Android notification permission enabled for Chrome / the installed PWA and do not force-stop the browser.

## What can and cannot be automatic with public data

| Information | Automatic public update? | Detail |
|---|---|---|
| Sarva Darshan approximate wait | Yes, when TTD publishes it | TTD Breaking News posts commonly publish a current situation and approximate wait without SSD tokens. |
| Queue location / compartment count | Yes, when reported | The app reports the text/number TTD actually publishes; it does not estimate a missing number. |
| SSD running slot / balance tickets | Yes | TTD Current Booking page. TTD itself warns that counter status can change. |
| Previous-day pilgrim footfall | Yes | TTD Breaking News daily post. |
| TTD announcements | Yes | Titles/snippets/links from TTD News. |
| Weather | Yes | Open-Meteo, no API key required. |
| Room vacancy counts | **No public live feed found** | TTD FAQ says current vacancies are displayed on counter boards. The app shows process information and official links only. |
| Locker / luggage vacancies | **No public live feed found** | TTD publishes counter locations and general service information, not a public live available-space count. |
| Divya Darshan live remaining tokens | **No public count found** | The app shows TTD's published footpath timing guidance, not a live count. |

For exact room/locker inventory or private operational data, ask TTD for an authorised API/feed. Do not scrape the booking portal's logged-in pages, automate login, or bypass CAPTCHA/security controls.

## Troubleshooting

- **App says `REFERENCE DATA · SETUP REQUIRED`:** Supabase URL/anon key or the first GitHub Actions run is still missing.
- **The Supabase table is empty:** run the workflow manually and inspect its log; verify the service-role secret and schema SQL.
- **TTD source shows unavailable:** the source may be offline or its page layout changed. The script keeps the last successful values and records both the latest check and the last successful check time. If every public source fails, the app labels the snapshot as stale rather than live.
- **Notification button says setup is incomplete:** recheck `app-config.js`, Firebase Web app config, VAPID public key and that the site is served through HTTPS.
- **Device registered but no alerts:** verify `FIREBASE_SERVICE_ACCOUNT_JSON`, `PUBLIC_APP_URL`, the FCM API permission and GitHub workflow logs. Alerts are sent only when a tracked value materially changes.
- **Notifications stop:** Android/Chrome may have revoked permission, the app/browser may have been force-stopped, or Firebase may have expired the device token. Re-open the app and enable alerts again.

## Low-cost operating estimate

This design uses free tiers to start: GitHub Actions for scheduled work, Supabase Free for a small snapshot/token table, Firebase Cloud Messaging for web push, and Open-Meteo without an API key. Provider quotas and plan terms can change. Supabase Free projects may pause after a week of insufficient activity, so monitor the project dashboard and usage before depending on this for public-service decisions.
