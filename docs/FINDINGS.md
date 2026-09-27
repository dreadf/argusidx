# Findings scoreboard

The 19 popular market beliefs ArgusIDX tests against IDX data, and what happened
to each. One row per belief. **Yes** means it held up on data the search never
saw (an explore/holdout split fixed before the results were seen); **No** means
it did not; **Inconclusive** means the two halves disagreed or the sample was too
small. Every result is published, including the failures.

The method, samples, limits and every number behind a row are in
[`EXPERIMENT.md`](../EXPERIMENT.md). The app reads this table
(`pipeline/appdata/build_findings.py` turns it into `data/app/findings.json`), so
the page at `/temuan` and this file cannot disagree.

Verdict symbols: ✓ held up, ✗ did not hold up, ~ inconclusive. H-numbers are the
hypothesis ids in `EXPERIMENT.md`. Rows added after the first version (H6, H17,
H18) are listed with their test dates there.

| What people believe | | Verdict |
|---|---|---|
| Cheap stocks (low P/E) do better | **✓** | Yes, modestly (H5, H10) |
| High dividend yield means better returns | **✓** | Yes, modestly (H10, new 2026-09-12) |
| Small companies earn more | **✓** | Yes, but weaker than H5 alone suggested: H5's own diagnostic traced most of it to one 2025 rate-cut window; H10 finds the same direction re-confirmed across pooled years, so this is now on firmer footing than H5 alone (see EXPERIMENT.md) |
| Oversold (RSI < 30) means a bounce | **✗** | No (H14) |
| Price above its 200-day average keeps going up | **✗** | No (H14) |
| Recent 60-day momentum predicts next month | **✗** | No (H14) |
| High ROE (quality) predicts better returns | **✗** | No (H10) |
| High leverage (debt/equity) predicts worse returns | **✗** | No (H10) |
| A stock suspended for a sudden price spike keeps rising | ~ | **Mixed (H11)**: typically fades (roughly 2 in 3 underperform the index over the next 90 days), but a small minority keep running hard, skewing the average the other way. Reported as both, not one verdict; see EXPERIMENT.md |
| Fast revenue growth predicts better returns | **✗** | No: sign disagreed between explore and holdout (H10) |
| High payout ratio predicts worse returns | **✗** | No (H10) |
| A high payout ratio predicts a dividend cut | **✓** | **Yes, strongly (H4)**: cut rate rises from ~14% (lowest payout tercile) to ~66% (highest) in holdout |
| Combining a cheap/quality/leverage signal with a technical one beats either alone | **✗** | No, all 3 tested combinations null (H15) |
| Insiders selling before a price spike warns of a coming crash | **✗** | Not proven: reversed in holdout, but only 4 events, too few to conclude anything (H8) |
| Positive news coverage predicts a stock will rise | ~ | **Inconclusive (H9)**: sign flips between the two halves of the only data available; promising but not confirmed, needs a longer news history to re-test |
| Thin float means wild swings | **✗** | Backwards: wide float is bumpier (H1) |
| Rising profits mean a rising share price | **✗** | No: holdout correlation +0.002 (H17) |
| Foreign investors buying heavily means the price will rise | **✗** | No: top foreign-buy vs top foreign-sell list, next 5 trading days: holdout spread −0.03% (H6) |
| Insiders buying their own stock means the price will rise | **✗** | No: holdout mean +3.0% (p 0.25); the typical event did not beat the index (H18) |
