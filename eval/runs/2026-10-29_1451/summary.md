## Overall
| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |
|---|---|---|---|---|---|---|---|---|---|---|
| sonnet:high (claude-sonnet-5-5) | **24/27** | 1 | 2 | 92% | 16s / 19s | 286 | 2.4 | 27/27 | 27/27 | 2.65 |

## Tokens (average per question)
| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |
|---|---|---|---|---|---|
| sonnet:high | 21,973 | 9,921 | 1,417 | 301 | 28,276 |

## Accuracy per company
| Company | sonnet:high |
|---|---|
| AMD | 2/3 |
| Amazon | 3/3 |
| Apple | 3/3 |
| Cross-company | 3/4 |
| JPMorgan Chase | 3/3 |
| Microsoft | 2/3 |
| NVIDIA | 3/3 |
| Tesla | 3/3 |
| Unanswerable | 2/2 |

## Question by question
| # | Company | sonnet:high (verdict · coverage · time) |
|---|---|---|
| 6 | Cross-company | ❌ 1w/0u · 95% · 16s |
| 7 | NVIDIA | ✅ · 100% · 19s |
| 11 | NVIDIA | ✅ · 100% · 17s |
| 17 | AMD | ✅ · 100% · 15s |
| 18 | NVIDIA | ✅ · 100% · 14s |
| 19 | AMD | ✅ · 100% · 16s |
| 21 | Unanswerable | ✅ · 70% · 15s |
| 22 | AMD | ❌ 0w/1u · 60% · 17s |
| 25 | Cross-company | ✅ · 55% · 19s |
| 26 | Apple | ✅ · 100% · 15s |
| 28 | Apple | ✅ · 100% · 16s |
| 30 | Apple | ✅ · 80% · 15s |
| 31 | Microsoft | ✅ · 100% · 13s |
| 33 | Microsoft | ✅ · 80% · 21s |
| 35 | Microsoft | ❌ 0w/1u · 100% · 14s |
| 37 | Amazon | ✅ · 100% · 14s |
| 38 | Amazon | ✅ · 100% · 17s |
| 40 | Amazon | ✅ · 100% · 12s |
| 41 | Tesla | ✅ · 67% · 16s |
| 44 | Tesla | ✅ · 83% · 15s |
| 45 | Tesla | ✅ · 100% · 15s |
| 47 | JPMorgan Chase | ✅ · 100% · 17s |
| 49 | JPMorgan Chase | ✅ · 100% · 16s |
| 50 | JPMorgan Chase | ✅ · 100% · 17s |
| 52 | Cross-company | ✅ · 100% · 25s |
| 54 | Cross-company | ✅ · 90% · 17s |
| 56 | Unanswerable | ✅ · 100% · 18s |

## Flagged claims
- **sonnet:high #22** (AMD) UNSUPPORTED: "Growth is accelerating, not one-off." (headline bullet under 'What the filing says') → The filing doesn't say whether growth is one-off or lasting. This is IndexIt's judgment, but it sits in the filing-facts section, close to calling growth sustainable as a fact (the answer key warns against this). It also clashes with the answer's own hedge ('I can't call it fully sustainable or a spike') and with filing data it cites: Data Center growth slowed from 94% to 32%, and Gaming swung from −58% (2024) to +51% (2025). The 14%→34% speed-up in total revenue is correct arithmetic (AMD FY2024 10-K p.60: 22,680→25,785; AMD FY2025 10-K p.68: 34,639).
- **sonnet:high #35** (Microsoft) UNSUPPORTED: Microsoft is a long-term partner of OpenAI, a major investor in it (about 25%) and a customer. / Microsoft is investor, customer and technology licensee. → No page I read describes Microsoft as a customer of OpenAI. The filing shows the reverse: Microsoft earns revenue from OpenAI ($24.1B in FY2026, p.60), and the risk factor on p.16 says partners like this are significant customers of Azure. The FY2025 10-K mentions 'reciprocal revenue-sharing arrangements', but that is not the same as Microsoft being a customer. A non-expert reader would likely get the direction of the relationship backwards.
- **sonnet:high #6** (Cross-company) WRONG: Calendar-year alternative: NVIDIA's year ended Jan 26, 2025 had revenue of $130,497 million. Against AMD's $34,639 million, that is about 3.8 times. → NVIDIA's year ended Jan 26, 2025 is fiscal 2025, which runs from late January 2024 to January 2025. It roughly matches calendar 2024, not 2025, so it is not a 'calendar-year alternative' for comparing against AMD's 2025. The answer key says using NVIDIA FY2025 ($130.5B) for 2025 is a fail. Labeling it as a valid alternative gets the period wrong and could mislead a non-expert, even though the main comparison is right. (The $130,497M figure and the 3.8x math are accurate.)
