## Overall
| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |
|---|---|---|---|---|---|---|---|---|---|---|
| sonnet:high (claude-sonnet-5-5) | **8/9** | 1 | 0 | 100% | 10s / 14s | 237 | 2.3 | 9/9 | 9/9 | 0.27 |

## Tokens (average per question)
| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |
|---|---|---|---|---|---|
| sonnet:high | 5,524 | 12,267 | 1,131 | 126 | 24,902 |

## Accuracy per company
| Company | sonnet:high |
|---|---|
| Cross-company | 8/9 |

## Question by question
| # | Company | sonnet:high (verdict · coverage · time) |
|---|---|---|
| 6 | Cross-company | ✅ · 100% · 10s |
| 14 | Cross-company | ✅ · 100% · 8s |
| 15 | Cross-company | ✅ · 100% · 14s |
| 52 | Cross-company | ✅ · 100% · 14s |
| 54 | Cross-company | ✅ · 100% · 10s |
| 56 | Cross-company | ✅ · 100% · 11s |
| 57 | Cross-company | ❌ 1w/0u · 100% · 10s |
| 58 | Cross-company | ✅ · 100% · 10s |
| 59 | Cross-company | ✅ · 100% · 12s |

## Flagged claims
- **sonnet:high #57** (Cross-company) WRONG: NVIDIA revenue 130,497 → 215,938 (about $ millions; the table doesn't state units) → The table explicitly states units: '(In millions, except per share data)', so the figures are $130,497M → $215,938M.
