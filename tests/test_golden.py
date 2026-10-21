"""The package gives exactly what the TwinSky app gives (tests/golden.json, written by the app's export).

Moon and Ashtakoota tests need the DE440 excerpt: run `python -m twinsky_engine.fetch` first.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from twinsky_engine import ashtakoota, bazi_chart, birth, moon_longitude, render_bazi_chart
from twinsky_engine.ephemeris import ephemeris_file
from twinsky_engine.fetch import default_ephemeris_path

from summary import digest

GOLDEN = json.loads((Path(__file__).parent / "golden.json").read_text(encoding="utf-8"))
BIRTHS = {item["name"]: item for item in GOLDEN["births"]}
NEEDS_EPHEMERIS = pytest.mark.skipif(not ephemeris_file(default_ephemeris_path()).is_file(),
                                     reason="run `python -m twinsky_engine.fetch` to download the DE440 excerpt")


def _birth(name):
    item = BIRTHS[name]
    return birth(item["datetime"], lat=item["lat"], lng=item["lng"], timezone=item["timezone"], gender=item["gender"])


@pytest.mark.parametrize("name", BIRTHS)
def test_bazi_matches_the_app(name):
    chart = bazi_chart(_birth(name))
    assert chart.pillars == GOLDEN["charts"][name]["pillars"]
    assert digest(chart.to_dict()) == GOLDEN["charts"][name]["bazi"]
    assert "<svg" in render_bazi_chart(chart)


@NEEDS_EPHEMERIS
@pytest.mark.parametrize("name", BIRTHS)
def test_moon_matches_the_app(name):
    assert moon_longitude(_birth(name), BIRTHS[name]["timezone"]) == pytest.approx(GOLDEN["moons"][name], abs=1e-8)


@NEEDS_EPHEMERIS
@pytest.mark.parametrize("match", GOLDEN["matches"], ids=lambda match: f"{match['groom']}+{match['bride']}")
def test_ashtakoota_matches_the_app(match):
    result = ashtakoota(_birth(match["groom"]), _birth(match["bride"]), groom_timezone=BIRTHS[match["groom"]]["timezone"],
                        bride_timezone=BIRTHS[match["bride"]]["timezone"])
    assert {row["key"]: row["score"] for row in result["kutas"]} == match["scores"]
    assert result["total"] == sum(match["scores"].values()) and result["max"] == 36
