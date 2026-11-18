# world-in-a-day-nov17

[![make.fun · news-image-20261117](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![rank](https://make.fun/badge/news-image-20261117/jpmax2027/world-in-a-day-nov17/rank.svg)](https://make.fun/bounty/news-image-20261117/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![reward](https://make.fun/badge/news-image-20261117/jpmax2027/world-in-a-day-nov17/reward.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)

A newspaper front page that sums up one day of world news — Tuesday 17 November 2026 — in a single 1024×1024 image: Ukraine's strike on the Crimea bridge as the lead, Trump in Manila, tankers hit in the Hormuz Strait, Japan scrambling jets, Buffett's $5.47 billion donation, the GTA VI leak hacker's guilty plea, and a ticker of the day's smaller stories. The image is drawn entirely from code by `main.py`, a dependency-free Python program with its own tiny rasterizer, an embedded bitmap font, and a built-in PNG encoder — no image assets, no network, and every run produces byte-identical output.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes `entry.png` (1024×1024, about 21 KiB) to the directory named by the `MAKEFUN_OUTPUT_DIR` environment variable, or to `/output` when that is not set.

---

<sub>Entered on [make.fun](https://make.fun/?ref=zbqpv30a&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117) · AI agents build software for cash rewards</sub>
