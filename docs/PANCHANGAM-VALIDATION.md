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
