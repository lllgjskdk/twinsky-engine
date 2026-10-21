"""Cast a fictional BaZi chart and score a fictional Ashtakoota pair."""

from twinsky_engine import ashtakoota, bazi_chart, birth

me = birth("1994-05-12T09:30", lat=1.29, lng=103.85, gender="female", timezone="Asia/Singapore")
four = bazi_chart(me)
print("BaZi pillars:", " ".join(four.pillars[name] for name in ("year", "month", "day", "hour")))
print("Day master:", four.day_master)
for period in four.da_yun[:4]:
    print(f"  luck pillar {period.pillar} ({period.stem_ten_god}) {period.start_year}–{period.end_year}")

him = birth("1985-12-01T23:40", lat=40.71, lng=-74.01, gender="male", timezone="America/New_York")
match = ashtakoota(him, me, groom_timezone="America/New_York", bride_timezone="Asia/Singapore")
print(f"Ashtakoota: {match['total']:g} / {match['max']}")
for row in match["kutas"]:
    print(f"  {row['name']:<14} {row['score']:g} / {row['max']}")
