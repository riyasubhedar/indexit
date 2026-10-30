## Overall
| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |
|---|---|---|---|---|---|---|---|---|---|---|
| sonnet:high (claude-sonnet-5-5) | **25/27** | 0 | 3 | 93% | 16s / 20s | 277 | 2.3 | 27/27 | 27/27 | 2.54 |

## Tokens (average per question)
| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |
|---|---|---|---|---|---|
| sonnet:high | 21,081 | 10,806 | 1,347 | 255 | 30,979 |

## Accuracy per company
| Company | sonnet:high |
|---|---|
| AMD | 3/3 |
| Amazon | 3/3 |
| Apple | 3/3 |
| Cross-company | 3/4 |
| JPMorgan Chase | 3/3 |
| Microsoft | 3/3 |
| NVIDIA | 2/3 |
| Tesla | 3/3 |
| Unanswerable | 2/2 |

## Question by question
| # | Company | sonnet:high (verdict · coverage · time) |
|---|---|---|
| 6 | Cross-company | ✅ · 100% · 16s |
| 7 | NVIDIA | ✅ · 100% · 17s |
| 11 | NVIDIA | ✅ · 100% · 16s |
| 17 | AMD | ✅ · 100% · 13s |
| 18 | NVIDIA | ❌ 0w/1u · 100% · 14s |
| 19 | AMD | ✅ · 100% · 12s |
| 21 | Unanswerable | ✅ · 100% · 12s |
| 22 | AMD | ✅ · 55% · 26s |
| 25 | Cross-company | ❌ 0w/2u · 70% · 19s |
| 26 | Apple | ✅ · 100% · 14s |
| 28 | Apple | ✅ · 100% · 16s |
| 30 | Apple | ✅ · 85% · 20s |
| 31 | Microsoft | ✅ · 100% · 13s |
| 33 | Microsoft | ✅ · 80% · 18s |
| 35 | Microsoft | ✅ · 100% · 16s |
| 37 | Amazon | ✅ · 100% · 17s |
| 38 | Amazon | ✅ · 100% · 18s |
| 40 | Amazon | ✅ · 100% · 11s |
| 41 | Tesla | ✅ · 70% · 17s |
| 44 | Tesla | ✅ · 50% · 16s |
| 45 | Tesla | ✅ · 100% · 15s |
| 47 | JPMorgan Chase | ✅ · 100% · 18s |
| 49 | JPMorgan Chase | ✅ · 100% · 15s |
| 50 | JPMorgan Chase | ✅ · 100% · 15s |
| 52 | Cross-company | ✅ · 100% · 23s |
| 54 | Cross-company | ✅ · 100% · 17s |
| 56 | Unanswerable | ✅ · 100% · 14s |

## Flagged claims
- **sonnet:high #18** (NVIDIA) UNSUPPORTED: Fiscal 2024 was a 52-week year, so the comparison with other years isn't distorted by an extra week → NVIDIA FY2026 10-K p.56 confirms only that fiscal 2026, 2025 and 2024 were 52-week years. The answer also compares fiscal 2024 with fiscal 2023, and the cited page says nothing about how many weeks fiscal 2023 had. The 52-week fact is right, but the broader 'not distorted' conclusion goes a little beyond the cited evidence.
- **sonnet:high #25** (Cross-company) UNSUPPORTED: The filings don't show AMD investing cash in AI customers the way NVIDIA does. → This is technically literal, but it misleads by omission. The AMD FY2025 10-K (p.73) shows AMD holding $1.3B of private, early-stage company stakes (up from $468M) and does not say whether those companies are customers. A non-expert will read this as 'AMD doesn't invest in its customers,' which the answer key specifically flags as an overclaim. The answer should say AMD does have private investments, and the filing doesn't say who they are.
- **sonnet:high #25** (Cross-company) UNSUPPORTED: Both tie a customer's purchases to the chipmaker's own money or shares. → For AMD this holds: the warrant vests on GPU purchase milestones. For NVIDIA, the filing only says its investees include AI model makers that buy its products. It never says the investments are tied to those purchases. The interpretation section labels this as the answer's own reading, but it goes beyond what the NVIDIA filing says.
