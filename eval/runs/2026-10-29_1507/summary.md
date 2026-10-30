## Overall
| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |
|---|---|---|---|---|---|---|---|---|---|---|
| sonnet:high (claude-sonnet-5-5) | **10/10** | 0 | 0 | 96% | 16s / 21s | 278 | 2.3 | 10/10 | 10/10 | 0.89 |

## Tokens (average per question)
| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |
|---|---|---|---|---|---|
| sonnet:high | 19,959 | 18,334 | 1,237 | 151 | 22,126 |

## Accuracy per company
| Company | sonnet:high |
|---|---|
| AMD | 4/4 |
| Cross-company | 2/2 |
| NVIDIA | 4/4 |

## Question by question
| # | Company | sonnet:high (verdict · coverage · time) |
|---|---|---|
| 1 | NVIDIA | ✅ · 100% · 14s |
| 2 | NVIDIA | ✅ · 100% · 13s |
| 3 | AMD | ✅ · 100% · 17s |
| 4 | AMD | ✅ · 75% · 21s |
| 8 | AMD | ✅ · 100% · 21s |
| 9 | NVIDIA | ✅ · 100% · 16s |
| 10 | AMD | ✅ · 100% · 20s |
| 12 | NVIDIA | ✅ · 85% · 16s |
| 14 | Cross-company | ✅ · 100% · 21s |
| 15 | Cross-company | ✅ · 100% · 14s |

## Flagged claims
- none
