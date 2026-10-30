# Model comparison scorecard

One table per eval run, by metric. Source records: `eval/runs/<run>/*.jsonl`; severity review in `eval/runs/<run>/analysis.md`.
"Pass" = the Opus-high fact-checker found no wrong or unsupported claim (strict). Flagged claims = wrong + unsupported.

## Stage 1: run `2026-10-26_1639` (27 dev questions, text-only index, before the prompt fixes)

| Evaluation metric | Test prompt type (our dev questions) | Sonnet 5.5 high | Opus 5.5 medium | Opus 5.5 high | Winning model |
|---|---|---|---|---|---|
| **Numerical precision** | Questions tagged `table` or `calc` (13: #7, 11, 26, 28, 31, 33, 37, 38, 41, 44, 49, 50, 54), e.g. "How much money does Apple make from iPhones?" | **12/13 pass**, 1 flagged claim (#33, minor: lease label). Coverage 91% | 8/13 pass, 6 flagged claims (#37 "three straight years", #49 "more than half" = 47%, #38 "primarily" → "all"). Coverage 92% | 7/13 pass, 8 flagged claims (#38 "nearly doubled" = 1.75×, #28 "2.3 billion devices" not in filing). Coverage 94% | **Sonnet** |
| **Visual chart reading** | 1 question tagged `chart` (#17) | 1/1 pass | 0/1 (outside knowledge in interpretation, not a chart misread) | 0/1 (same) | **Not tested.** The index is text-only, so no model saw a chart image. Needs chart questions + multimodal (page images) to measure |
| **Cross-report synthesis** | Cross-company questions (4: #6, 25, 52, 54), e.g. "Who earned the most in 2025?" | 3/4 pass, 3 flagged claims. **Serious: #52** (stated "latest fiscal year", ranked by calendar year; OpenAI gain ~$6.5B vs filing's $5.0B). Coverage 72% | 3/4 pass, 1 flagged claim (#54, minor: NCI definition). Coverage 87% | 2/4 pass, 2 flagged claims (#52, #54). Coverage 88% | **Opus medium** (Sonnet covers less and had a serious error here) |
| **Latency / cost** | All 27 | **14.2 s** median (p90 16.7 s) · **$0.048** per answer | 18.2 s (p90 26.1 s) · $0.123 | 19.2 s (p90 25.6 s) · $0.134 | **Sonnet** (≈1.3× faster, ≈2.6× cheaper) |
| **Overall** | All 27 | **23/27 pass · 2 serious errors** | 18/27 · 5 serious | 16/27 · 5 serious | **Sonnet** (D-021) |

Notes:
- Cost = API-equivalent list price (Claude Code reports it). On Pro there's no bill; it shows how much plan usage each answer takes.
- Latency = whole answer (Claude Code in non-streaming eval mode); time to first word was almost the same, since the agent writes only once its research is done.
- Small samples (13 / 4 / 1 questions) and one run each: a per-metric "winner" is a direction, not proof.

## Price and speed trade-off (list prices checked 2026-10-27 at platform.claude.com/docs/en/about-claude/pricing)

| Metric | Claude Sonnet 5.5 | Claude Opus 5.5 | The PM trade-off analysis |
|---|---|---|---|
| **Input price / MTok** | $2.00 | $4.00 | Sonnet is 50% cheaper per input token. IndexIt doesn't send whole 10-Ks: RAG sends only the passages found, so input is ~17k tokens (Sonnet) to ~27k (Opus) per answer. |
| **Cached input** (Claude Code caches automatically) | write $4.00 (1 h) · read $0.10 | write $8.00 (1 h) · read $0.20 | **Cache writes are most of the bill (~75%)**: the system prompt + tool results are written to cache on each question. |
| **Output price / MTok** | $10.00 | $20.00 | Opus costs double per output token *and* wrote more (1,268–1,409 vs 1,017 tokens; 291–301 vs 266 words). |
| **Measured tokens per answer** (stage 1, 27 dev) | 17.4k input (9.3k cache write + 8.2k cache read) · 1.0k output · 35 thinking | medium: 27.3k input · 1.3k output · 234 thinking<br>high: 29.5k input · 1.4k output · 325 thinking | Opus searched more (2.4–2.6 vs 1.8 searches), so it read more passages: **~1.6× the input tokens**. |
| **Measured cost per answer** | **$0.048** | medium $0.123 · high $0.134 | Opus is **~2.6× the cost**: 2× the price × ~1.3× the tokens. |
| **Latency / speed** | **Fast: 14 s median** (p90 17 s) | Moderate: 18–19 s median (p90 26 s) | Sonnet is ~4–5 s faster per answer and more predictable (smaller p90). |
| **At 600 questions/month** (20/day) | ≈ $29 | ≈ $74–80 | Only matters for the future API version. **On Pro, the bill is $0**; these costs show how much plan usage each answer takes (Sonnet lets you ask ~2.6× more before the session limit). |

Notes:
- Measured costs are Claude Code's own API-equivalent figures, and they match the list prices (e.g. Sonnet: 9,268 × $4 + 8,166 × $0.10 + 1,017 × $10 per MTok ≈ $0.048).
- Excludes the eval's fact-checker (Opus high), which runs only during evals.
- A future direct-API version would have a smaller prompt than Claude Code's, so costs per answer would likely be lower; re-measure then.

## Stage 2: run `2026-10-27_1854`: Sonnet 5.5 high + prompt fixes + Docling tables (27 dev questions)

| Evaluation metric | Test prompt type | Sonnet high, stage 1 | **Sonnet high, stage 2** | Change |
|---|---|---|---|---|
| **Numerical precision** | 13 `table`/`calc` questions | 12/13 pass, 1 flagged claim | **13/13 pass, 0 flagged claims** | ✅ better |
| **Visual chart reading** | 1 `chart` question (#17) | 1/1 | 1/1 | Still not really tested (text-only) |
| **Cross-report synthesis** | 4 cross-company questions | 3/4, 72% coverage, 1 serious (#52) | 3/4, **93% coverage**; #52 fixed; #25 fails (see below) | ✅ better |
| **Overall accuracy** | All 27 | 23/27 · 4 wrong + 2 unsupported claims | **25/27 · 0 wrong + 3 unsupported** | ✅ better |
| **Serious errors** (Claude-verified) | All 27 | 2 (#22, #52) | **0 serious, 1 moderate (#25)** | ✅ better |
| **Coverage** | All 27 | 89% | **93%** (now equal to Opus) | ✅ better |
| **Latency** | All 27 | 14 s median · p90 17 s | 16 s median · p90 20 s | ⚠️ +2 s |
| **Cost per answer** (API-equivalent) | All 27 | $0.048 | **$0.094** | ⚠️ ~2× (≈ Opus stage 1) |
| **Agent depth** | All 27 | 48 searches · 0 page reads · 12/27 with ≤1 tool call | 62 searches · 1 page read · 7/27 with ≤1 tool call | Searches more |

**Were stage 1's errors resolved?** (Claude checked each answer against the filings)
- **#52 ✅ fixed.** It states the calendar-2025 rule once and applies it to every company (NVIDIA $120.1B leads), shows Microsoft's newer June-2026 year separately ($133.7B), and now quotes the filing's **$5.0B** OpenAI effect (was ~$6.5B).
- **#22 ✅ no false claim now**, but it still **leaves out the $853M one-time tax benefit** (55% coverage). The error has become an omission: safer, but the key "spike vs sustainable" point is still missing.
- **#33, #56 ✅** now pass.

**New failures**
- **#18 (minor):** "fiscal 2024 was a 52-week year, so the comparison isn't distorted". It's true for FY2024, but the answer also compares with FY2023, which the cited page doesn't cover.
- **#25 (moderate):** "The filings don't show AMD investing cash in AI customers the way NVIDIA does." It's literally true, but it misleads: AMD holds **$1.3B of private-company stakes** (p73), and the filing doesn't say whether they're customers. Stage 1 omitted this too, but didn't make the negative claim. **Cause: retrieval.** Sonnet searched for "AMD strategic investments in customers or ventures" (it followed the new rule), but the filing uses the accounting term "non-marketable equity securities", and that search doesn't return p73 (checked). It's the JPMorgan-style jargon gap again. Left unfixed for now: a prompt hint for this one term would be overfitting to dev.

**Why the cost doubled:** each search now carries the page tables (~2k tokens), Sonnet searched more (2.3 vs 1.8 per question), and it thought a little more (255 vs 35 thinking tokens). Input written to cache went from 9.3k to 21k tokens per answer. Lever if needed: lower `TABLE_BUDGET_CHARS` (16k now) or attach tables only for the top pages.

## Stage 2 test set: run `2026-10-27_1911`: same system, 19 held-out test questions (run once)

| Evaluation metric | Test prompt type | **Sonnet high, stage 2 (test)** | Same system on dev |
|---|---|---|---|
| **Overall accuracy** (strict) | All 19 | **15/19** · 0 wrong + 3 unsupported claims | 25/27 |
| **Serious errors** (wrong fact or number) | All 19 | **0** | 0 |
| **Wording overreach** (unsupported, minor–moderate) | | 3: #23 opening line calls NVIDIA Data Center "not a stable source" (filing lists risks, doesn't say unstable) · #27 Apple sales "hit a record" (filings show 5 years only) · #43 Tesla credits "almost all likely falls through to profit" (filing: "negligible incremental costs"; the key flags "pure profit") | 2 (#18, #25) |
| **Broken output** | | **1: #53**: Sonnet *typed* its 7 search calls as text instead of running them, then stopped. The user would have seen raw markup. 1 in ~140 answers across all runs | 0 |
| **Coverage** | All 19 | 89% (90% excluding #53) | 93% |
| **Cross-report synthesis** | 4 cross-company | 3/4 (the failure is #53's broken output; #55 debt comparison passed) | 3/4 |
| **Latency** | All 19 | 16 s median · p90 22 s (#55: 78 s, 7-company debt question) | 16 s |
| **Cost per answer** (API-equivalent) | All 19 | $0.114 | $0.094 |

**Reading it:** on questions never used for tuning, IndexIt made **no wrong factual claims** across 19 answers. Every flag is an *overreach in wording* (a superlative or a too-strong summary line), typically in the opening sentence, while the bullets below are right. Strict accuracy drops from 93% (dev) to 79% (test), the usual gap between tuned and unseen questions. That makes **~80% strict / 0 serious** the honest estimate for now.
**Don't tune on these test questions.** Any fix must be generic (e.g. an output check), and future test scores are slightly optimistic now that we've seen these answers.

## Stage 3: runs `2026-10-29_1451` (dev 27) + `2026-10-29_1507` (extra 10): Sonnet high + wording rules

| Metric | Stage 2 dev (before wording rules) | **Stage 3 dev** | **Stage 3 extra** |
|---|---|---|---|
| Strict accuracy | 25/27 | **24/27** | **10/10** |
| Wrong / unsupported claims | 0 / 3 | 1 / 2 | 0 / 0 |
| Coverage | 93% | 92% | 96% |
| Median time | 16 s | 16 s | 16 s |
| Format OK / 3 follow-ups | 27/27 | 27/27 | 10/10 |

**Failures (different questions from last time):**
- **#6 (moderate, wrong period):** offered NVIDIA's year ended Jan 2025 as a "calendar-year alternative" to AMD's 2025. That year is roughly calendar **2024**. The main comparison was right.
- **#22 (overreach):** "Growth is accelerating, not one-off" stated as a fact bullet; the filing makes no such judgement. This is exactly the type the new rules target, so the rules didn't stop it here.
- **#35 (relationship direction):** called Microsoft a *customer* of OpenAI; the filing shows OpenAI paying Microsoft (Azure).
- Previous failures #18 and #25 now pass.

**Reading it:** overreach-type flags on dev went 2 → 1, and extra is clean. But with one run each, ±1–2 failures is within run-to-run noise: **no measurable change** from the wording rules. Each run fails a *different* 2–3 questions, roughly 1 answer in 10, with a mixed bag of causes (overreach, period, relationship direction). Coverage and format held, so the rules cost nothing. Kept.
