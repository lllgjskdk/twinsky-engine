"""Print a birth's BaZi chart as JSON, or the Ashtakoota score of two births.

    python -m twinsky_engine 1994-05-12T09:30 --lat 1.29 --lng 103.85 --gender female --summary
    python -m twinsky_engine 1985-12-01T23:40 --lat 40.71 --lng -74.01 --gender male \\
        --match 1994-05-12T09:30 --match-lat 1.29 --match-lng 103.85
"""

from __future__ import annotations

import argparse
import json

from . import ashtakoota, bazi_chart, birth
from .timezone import resolve_timezone


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m twinsky_engine", description=__doc__.split("\n")[0])
    parser.add_argument("when", help="local birth time, e.g. 1994-05-12T09:30")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lng", type=float, required=True)
    parser.add_argument("--timezone", help="IANA name; looked up from the place when omitted")
    parser.add_argument("--gender", required=True, choices=("female", "male"), help="sets the direction of BaZi luck pillars")
    parser.add_argument("--summary", action="store_true", help="pillars and day master only")
    parser.add_argument("--match", metavar="WHEN", help="the other birth for Ashtakoota (this one is the groom if male)")
    parser.add_argument("--match-lat", type=float)
    parser.add_argument("--match-lng", type=float)
    parser.add_argument("--match-timezone")
    args = parser.parse_args()
    zone = args.timezone or resolve_timezone(args.lat, args.lng)
    value = birth(args.when, lat=args.lat, lng=args.lng, timezone=zone, gender=args.gender)
    if args.match:
        if args.match_lat is None or args.match_lng is None:
            parser.error("--match needs --match-lat and --match-lng")
        other_zone = args.match_timezone or resolve_timezone(args.match_lat, args.match_lng)
        other = birth(args.match, lat=args.match_lat, lng=args.match_lng, timezone=other_zone,
                      gender="female" if args.gender == "male" else "male")
        groom, bride = (value, other) if args.gender == "male" else (other, value)
        groom_zone, bride_zone = (zone, other_zone) if args.gender == "male" else (other_zone, zone)
        output = ashtakoota(groom, bride, groom_timezone=groom_zone, bride_timezone=bride_zone)
    else:
        four = bazi_chart(value)
        output = ({"timezone": zone, "pillars": four.pillars, "day_master": four.day_master} if args.summary
                  else {"timezone": zone, "bazi": four.to_dict()})
    print(json.dumps(output, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
