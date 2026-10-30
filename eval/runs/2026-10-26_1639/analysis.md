# Stage 1 analysis: Opus 5.5 (medium / high) vs Sonnet 5.5 (high) on 27 dev questions

Run `2026-10-26_1639`. Raw records: `opus.jsonl`, `opus-high.jsonl`, `sonnet.jsonl`. Generated tables: `summary.md`.
Fact-checker: Opus 5.5 (high). Claude reviewed every flag against the filings (2026-10-26) and sorted it by severity.

## Headline
| Config | Strict accuracy | Answers with a **serious** error | Coverage | Median time | Words | Searches | Thinking tokens | ≈API $ |
|---|---|---|---|---|---|---|---|---|
| Opus, medium | 18/27 | **5** | 93% | 18 s | 291 | 2.4 | 234 | $3.32 |
| Opus, high | 16/27 | **5** | 94% | 19 s | 301 | 2.6 | 325 | $3.63 |
| **Sonnet, high** | **23/27** | **2** | 89% | **14 s** | 266 | 1.8 | 35 | **$1.30** |

- **Serious** = a wrong or unsourced fact, number or conclusion a non-expert could rely on.
- **Minor** = imprecise wording, hedged interpretation the filing doesn't back, or a definitional nuance.

## Serious errors (verified)
| Config | # | Error |
|---|---|---|
| Opus medium | 47 | "$95.6B costs → $57.0B net income": silently skips the $14.2B provision + taxes (a $30B gap) |
| Opus medium | 49 | "More than half of deposits from businesses": CIB is 47% (p105) |
| Opus medium | 37 | "Three straight years of faster growth": 2023 was a slowdown |
| Opus medium | 18 | Follow-up question with a false premise: "why did gross margin go up FY24→FY26" (72.7% → 71.1%) |
| Opus medium | 38 | Anthropic gains stated as all of $13.3B; filing says "primarily" (AMZN p45) |
| Opus high | 28 | "Roughly 2.3 billion devices": number not in the filing (outside knowledge) |
| Opus high | 38 | "Margins nearly doubled": 6.4% → 11.2% (~1.75×) |
| Opus high | 22 | Inventory reason for Embedded's 2024 drop applied to 2025 (filing: "end market demand remained mixed") |
| Opus high | 47 | Whole $35.8B Markets revenue put inside noninterest revenue (it spans NII too) |
| Opus high | 41 | Tesla's 2023 valuation-allowance release called a "tax credit" |
| Sonnet | 22 | "The filing doesn't say which parts are one-time": it does ($853M tax benefit, p70) |
| Sonnet | 52 | States "latest fiscal year" rule, then ranks NVIDIA above Microsoft; "~$6.5B OpenAI gain" vs filing's $5.0B net-income effect |

## Minor flags (summary)
Opus medium 8 (outside-knowledge interpretation #17; "fees grew faster" #47; "mainly from" #47; client assets vs deposits #49; oversimplified reserve drivers #50; NCI definition #54; "only AMD names Intel" + Intel FY end #21) · Opus high 8 (hedged interpretation #17, #37×2, #49×2, #52; "largest private employers" #40; NCI definition #54) · Sonnet 2 ("datacenter-type" lease label #33; Google calendar year #56).

## Findings
1. **Sonnet is the most accurate on both measures:** strict (23/27) and serious errors (2 vs 5). It's also the fastest and ~2.5× cheaper in API terms, and lighter on the Pro plan.
2. **More effort made Opus worse, not better.** Opus-high wrote longer answers with more interpretation and more outside knowledge (#28, #40). For a user who can't spot mistakes, "explaining more" is a risk, not a feature.
3. **Opus covers slightly more of the answer key** (93–94% vs 89%). Sonnet's misses are omissions (e.g. #22's one-offs), which are less dangerous than wrong statements.
4. **Self-preference check:** the checker is Opus, so any bias should *favour* Opus. Opus scoring worse strengthens the result.
5. **Error types to fix in the prompt (all models):** outside facts/numbers inside "What this might mean"; follow-up questions with unverified premises; loose quantifiers ("nearly doubled", "more than half", "mainly").
6. **Caveats:** 27 questions; one run each; text-only index (no Docling tables yet); one fact-checker. Fact-check token averages in `summary.md` cover only re-checked/resumed rows (checker tokens weren't recorded at first).
