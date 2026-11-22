# Tirumala Panchangam implementation and validation plan

## Status

This branch is a staging area only. It does not change the live `main` branch and does not publish Panchangam values.

Reference supplied for validation: `ttd-panchangam-calendar-2027-748.pdf` (12-page Telugu monthly calendar, uploaded by the repository owner).

## Recommended calculation convention

Proposed default: Drik Ganita (astronomical calculation), Lahiri/Chitrapaksha ayanamsa, geocentric sidereal Sun and Moon longitudes, Tirumala coordinates, and Asia/Kolkata civil time.

This is a proposed computational convention, not a claim that it exactly reproduces every TTD calendar convention. Any difference from the TTD reference must be recorded, not silently adjusted.

## Licensing and dependency gate

Do not add Swiss Ephemeris / pyswisseph until its AGPL or commercial licensing implications have been reviewed for the intended app distribution.

Prefer a permissively licensed astronomy library and a documented JPL ephemeris data source. Before adding dependencies, record:
- package and exact version;
- license and redistribution obligations;
- ephemeris file name, source, size, and checksum;
- whether GitHub Actions can retrieve and cache it reliably;
- whether the result is reproducible offline after the data file is cached.

## Validation requirements

1. Extract the 2027 monthly calendar entries from the supplied PDF. It is a scanned Telugu calendar, so OCR output must be manually checked against page images.
2. Build a machine-readable reference fixture with the source page and date for each transcribed field. Never treat uncertain OCR as ground truth.
3. Compare computed values for multiple dates spread across the year, including dates near sunrise and Tithi/Nakshatra transitions.
4. Compare:
   - weekday / Vara;
   - Tithi and its ending time, where the calendar publishes it;
   - Nakshatra and its ending time, where published;
   - sunrise and sunset;
   - Rahu Kalam, Yamagandam and Gulika intervals, where published.
5. Record exact timezone, location coordinates, ayanamsa, ephemeris version and rounding convention with every test.
6. Do not claim a field is validated when the supplied calendar does not publish a comparable value.
7. Do not populate Amrita Kalam, Varjyam, Durmuhurtham, Brahma Muhurta or Abhijit Muhurta until their specific rules and reference comparisons are independently confirmed.

## Release gate

No Panchangam values are enabled in the production snapshot until:
- dependency licensing is acceptable for the app;
- the calculation engine has automated tests;
- reference comparisons have been reviewed;
- the output schema is backward compatible;
- missing or failed calculations remain explicitly unavailable rather than guessed.

After those gates pass, open a separate pull request for review. Do not merge or deploy automatically.


## Review of the supplied TTD 2027 PDF

The uploaded file was reopened and inspected as page images (12 pages; scanned Telugu calendar, not a text-native PDF).

Confirmed from the January 2027 page:
- The page is headed as the January 2027 calendar and contains day-by-day calendar cells.
- The printed footer explicitly states in Telugu that the Tithi and Nakshatra entries indicate their ending times (అంత్య సమయము).
- The footer also explains the dawn-to-dawn convention for the weekday marker, including the period before the following sunrise. This convention must be represented explicitly when matching a civil date to a TTD calendar day.
- The calendar credits its Panchanga compiler and identifies TTD as publisher/printer.

Validation consequence:
- A comparison must compare transition/end times, not merely the Tithi or Nakshatra label at local midnight.
- The TTD dawn-based weekday/day convention must be modelled before declaring a date-level match.
- The source is image-scanned. OCR of the small Telugu cells is error-prone; every reference value used in tests must be visually transcribed and independently checked. Unreviewed OCR is not acceptable as a golden test fixture.

## Current implementation decision

The first experimental calculation module and isolated test workflow have now been added on this branch only. The existing runtime feed remains marked unavailable. This is intentional: the PDF's printed convention has been identified, but a verified, machine-readable set of date/time reference points and an acceptable permissive-licensed ephemeris stack are still required before a calculation can be called validated.


## Free calculation prototype added (not production-enabled)

A first experimental helper module now exists at `scripts/panchang.py`. It uses Skyfield, an open-source Python astronomy library, and expects a JPL DE421 ephemeris file supplied locally. The location object uses Skyfield's current `wgs84.latlon` API. The Panchangam dependency is isolated in `scripts/requirements-panchang.txt`; it is not installed by the existing live-data updater.

The prototype currently contains:
- solar sunrise/sunset and lunar rise event calculations for Tirumala;
- a provisional Lahiri ayanamsa approximation;
- basic tithi and nakshatra segment calculations;
- weekday-based Rahu Kalam, Yamagandam and Gulika daytime segments;
- provisional Brahma Muhurta and Abhijit intervals.

Important limitations:
- This is an engineering prototype, not a validated Panchangam.
- The Lahiri approximation and time-window conventions require comparison with the supplied TTD calendar and a clearly selected tradition.
- Tithi/Nakshatra are currently sampled at sunrise; transition/end times are not yet calculated.
- Yoga is emitted only as an index in the prototype; Karana, Amrita Kalam, Varjyam and Durmuhurtham remain unavailable.
- The module is not called by `update_data.py`, does not modify `data/live.json`, and does not publish to Supabase or Firebase.
- No ephemeris binary is committed. Its acquisition, provenance, redistribution terms and checksum must be recorded before CI or production use.

An isolated GitHub Actions workflow runs helper unit tests for this prototype. Passing those tests checks arithmetic helpers only; it does not establish agreement with TTD's calendar.


### Dependency licence check

The Skyfield project LICENSE file identifies the library as MIT-licensed and permits use, modification and distribution subject to retaining its copyright and permission notice. Source reviewed: https://github.com/skyfielders/python-skyfield/blob/master/LICENSE

This means the Python library itself does not require a paid subscription. The JPL ephemeris data file is a separate input and must have its own source/provenance recorded; the project does not bundle or redistribute it at this stage.
