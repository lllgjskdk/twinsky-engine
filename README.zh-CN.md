<p align="center">
  <a href="https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine"><img src="docs/twinsky-banner.png" alt="TwinSky：同一个时刻，两套命运坐标" width="100%"></a>
</p>

<p align="center">
  <a href="https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine"><img src="https://img.shields.io/badge/%E5%85%8D%E8%B4%B9%E6%8E%92%E7%9B%98-twinsky--ai.com-111111?style=flat-square" alt="免费排盘"></a>
  <a href="https://github.com/lllgjskdk/twinsky-engine/actions/workflows/tests.yml"><img src="https://github.com/lllgjskdk/twinsky-engine/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-111111?style=flat-square" alt="MIT"></a>
</p>

# TwinSky Engine

**Python 的八字排盘、36 分合婚（Ashtakoota）与 NASA JPL 星历。MIT 许可，不依赖 Swiss Ephemeris。**

> **想要解读，而不只是盘面？** 在 [TwinSky](https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine) 免费排出你的八字与印度占星双盘，再用自己的命盘向 AI 提问事业、感情与时机；每个回答都标出依据来自盘上的哪一柱、哪一宫、哪一段运。本仓库是它开源的那一部分。

[English](README.md) · [准确度说明](docs/ACCURACY.md) · [去 TwinSky 免费排盘](https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine)

<p align="center"><img src="docs/sample-bazi.svg" alt="twinsky_engine 画出的八字盘：四柱、藏干十神、小运与大运" width="460"></p>

```python
from twinsky_engine import birth, bazi_chart, ashtakoota, render_bazi_chart

me = birth("1994-05-12T09:30", lat=1.29, lng=103.85, gender="female", timezone="Asia/Singapore")
chart = bazi_chart(me)
chart.pillars        # {'year': '甲戌', 'month': '己巳', 'day': '戊戌', 'hour': '丙辰'}
svg = render_bazi_chart(chart)

him = birth("1985-12-01T23:40", lat=40.71, lng=-74.01, gender="male", timezone="America/New_York")
ashtakoota(him, me, groom_timezone="America/New_York", bride_timezone="Asia/Singapore")["total"]   # 27.0 / 36
```

## 包含什么

| 模块 | 内容 |
|---|---|
| 八字 | 四柱（月柱按精确节气）、藏干、十神、司令；大运（含起运岁数）、流年、小运；流月流日日历 |
| 真太阳时 | 经度时差（默认）、标准时、经度加均时差；IANA 时区，含历史夏令时 |
| 36 分合婚 | 按双方本命月亮（True Chitra 岁差）计算八项：Varna、Vashya、Tara、Yoni、Graha Maitri、Gana、Bhakoot、Nadi |
| 盘图 | 八字盘与细节的 SVG |
| `twinsky_engine.ephemeris` | 与 pyswisseph 接口兼容的子集，基于 Skyfield + NASA JPL DE440，可单独使用 |

## TwinSky 在此之上做了什么

引擎负责算出盘；[TwinSky](https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine) 是在它之上的完整产品：

- **一个问题，两套体系**：八字看整体格局与阶段，印度占星用分盘和大运细看你问的那个领域。
- **回答可以核对**：AI 读的是算好的盘，每个判断都能点开看到依据。
- **免费开始**：排盘、每日运势、择日和入门资料都免费；向 AI 提问用点数，注册就送。
- 支持简体中文、繁體中文、English、日本語、한국어。

**[去免费排盘 →](https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine)**

## 安装

```bash
pip install git+https://github.com/lllgjskdk/twinsky-engine
python -m twinsky_engine.fetch    # 只需一次：下载 DE440 节选（约 80 MB），合婚与星历要用
```

只排八字不需要下载星历。

## 许可

MIT，© 2026 Dreamie Tech Limited，可用于闭源与商业产品。八字与合婚是传统的解读体系；本引擎负责把它们算准，不代表预测必然成立，请勿据此做医疗、法律或投资决定。由 [TwinSky](https://twinsky-ai.com/?utm_source=github&utm_medium=readme_zh&utm_campaign=engine) 团队制作。
