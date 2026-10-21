# Accuracy

Everything here is exported unchanged from the TwinSky app; `tests/golden.json` proves the package gives the app's results.

## BaZi

Month pillars change at the exact solar terms from lunar-python (6tail). The day changes at midnight of the birth's effective time (23:00–24:00 stays on the same day by default; `zishi_rule="switch"` or `"split"` for the other conventions). By default the effective time is true solar time from the birth longitude; `SolarTimeMode.STANDARD` and `SolarTimeMode.LONGITUDE_EOT` are available. Luck pillars start at the traditional three-days-per-year age from the nearest jie term, forward or backward by gender and the year stem's polarity.

## Ashtakoota

Scores follow AstroSage's Guna Milan. Varna, Tara, Gana, Bhakoot and Nadi use dashaflow's rules; Yoni, Vashya and Graha Maitri use the package's own tables, because dashaflow's differ from AstroSage there. In the app, 20 fictional pairs were checked koota by koota against AstroSage and all matched. The Moon is the sidereal Moon with the True Chitra ayanamsa from DE440; a birth time near a nakshatra or sign boundary can change the score, so give exact times.

## Ephemeris: JPL DE440 against Swiss Ephemeris

The ephemeris reads NASA JPL DE440 through Skyfield, with ΔT from the same published table Swiss Ephemeris 2.10 used (Morrison et al. 2021 before 1955, USNO 1955–1972, IERS observations since). 229 charts, this ephemeris minus Swiss Ephemeris 2.10.03:

| Quantity | Max | 95% of charts |
|---|---|---|
| Moon (sidereal) | 0.0036″ | 0.0025″ |
| Sun | 0.0017″ | 0.0012″ |
| Mercury / Venus / Mars | 0.0020″ / 0.0062″ / 0.0036″ | ≤ 0.0026″ |
| Jupiter / Saturn | 0.0009″ / 0.0012″ | ≤ 0.0006″ |
| True node | 0.075″ | 0.012″ |
| Ascendant | 0.0020″ | 0.0007″ |
| Sunrise and sunset | 0.002 s | — |

Over those charts no sign, nakshatra or pada changed. The excerpt covers 1760–2560.
