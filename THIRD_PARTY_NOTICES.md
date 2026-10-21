# Third-party notices

| Component | Where | License |
|---|---|---|
| dashaflow 1.1.0 by Adarsh J: `constants.py`, `matchmaking.py`, `nakshatra.py` | vendored in `src/twinsky_engine/_vendor/dashaflow` (see its `NOTICE.md`) | MIT, text in `_vendor/dashaflow/LICENSE` |
| lunar-python by 6tail | dependency | MIT |
| Skyfield, jplephem by Brandon Rhodes | dependencies | MIT |
| NumPy | dependency | BSD-3-Clause |
| pytz, timezonefinder | dependencies | MIT |
| NASA JPL DE440 planetary ephemeris | downloaded by `python -m twinsky_engine.fetch`, not shipped | Public data from NASA/JPL (Park et al. 2021) |
| ΔT table (`src/twinsky_engine/data/delta_t.json`) | shipped | Built from published data: Morrison, Stephenson, Hohenkerk & Zawilski 2021; U.S. Naval Observatory; IERS UT1 observations |

The Lahiri (True Chitra) ayanamsa follows its published definition with the Hipparcos position of Spica.
