## Overall
| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |
|---|---|---|---|---|---|---|---|---|---|---|
| sonnet:high (<synthetic>, claude-sonnet-5-5) | **15/19** | 0 | 3 | 89% | 16s / 22s | 281 | 2.6 | 18/19 | 18/19 | 2.16 |

## Tokens (average per question)
| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |
|---|---|---|---|---|---|
| sonnet:high | 24,842 | 46,454 | 1,436 | 268 | 30,177 |

## Accuracy per company
| Company | sonnet:high |
|---|---|
| AMD | 2/2 |
| Amazon | 2/2 |
| Apple | 1/2 |
| Cross-company | 3/4 |
| JPMorgan Chase | 2/2 |
| Microsoft | 2/2 |
| NVIDIA | 1/2 |
| Tesla | 1/2 |
| Unanswerable | 1/1 |

## Question by question
| # | Company | sonnet:high (verdict · coverage · time) |
|---|---|---|
| 5 | Cross-company | ✅ · 100% · 21s |
| 13 | AMD | ✅ · 100% · 15s |
| 16 | NVIDIA | ✅ · 100% · 13s |
| 20 | Unanswerable | ✅ · 100% · 15s |
| 23 | NVIDIA | ❌ 0w/1u · 100% · 19s |
| 24 | AMD | ✅ · 85% · 14s |
| 27 | Apple | ❌ 0w/1u · 95% · 16s |
| 29 | Apple | ✅ · 75% · 16s |
| 32 | Microsoft | ✅ · 100% · 14s |
| 34 | Microsoft | ✅ · 100% · 16s |
| 36 | Amazon | ✅ · 100% · 16s |
| 39 | Amazon | ✅ · 90% · 14s |
| 42 | Tesla | ✅ · 100% · 20s |
| 43 | Tesla | ❌ 0w/1u · 80% · 16s |
| 46 | JPMorgan Chase | ✅ · 100% · 14s |
| 48 | JPMorgan Chase | ✅ · 100% · 22s |
| 51 | Cross-company | ✅ · 65% · 15s |
| 53 | Cross-company | ❌ 0w/0u · 0% · 11s |
| 55 | Cross-company | ✅ · 100% · 78s |

## Flagged claims
- **sonnet:high #23** (NVIDIA) UNSUPPORTED: Opening line: Data Center is 'AI-related and therefore not a stable, steady source' → This is a slight overreach. The filing does not call the revenue unstable; it lists risks. The answer's own later wording ('doesn't describe this revenue as steady or locked in') fits the filing better. It is not a crash prediction, but it leans less balanced than the answer key.
- **sonnet:high #27** (Apple) UNSUPPORTED: Sales hit a record → The available filings only show net sales for fiscal 2021–2025. Nothing in them calls fiscal 2025 an all-time record. The answer later correctly narrows this to 'the highest of these five years', but the opening line goes beyond the evidence.
- **sonnet:high #43** (Tesla) UNSUPPORTED: So almost all of the revenue likely falls through to profit. → The filing (Tesla FY2025 10-K, p.59) only says the credits have 'negligible incremental costs'. It never says the revenue falls through to profit. The answer key specifically marks calling credits 'pure profit' as an error. The answer hedges with 'likely' and ties the point to the filing's wording, so it is a borderline inference rather than a contradiction.
