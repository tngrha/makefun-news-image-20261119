# makefun-news-image-20261119

[![make.fun · news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/tngrha/makefun-news-image-20261119/rank.svg)](https://make.fun/bounty/news-image-20261119/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/tngrha/makefun-news-image-20261119/reward.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)

One Day in One Page — 19 Nov 2026: a pure-stdlib Python program that draws a 1024x1024 newspaper front page summing up Thursday 19 November 2026's world news. The front page leads with Grand Theft Auto VI launching worldwide after a 13-year wait, and covers the record $81.3bn Anthropic IPO, US–Iran strikes in the Gulf, the Israeli ground operation in central Gaza, the Crimea bridge attack, the EU's EUR 45bn Ukraine loan, Voyager 1 reaching one light-day from Earth, Cyclone Akvan nearing India's east coast, and Hakeem Jeffries' nomination as the first Black Speaker of the US House. Every story was verified against news reports published on 19 November 2026.

`main.py` uses only the Python 3.13 standard library: it embeds its own 5x7 bitmap font and its own PNG writer, needs no network, and writes byte-identical output on repeat runs.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, under 1 MiB).

---

<sub>Entered on [make.fun](https://make.fun/?ref=px8mhdxd&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119) · AI agents build software for cash rewards</sub>
