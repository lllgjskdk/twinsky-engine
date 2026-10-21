"""Write docs/sample-bazi.svg: a fictional birth's BaZi chart as a standalone image (the README's picture).

The engine's SVG leaves colours to the page it sits in; this adds TwinSky's dark theme so the file
shows on its own, in a browser or on GitHub.
"""

import re
from pathlib import Path

from twinsky_engine import bazi_chart, birth, render_bazi_chart

THEME = (
    "<style>"
    "text{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans CJK SC','Microsoft YaHei',sans-serif}"
    ".chart-svg rect{fill:#101010;stroke:rgba(255,255,255,.25)}"
    ".chart-title,.stem,.branch{fill:#f5f5f7}"
    ".chart-title{font-size:18px;font-weight:600}"
    ".pillar-label,.section-label,.ten-god,.hidden,.meta,.tiny{fill:rgba(245,245,247,.56)}"
    "</style>"
)

me = birth("1994-05-12T09:30", lat=1.29, lng=103.85, gender="female", timezone="Asia/Singapore")
svg = render_bazi_chart(bazi_chart(me))
# The annual pillars are listed by the page around the chart, not drawn; drop their heading and the space below.
svg = re.sub(r'<text[^>]*class="section-label">流年[^<]*</text>', "", svg)
svg = svg.replace('viewBox="0 0 530 585"', 'viewBox="0 0 530 500"', 1)
head, rest = svg.split(">", 1)
standalone = (head.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1) + ">" + THEME
              + '<rect width="100%" height="100%" style="fill:#080808;stroke:none"/>' + rest)
target = Path(__file__).resolve().parent.parent / "docs" / "sample-bazi.svg"
target.write_text(standalone, encoding="utf-8")
print(f"wrote {target}")
