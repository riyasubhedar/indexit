## Overall
| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |
|---|---|---|---|---|---|---|---|---|---|---|
| opus (claude-opus-5-5) | **18/27** | 6 | 7 | 93% | 18s / 26s | 291 | 2.4 | 27/27 | 27/27 | 3.32 |
| sonnet (claude-sonnet-5-5) | **23/27** | 3 | 3 | 89% | 14s / 17s | 266 | 1.8 | 27/27 | 27/27 | 1.30 |
| opus:high (claude-opus-5-5) | **16/27** | 4 | 9 | 94% | 19s / 26s | 301 | 2.6 | 27/27 | 27/27 | 3.63 |

## Tokens (average per question)
| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |
|---|---|---|---|---|---|
| opus | 12,968 | 15,536 | 1,289 | 234 | 44,963 |
| sonnet | 10,455 | 8,166 | 1,038 | 35 | 35,645 |
| opus:high | 14,021 | 16,692 | 1,430 | 325 | 26,167 |

## Accuracy per company
| Company | opus | sonnet | opus:high |
|---|---|---|---|
| AMD | 2/3 | 2/3 | 1/3 |
| Amazon | 1/3 | 3/3 | 0/3 |
| Apple | 3/3 | 3/3 | 2/3 |
| Cross-company | 3/4 | 3/4 | 2/4 |
| JPMorgan Chase | 0/3 | 3/3 | 1/3 |
| Microsoft | 3/3 | 2/3 | 3/3 |
| NVIDIA | 2/3 | 3/3 | 3/3 |
| Tesla | 3/3 | 3/3 | 2/3 |
| Unanswerable | 1/2 | 1/2 | 2/2 |

## Question by question
| # | Company | opus (verdict · coverage · time) | sonnet (verdict · coverage · time) | opus:high (verdict · coverage · time) |
|---|---|---|---|---|
| 6 | Cross-company | ✅ · 95% · 16s | ✅ · 90% · 14s | ✅ · 100% · 20s |
| 7 | NVIDIA | ✅ · 100% · 18s | ✅ · 100% · 15s | ✅ · 100% · 18s |
| 11 | NVIDIA | ✅ · 100% · 18s | ✅ · 100% · 13s | ✅ · 100% · 16s |
| 17 | AMD | ❌ 0w/1u · 100% · 20s | ✅ · 100% · 14s | ❌ 0w/1u · 100% · 17s |
| 18 | NVIDIA | ❌ 1w/0u · 100% · 19s | ✅ · 90% · 14s | ✅ · 100% · 15s |
| 19 | AMD | ✅ · 100% · 17s | ✅ · 100% · 12s | ✅ · 100% · 18s |
| 21 | Unanswerable | ❌ 1w/1u · 100% · 17s | ✅ · 100% · 6s | ✅ · 100% · 14s |
| 22 | AMD | ✅ · 60% · 23s | ❌ 1w/0u · 65% · 17s | ❌ 1w/0u · 60% · 23s |
| 25 | Cross-company | ✅ · 72% · 21s | ✅ · 50% · 16s | ✅ · 60% · 26s |
| 26 | Apple | ✅ · 100% · 17s | ✅ · 100% · 13s | ✅ · 100% · 17s |
| 28 | Apple | ✅ · 100% · 19s | ✅ · 100% · 14s | ❌ 0w/1u · 100% · 24s |
| 30 | Apple | ✅ · 100% · 20s | ✅ · 80% · 15s | ✅ · 100% · 19s |
| 31 | Microsoft | ✅ · 100% · 16s | ✅ · 100% · 12s | ✅ · 100% · 15s |
| 33 | Microsoft | ✅ · 80% · 20s | ❌ 0w/1u · 80% · 16s | ✅ · 83% · 30s |
| 35 | Microsoft | ✅ · 100% · 26s | ✅ · 100% · 14s | ✅ · 100% · 25s |
| 37 | Amazon | ❌ 1w/0u · 100% · 18s | ✅ · 100% · 14s | ❌ 0w/2u · 100% · 18s |
| 38 | Amazon | ❌ 0w/1u · 100% · 23s | ✅ · 100% · 12s | ❌ 1w/0u · 100% · 20s |
| 40 | Amazon | ✅ · 100% · 27s | ✅ · 100% · 12s | ❌ 0w/1u · 100% · 15s |
| 41 | Tesla | ✅ · 75% · 17s | ✅ · 70% · 15s | ❌ 0w/1u · 85% · 17s |
| 44 | Tesla | ✅ · 45% · 16s | ✅ · 60% · 14s | ✅ · 67% · 19s |
| 45 | Tesla | ✅ · 100% · 20s | ✅ · 100% · 15s | ✅ · 100% · 21s |
| 47 | JPMorgan Chase | ❌ 1w/2u · 100% · 27s | ✅ · 100% · 15s | ❌ 1w/0u · 100% · 26s |
| 49 | JPMorgan Chase | ❌ 1w/1u · 100% · 17s | ✅ · 100% · 14s | ❌ 0w/2u · 100% · 21s |
| 50 | JPMorgan Chase | ❌ 0w/1u · 100% · 16s | ✅ · 80% · 13s | ✅ · 100% · 20s |
| 52 | Cross-company | ✅ · 92% · 21s | ❌ 2w/1u · 60% · 20s | ❌ 0w/1u · 100% · 22s |
| 54 | Cross-company | ❌ 1w/0u · 90% · 18s | ✅ · 90% · 29s | ❌ 1w/0u · 90% · 20s |
| 56 | Unanswerable | ✅ · 100% · 17s | ❌ 0w/1u · 100% · 14s | ✅ · 100% · 17s |

## Flagged claims
- **opus #18** (NVIDIA) WRONG: Dig deeper question 2 assumes NVIDIA's gross margin went up from fiscal 2024 to fiscal 2026 ("Why did NVIDIA's gross margin go up from fiscal 2024 to fiscal 2026?") → Gross margin was about 72.7% in fiscal 2024 (44,301/60,922) and about 71.1% in fiscal 2026 (153,463/215,938), so it went slightly down. It rose to 75.0% in fiscal 2025 and then fell again. The question asks the reader to explain something that didn't happen.
- **opus #17** (AMD) UNSUPPORTED: The semiconductor group 'includes the companies that gained most from AI demand' → Page 62 of the AMD FY2025 10-K only gives index values. It doesn't name the index's members or credit AI demand for their gains, so this is outside knowledge (offered as interpretation).
- **opus #37** (Amazon) WRONG: That makes three straight years of faster growth: 13% in 2023, about 19% in 2024, then 20% in 2025. → The three years show only two speed-ups, from 13% to about 19% (2024) and then to 20% (2025). 2023 was a slowdown, not a speed-up. The answer says so itself later ("AWS growth sped up again after a slower 2023"). The accurate wording is "two straight years of faster growth".
- **opus #38** (Amazon) UNSUPPORTED: $13.3B of that came from gains on Amazon's investment in Anthropic, an AI company ($5.6B + $7.7B) → Page 45 of the Amazon.com FY2025 10-K says the $5.6B gain is 'primarily from' the Anthropic convertible notes. It says the $7.7B private-company upward adjustment is 'primarily from' the Anthropic nonvoting preferred stock. So Anthropic accounts for most of the $13.3B, but the filing doesn't say all of it. The answer overstates this. It should say 'mostly from Anthropic'.
- **opus #47** (JPMorgan Chase) WRONG: After $95.6 billion in operating costs and other charges, net income (profit) was $57.0 billion → The $95.6B is total noninterest expense (operating costs) only. Getting to $57.0B of net income also takes out a $14.2B provision for credit losses and income taxes. $182.4B − $95.6B = $86.8B (pre-provision profit), not $57.0B, so a reader would see a ~$30B gap with no explanation.
- **opus #47** (JPMorgan Chase) UNSUPPORTED: trading and fees grew faster [than lending income in 2025] → Markets (trading) revenue did grow 19%, but total noninterest revenue grew only 2%, slower than net interest income's 3%. Noninterest revenue excluding Markets fell 2%, while NII excluding Markets was flat (p.49). Some individual fee lines grew, but 'fees grew faster' overall doesn't hold up.
- **opus #47** (JPMorgan Chase) UNSUPPORTED: CCB net interest income of $58.2B came mainly from credit card balances and from deposits → p.68 names card revolving balances and deposit margin as the drivers of the 6% increase in NII. It doesn't break down where the $58.2B comes from, so 'mainly from' is an inference that stretches the source a little.
- **opus #49** (JPMorgan Chase) WRONG: Client assets of $7,118B are 'money invested through JPMorgan, not deposits' → Total client assets include a 'Custody/brokerage/administration/deposits' line of $2,327B, so some deposits are counted in client assets. It is not true that none of it is deposits.
- **opus #49** (JPMorgan Chase) UNSUPPORTED: More than half of the deposits come from businesses rather than individuals → The segment table on p.105 shows the Commercial & Investment Bank at $1,193.3B, which is about 47% of the $2,559.3B total, not more than half. The filing does not split deposits into business and individual totals. It only says uninsured deposits mainly reflect wholesale operating deposits. The 'more than half' figure is the answer's own inference, and it is stated as fact.
- **opus #50** (JPMorgan Chase) UNSUPPORTED: The rest [of the reserve increase beyond the $2.2B Apple Card amount] came from more card lending and a gloomier economic outlook. → This is a small oversimplification. On p.55 of the JPMorgan Chase FY2025 10-K, those drivers (card loan growth and changes in the macroeconomic outlook, partly offset by reduced borrower uncertainty) explain only the $3.3B consumer reserve addition. The $1.1B wholesale addition had different causes: growth in the loan and lending-commitment portfolios, changes in client credit quality, updated loss assumptions on leveraged loans, and borrower fraud. In wholesale, the macro outlook actually partly offset the increase. Also, 'gloomier' is the answer's own word; the filing only says 'changes in the Firm's weighted-average macroeconomic outlook'. The answer does mention wholesale borrower fraud in the next sentence.
- **opus #54** (Cross-company) WRONG: Tesla $3,855M on $94,827M of revenue, so 3,855 ÷ 94,827 ≈ 4.1% net margin (and the 'about $3.9 billion' / '29 times' figures built on it) → The answer key uses net income attributable to common stockholders: $3,794M ÷ $94,827M ≈ 4.0%. The $3,855M 'Net income' line includes $61M that belongs to noncontrolling interests. Apple has no noncontrolling interests, so the attributable figure is the like-for-like comparison. This is a minor difference of definition, not an invented number.
- **opus #21** (Unanswerable) WRONG: Intel shows up only as a competitor named in AMD's annual report (10-K) → Intel is named as a competitor in more than one filing. NVIDIA's 10-K also lists Intel Corporation among its current competitors, so it isn't only AMD's report. The underlying point, that Intel appears only as a competitor and never as a filer, still holds.
- **opus #21** (Unanswerable) UNSUPPORTED: Intel's own 10-K for the year ended in December 2025 → Intel's fiscal year-end isn't stated in any filing in the library. This comes from outside knowledge. It is minor and likely right, but nothing here backs it.
- **sonnet #22** (AMD) WRONG: The filing doesn't say which parts are one-time. → The filing does point out one-time items. It says 2025 taxes were lowered mainly by an $853 million benefit from releasing uncertain tax positions after IRS relief granted in April 2025. It also says other income rose to $577M from $181M mostly because of unrealized investment gains, and it names the ~$800M MI308 charge, of which ~$360M was later reversed. The answer key treats these as the main one-off items.
- **sonnet #33** (Microsoft) UNSUPPORTED: The $24.6 billion obtained through finance leases in FY2026 was 'datacenter-type assets' → On p.78 the $24,608M appears only as 'Right-of-use assets obtained in exchange for lease obligations: Finance leases', with no breakdown by asset type. Page 45 says Microsoft's leases cover datacenters, servers, network equipment, offices and R&D facilities, so calling the whole $24.6B datacenter-type is a loose label the filing doesn't state. The number itself is correct.
- **sonnet #52** (Cross-company) WRONG: NVIDIA made the most profit ... I took 'last year' to mean each company's most recent fiscal year in the filings → Under the stated rule (each company's latest fiscal year), Microsoft leads at $133,749M (FY ended Jun 30, 2026). NVIDIA leads only under the 'closest to calendar 2025' reading, which the answer did not adopt as its rule.
- **sonnet #52** (Cross-company) WRONG: Net income, ranked: NVIDIA listed first, Microsoft second → The list is labelled 'ranked', but the next entry (Microsoft, $133,749M) is larger than NVIDIA's $120,067M, so the order contradicts the figures and the stated rule.
- **sonnet #52** (Cross-company) UNSUPPORTED: Microsoft's ~$6.5B OpenAI net gains are 'a one-off boost' → The $6.5B figure is in the filing (Microsoft FY2026 10-K p.62), which says the gain mainly came from the dilution gain on the OpenAI Recapitalization. The filing does not call it one-off or non-recurring. That label is the answer's own interpretation.
- **sonnet #56** (Unanswerable) UNSUPPORTED: Microsoft's fiscal year ... wouldn't line up exactly with Google's calendar year. → No Alphabet filing is available, so nothing in the filings shows that Google reports on a calendar year. This is outside knowledge. It's a minor hedge, not a Google number, but it isn't sourced.
- **opus:high #17** (AMD) UNSUPPORTED: That gap likely reflects how much of the chip index's gain came from other AI-chip makers. → Neither filing breaks down which companies make up the S&P 500 Semiconductors Index or what drove its gains. The answer does present this as its own interpretation and hedges it, but the filings don't back it up.
- **opus:high #22** (AMD) WRONG: Embedded sales slid from $5.3B to $3.6B and then $3.5B 'as customers worked through their existing stock' [p.89, p.63] → The inventory explanation applies only to the 2024 drop: the FY2024 10-K (p.60) says customers 'continued to normalize their inventory levels.' For the 2025 dip of 3%, the FY2025 10-K gives a different reason: 'certain end market demand remained mixed.' The cited page 63 says that, not inventory drawdown.
- **opus:high #28** (Apple) UNSUPPORTED: Services turns the roughly 2.3 billion... [devices] → No installed-base or active-device figure appears in the Apple FY2025 10-K (searched); the number comes from outside knowledge and is left as an unfinished fragment.
- **opus:high #37** (Amazon) UNSUPPORTED: "In other words, big customers locked in discounts." (in the 'What the filing says' section) → The filing (Amazon.com FY2025 10-K, p.25) only says growth was "partially offset by pricing changes primarily driven by long-term customer contracts." It never mentions discounts or big customers. This is the answer's own reading, but it sits in the section meant to report only what the filing says.
- **opus:high #37** (Amazon) UNSUPPORTED: Rising AWS costs are "probably because of heavy spending on data centers and AI" → The filing (p.27) gives the reason as "spending on technology infrastructure... to support AWS business growth." Nothing on the cited pages mentions AI. The answer labels this as its own reading, so the problem is small.
- **opus:high #38** (Amazon) WRONG: margins nearly doubled → Operating margin rose from about 6.4% (2023) to about 11.2% (2025), which is roughly 1.75 times the 2023 level, or about a 75% increase. 'Nearly doubled' overstates the change. The 2023 to 2024 step (6.4% to 10.8%, about 1.7 times) also falls short of nearly doubling.
- **opus:high #40** (Amazon) UNSUPPORTED: Amazon is one of the largest private employers anywhere → None of the Amazon 10-Ks say this. The filings give only Amazon's own headcount and don't compare it with other employers, so the ranking comes from outside knowledge. It may well be true, but nothing in the filings backs it.
- **opus:high #41** (Tesla) UNSUPPORTED: The 2023 $5,001M tax benefit meant 'a tax credit rather than a tax bill' → The filing (Tesla FY2025 10-K p.91) says the 2023 benefit came mainly from releasing the valuation allowance on U.S. federal and certain state deferred tax assets, not from a tax credit. The lay wording mischaracterizes where it came from.
- **opus:high #47** (JPMorgan Chase) WRONG: Noninterest revenue ($87.0 billion) 'includes trading for clients ("Markets," $35.8 billion)' → The $35.8B Markets figure is Markets' total net revenue, so it spans both net interest income and noninterest revenue. The memo lines imply only about $29.8B of noninterest revenue is from Markets ($87,004M minus $57,208M NIR excluding Markets), and about $2.9B of NII is from Markets ($95,443M minus $92,591M). Presenting the full $35.8B as part of the $87.0B overstates Markets' share of noninterest revenue.
- **opus:high #49** (JPMorgan Chase) UNSUPPORTED: Because most deposits are uninsured, the bank depends on clients trusting it, which helps explain why it calls these deposits stable. → The filing doesn't make this link. On p.105 it calls consumer deposits and wholesale operating deposits stable because clients keep operating service relationships with the bank, and it says deposit insurance is what adds funding stability. Being uninsured isn't given as a reason for stability. This is in the 'own reading' section, but the reasoning doesn't match what the filing says.
- **opus:high #49** (JPMorgan Chase) UNSUPPORTED: Business clients are the biggest and fastest-growing source of deposits. → CIB is the largest segment (47%) and grew faster than CCB and AWM. In percentage terms, though, the Corporate segment grew faster: year-end $27.6B to $35.9B, about 30%, and average up about 14%, compared with CIB's 11%. 'Fastest-growing' is only true among the client-facing businesses. This is a minor point.
- **opus:high #52** (Cross-company) UNSUPPORTED: Microsoft's latest year was also helped by a one-time-style investment gain, so its 'core' lead over NVIDIA is smaller than the headline numbers suggest. → The adjustment is applied to only one company. Microsoft's $5.0B OpenAI gain is confirmed (Microsoft FY2026 10-K, p.38), and the $128.7B figure is correct. But NVIDIA's 'Other income, net' also rose, from $1,034M to $9,022M (NVIDIA FY2026 10-K, p.51), and the answer does not remove it. The filing also never calls the OpenAI gain 'one-time' (the year before was a $3.6B loss). So the 'core lead' comparison is an interpretation without full support.
- **opus:high #54** (Cross-company) WRONG: Tesla earned $3,855M on $94,827M, a 4.1% net margin (and Apple's profit is about 29 times Tesla's) → This is a minor, definitional mismatch with the answer key. $3,855M is the line Tesla labels 'Net income', but it includes $61M that belongs to noncontrolling interests, meaning outside owners of some Tesla subsidiaries. The figure that matches Apple's (Apple has no noncontrolling interests) is net income attributable to common stockholders, $3,794M. That gives a 4.0% net margin, as in the answer key, and makes Apple's profit about 29.5 times Tesla's. The conclusion doesn't change.
