# Golden Questions: the eval set (v2, 2026-10-25)

The answer key we score IndexIt against: **56 questions across 7 companies**, one file.
#1–25 were written 2026-10-21 (NVIDIA/AMD; #22–25 by Riya). #26–56 were drafted by Claude on 2026-10-25 for the
other companies, with answers checked directly in the PDFs. Riya reviewed and approved #26–56 on 2026-10-26.

## How to use it
- **Set** (D-017): **dev** = tune on freely (27) · **test** = held out, never tune on, run only at decision
  points such as model choice (19) · **extra** = older NVIDIA/AMD questions kept for regression checks,
  not counted in headline scores (10). Balanced at **3 dev + 2 test per company**.
- **Search decisions use dev only:** every original question was already used to pick search settings (D-019).
- **Scores are reported per company** as well as overall, so one company can't hide another's weak results.
- **New questions:** add them to the right company section with the next number (57, 58…) and a Set.

## Conventions
- **Page** = the PDF page number shown in a viewer, not the printed footer number (they differ on browser-printed PDFs, e.g. AMD's printed "46" = PDF p62).
- **Shorthand:** NVDA-FY25/26 = NVIDIA FY2025/FY2026 10-K · AMD-FY24/25 = Advanced Micro Devices · AAPL-FY23/24/25 = Apple · MSFT-FY25/26 = Microsoft · AMZN-FY23/24/25 = Amazon.com · TSLA-FY24/25 = Tesla · JPM-FY24/25 = JPMorgan Chase.
- $ in millions unless noted; *calc* = computed from the filing's numbers. ⚠️ = a **trap**: a plausible answer that's wrong.
- **Types:** `table` number from a table · `calc` arithmetic · `text` prose · `vague` non-expert wording · `jargon` must explain a term · `cross-doc` 2+ filings · `period` fiscal-year trap (D-010) · `latest` same figure in several filings (D-011) · `chart` from a graph · `analysis` synthesis, graded with a ✅/❌ **rubric** · `unanswerable` not in the filings


## NVIDIA
Fiscal year ends late January (NVIDIA FY2026 ≈ calendar 2025).

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 1 | What was NVIDIA's total revenue in fiscal year 2026? | table | $215,938M (~$215.9B), fiscal year ended Jan 25, 2026 | NVDA-FY26 · p51 | extra |
| 2 | How fast did NVIDIA's revenue grow last year? | calc, vague | $130,497M → $215,938M = **+65.5%** *calc* (filing says "up 65%") | NVDA-FY26 · p51, p37 | extra |
| 7 | Where does NVIDIA's money come from? | vague, table | Data Center $193,737M ≈ **90%** of FY26 revenue (Compute $162,361M + Networking $31,376M); Gaming $16,042M; Professional Visualization $3,191M; Automotive $2,349M | NVDA-FY26 · p79 | dev |
| 9 | Does NVIDIA depend on a few big customers? | vague, text | Yes. In FY26 one direct customer was **22%** and another **14%** of total revenue; the filing says revenue is concentrated among a limited number of customers | NVDA-FY26 · p41 (also p78) | extra |
| 11 | What is diluted EPS, and what was NVIDIA's in fiscal 2026? | jargon, table | $4.90 diluted (basic $4.93). Plain explanation: profit per share, counting shares that *could* exist from options/stock awards | NVDA-FY26 · p51 | dev |
| 12 | How much cash does NVIDIA have? | table | **$62.6B** in cash, cash equivalents and marketable securities as of Jan 25, 2026 (cash & equivalents alone: $10,605M), up from $43.2B | NVDA-FY26 · p42–43 | extra |
| 16 | If I had invested $100 in NVIDIA stock five years ago, what would it be worth? | chart | **$1,448.75** (from $100 on 1/31/2021 to 1/25/2026, dividends reinvested) vs S&P 500 $200.33 and Nasdaq 100 $206.01 | NVDA-FY26 · p35 | test |
| 18 | What was NVIDIA's revenue in fiscal 2024? | latest | $60,922M. Appears in **both** NVIDIA filings; should cite the **latest** (NVDA-FY26 p51) | NVDA-FY26 · p51 (also NVDA-FY25 p52) | dev |
| 23 | What is NVIDIA's biggest source of revenue? Is it a stable source, or AI-related and could be affected? | analysis, vague, table | ✅ Data Center **$193.7B ≈ 90%** of FY26 revenue, up 68%, driven by "accelerated computing and AI". ✅ Risks the filing names: demand for accelerated computing / AI / LLMs; **customer concentration** (two direct customers = 22% and 14% of revenue); **export controls** (H20 China restriction → **$4.5B charge** in Q1 FY26). ✅ Balanced: strong growth *and* concentrated, AI-dependent revenue. ❌ Predicting a crash or a boom | NVDA-FY26 · p79, p37, p16, p41, p10/p26 | test |

## AMD
Fiscal year ends late December.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 3 | What was AMD's net income in 2025? | table | $4,335M | AMD-FY25 · p74 | extra |
| 4 | Is AMD making money, and is it getting better? | vague, table | Yes. Net income $854M (2023) → $1,641M (2024) → $4,335M (2025); operating income $401M → $1,900M → $3,694M. Should explain "net income" in plain words | AMD-FY25 · p74 | extra |
| 8 | How much of AMD's revenue came from data centers in 2025, and how fast did it grow? | table, calc | Data Center $16,635M = **48%** of revenue; up **32%** from $12,579M *calc* | AMD-FY25 · p68 (also p89) | extra |
| 10 | What are the biggest risks for AMD? | vague, text | Grounded in the Risk Factors Summary: highly competitive, fast-changing markets; cyclical semiconductor industry; (+ other summary bullets). Must not invent risks | AMD-FY25 · p25 | extra |
| 13 | How much debt does AMD have, and is it going up? | text | Total debt (principal) **$3.3B** at Dec 27, 2025, up from **$1.8B** a year earlier | AMD-FY25 · p63 | test |
| 17 | How has AMD's stock done compared with the market? | chart, vague | $100 → **$234** (12/26/2020 → 12/27/2025). Beat the S&P 500 ($201) but lagged the S&P 500 Semiconductors Index ($547) | AMD-FY25 · p62 | dev |
| 19 | In AMD's 2024 annual report, what revenue did AMD report for 2024? | latest (explicit older) | $25,785M. Must cite the **older** filing because the user asked for it | AMD-FY24 · p67 | dev |
| 22 | Looking at AMD, what is the company's growth? What factors are responsible? Are those sustainable factors or just spikes? | analysis, vague | ✅ Revenue +34% to $34.6B (2025). ✅ Drivers: Data Center +32% to $16.6B (EPYC CPUs, Instinct MI350 GPUs); Client & Gaming +51% to $14.6B (Ryzen units +31%, average selling price +15%; consoles; Radeon); Embedded −3%. ✅ **One-offs in profit:** net income ($4.3B) was boosted by an **$853M one-time tax benefit** and higher unrealized investment gains (other income $577M vs $181M), and reduced by **~$440M net MI308 export-control charges**. So underlying profit growth is smaller than the headline. ✅ Sustainability signals: R&D +25% for AI; multiyear OpenAI deal (6 GW of GPUs). ✅ Clearly separates *filing facts* from *IndexIt's interpretation*. ❌ Buy/sell advice. ❌ Calling growth "sustainable" as a fact | AMD-FY25 · p63, p68–70, p8 | dev |
| 24 | Are there any geopolitical threats AMD sees as a detractor to their business? | text, vague | ✅ **US export controls on China** (Apr 2025 license rule hit MI308 GPUs → ~$800M inventory charges; some licenses since granted). ✅ **China–Taiwan** tensions could disrupt Taiwan-based foundries; AMD relies on **TSMC** for all ≤7nm CPU/GPU wafers. ✅ Tariffs and trade tensions; conflicts (Ukraine–Russia, Israel–Hamas, Venezuela) hitting the global economy. ❌ Risks not in the filing | AMD-FY25 · p40, p56, p35, p47, p33 | test |

## Apple
Fiscal year ends late September.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 26 | How much money does Apple make from iPhones? | table | FY2025 (ended Sep 27, 2025) iPhone net sales **$209,586M**, up 4% from $201,183M; ≈ **50%** of total net sales of $416,161M *calc* | AAPL-FY25 · p26 (also p39) | dev |
| 27 | Is Apple still growing, or has it peaked? | vague, analysis | Total net sales $383,285M (FY23) → $391,035M (+2%) → **$416,161M (+6%)**. Services +14% to $109,158M; iPhone +4%; Wearables, Home and Accessories −4% ($35,686M). ✅ Separates facts from interpretation. ❌ Calling it "peaked" or "booming" as fact | AAPL-FY25 · p26, p32 | test |
| 28 | Why does everyone say Apple's services business matters so much? | jargon, table, calc | Services gross margin **75.4%** vs Products **36.8%** (FY25). Services = **26%** of sales ($109,158M ÷ $416,161M) but **42%** of gross margin ($82,314M ÷ $195,201M) *calc*. ✅ Explains "gross margin" plainly | AAPL-FY25 · p27 | dev |
| 29 | How much cash does Apple hand back to shareholders? | text, calc | In FY2025 Apple repurchased **$89.3B** of stock and paid **$15.4B** in dividends ≈ **$104.7B** *calc*. ✅ Explains buybacks plainly | AAPL-FY25 · p29 | test |
| 30 | Why did Apple's profit drop in 2024 even though sales went up? | analysis, latest | ⚠️ Net income $96,995M (FY23) → **$93,736M** (FY24) while sales rose 2%. The main cause is a **one-time $10.2B income tax charge** related to the EU State Aid Decision, not weaker business; operating income rose ($114,301M → $123,216M). FY25 net income recovered to $112,010M. ❌ Blaming weak demand | AAPL-FY24 · p28 · AAPL-FY25 · p32 | dev |

## Microsoft
Fiscal year ends June 30 (FY2026 = July 2025 – June 2026).

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 31 | What was Microsoft's revenue in fiscal year 2026? | table, period | **$331,839M**, up 18% from $281,724M. ✅ Says FY2026 = July 2025 – June 2026 | MSFT-FY26 · p50, p37 | dev |
| 32 | How big is Microsoft's cloud business? | vague, text | **Microsoft Cloud** revenue **$214.4B** in FY26, up 27% ≈ **65%** of total revenue *calc*. ✅ Says what "Microsoft Cloud" includes (Microsoft 365 commercial cloud, Azure and other cloud services, commercial LinkedIn, Dynamics 365) | MSFT-FY26 · p34, p36 | test |
| 33 | Is Microsoft spending a lot on AI data centers? | analysis, table, calc | Additions to property and equipment **$115,948M** (FY26) vs $64,551M (FY25, **+80%** *calc*) and $44,477M (FY24) ≈ **35%** of revenue *calc*; the filing ties the spending to datacenters and computer systems | MSFT-FY26 · p53, p45 | dev |
| 34 | Did Microsoft's profit jump for real, or was it a one-off? | analysis, calc | ⚠️ Net income **$133,749M** vs $101,832M (+31%). **$5.0B** came from net gains on OpenAI investments (mainly a dilution gain from the OpenAI recapitalization). Operating income grew **+21%** ($155,237M vs $128,528M) *calc*, a cleaner measure. ❌ Presenting +31% as all underlying growth | MSFT-FY26 · p50, p38, p41 | test |
| 35 | What's the deal between Microsoft and OpenAI? | text | Long-term strategic partnership since **2019**, extended in **October 2025 and April 2026**; Microsoft is a **major investor**, receives **revenue-sharing payments**, and holds **rights to OpenAI's IP** (models, infrastructure). ❌ Ownership % or other facts not in the filing | MSFT-FY26 · p34, p17 | dev |

## Amazon
Calendar fiscal year.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 36 | Where does Amazon actually make its money? | vague, table, calc | 2025 sales $716,924M, but operating income comes mostly from **AWS: $45,606M of $79,975M (57%)**, while AWS is only **18%** of sales *calc*. North America $29,619M; International $4,750M | AMZN-FY25 · p68 | test |
| 37 | How fast is AWS growing? | table, calc | AWS net sales $107,556M (2024) → **$128,725M** (2025) = **+19.7%** *calc*; AWS operating income $39,834M → $45,606M | AMZN-FY25 · p68 | dev |
| 38 | Has Amazon's profit improved over the last three years? | table, latest | Net income **$30,425M** (2023) → **$59,248M** (2024) → **$77,670M** (2025); operating income $36,852M → $68,593M → $79,975M. Use the FY2025 filing (latest) | AMZN-FY25 · p37 | dev |
| 39 | What is free cash flow, and how much did Amazon have? | jargon, table | ⚠️ Free cash flow **fell** to **$11,194M** (2025) from $38,219M (2024), even though profit rose, because spending on property and equipment jumped ($128,320M vs $77,658M, net). ✅ Explains free cash flow plainly and that it's Amazon's own (non-GAAP) measure | AMZN-FY25 · p28 | test |
| 40 | How many people work at Amazon? | text | About **1,576,000** full- and part-time employees as of Dec 31, 2025 | AMZN-FY25 · p4 | dev |

## Tesla
Calendar fiscal year.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 41 | Is Tesla making more or less money than before? | vague, table | **Less.** Net income attributable to common stockholders $14,997M (2023) → $7,091M (2024) → **$3,794M** (2025); revenue $96,773M → $97,690M → $94,827M (−3%) | TSLA-FY25 · p53 | dev |
| 42 | How many cars did Tesla sell in 2025? | text | Delivered about **1.64 million** consumer vehicles in 2025 (produced ~1.66M), down from about **1,789,000** delivered in 2024 | TSLA-FY25 · p34 · TSLA-FY24 · p35 | test |
| 43 | What are regulatory credits, and how important are they to Tesla? | jargon, table, calc | ✅ Credits earned under emissions and other rules, sold to other companies that need them to comply. Revenue **$1,993M** in 2025, down 28% from $2,763M ≈ 2% of revenue, but equal to about **half (53%) of Tesla's 2025 net income** of $3,794M *calc*. ❌ Claiming credits are "pure profit" (not stated) | TSLA-FY25 · p10, p40, p53 | test |
| 44 | Is Tesla more than a car company? | vague, table | Energy generation and storage revenue **$12,771M** (+27%) = 13.5% of revenue *calc*; **46.7 GWh** of storage deployed in 2025; automotive revenue fell 10% to $69,526M | TSLA-FY25 · p40, p34 | dev |
| 45 | How much does Tesla depend on Elon Musk? | text | Risk factor: Tesla is "**highly dependent on the services of Elon Musk**, Technoking of Tesla and our Chief Executive Officer"; no key employee is bound by an employment agreement for a specific term. ❌ Outside facts about Musk | TSLA-FY25 · p21 | dev |

## JPMorgan Chase
A bank, with different statements and jargon; calendar fiscal year.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 46 | How much money did JPMorgan make in 2025? | table | ⚠️ Firm-wide net income **$57.0B** (down 2%), EPS $20.02. ❌ Quoting a *segment's* net income (e.g. $18.2B for one business) as the firm's profit | JPM-FY25 · p49 | test |
| 47 | How does a bank like JPMorgan make money? | jargon, vague | Total net revenue **$182.4B**; **net interest income $95.4B** (≈52% *calc*). ✅ Explains NII plainly (interest earned on loans and securities minus interest paid on deposits and borrowing); the rest is fees and other noninterest revenue | JPM-FY25 · p49 | dev |
| 48 | Is JPMorgan safe? Does it have enough capital? | jargon, analysis | Standardized **CET1 ratio 14.6%** (Advanced 14.1%) at Dec 31, 2025, vs a requirement including buffers of **11.5%**. ✅ Explains CET1 plainly (the bank's core capital as a share of its risk-weighted assets). ❌ Declaring it "safe" as fact | JPM-FY25 · p50, p96, p92 | test |
| 49 | How much money do customers keep at JPMorgan? | table | ⚠️ Deposits **$2,559,320M (~$2.56 trillion)** at Dec 31, 2025, up 6% from $2,406,032M. ❌ Quoting the *average* balance ($2,506,565M, p106) as the year-end figure without saying it's an average | JPM-FY25 · p58, p279 | dev |
| 50 | How much did JPMorgan set aside for bad loans? | jargon, table | Provision for credit losses **$14.2B** in 2025 ($14,212M vs $10,678M, **+33%** *calc*); net charge-offs $9.8B. ✅ Explains "provision" and "charge-off" plainly | JPM-FY25 · p50, p55 | dev |

## Cross-company
Need 2+ companies' filings; most include a fiscal-period or comparability trap.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 5 | Which company is more profitable, NVIDIA or AMD? | cross-doc, calc, jargon | NVIDIA: gross margin **71.1%**, net margin **55.6%** (FY26). AMD: gross margin **49.5%**, net margin **12.5%** (FY25) *calc*. Must explain what margins mean and note the fiscal periods differ by about a month | NVDA-FY26 p51 · AMD-FY25 p74 | test |
| 6 | Compare NVIDIA's and AMD's revenue in 2025. | cross-doc, period | NVIDIA **FY2026** (Jan 27, 2025 – Jan 25, 2026) $215.9B vs AMD **FY2025** (ended Dec 27, 2025) $34.6B. **Must explain** that NVIDIA's "FY2026" ≈ calendar 2025; using NVIDIA FY2025 ($130.5B) is a **fail** | NVDA-FY26 p51 · AMD-FY25 p74 | dev |
| 14 | Which company invests more in research and development, NVIDIA or AMD? | cross-doc, calc | It depends on the measure: NVIDIA spends more in dollars ($18,497M vs $8,091M), but AMD spends more relative to its size (**23.4%** of revenue vs NVIDIA's **8.6%**) *calc*. A good answer gives both | NVDA-FY26 p51 · AMD-FY25 p74 | extra |
| 15 | How many employees do NVIDIA and AMD each have? | cross-doc, text | NVIDIA ~**42,000** (end of FY26); AMD ~**31,000** (Dec 27, 2025) | NVDA-FY26 p11 · AMD-FY25 p18 | extra |
| 25 | Is NVIDIA investing in AI companies that in turn are buying their chips/services? Is this also true for AMD? | analysis, cross-doc | ✅ NVIDIA: says it has "invested and may continue to invest in our **ecosystem**"; private (non-marketable) holdings jumped from **$3.4B to $22.3B** in FY26 (net additions $17.4B); "finalizing an investment and partnership agreement with **OpenAI**" (not guaranteed); gains on these boosted other income. ✅ **Honesty test:** the filing does **not** say how much these investees buy from NVIDIA, so the answer must say that link isn't disclosed in the 10-K. ✅ AMD works the *other way round*: no equity stake in OpenAI. AMD **gave OpenAI a warrant** for up to **160M AMD shares at $0.01**, vesting as OpenAI hits GPU purchase milestones (tied to a 6 GW GPU deal); none vested and no 2025 financial impact (p64). ✅ AMD *also* holds investments in privately held, early-stage companies (p73), and the filing doesn't say whether they're customers. So "AMD doesn't invest in AI customers" is an overclaim (found by the fact-checker, 2026-10-25). ❌ Naming investees or "circular deals" from outside knowledge as if the filing said so | NVDA-FY26 · p22, p44, p67, p42 · AMD-FY25 · p64, p8 | dev |
| 51 | Compare Apple's and Microsoft's revenue for 2025. | cross-doc, period | ⚠️ Neither fiscal year is calendar 2025. Apple FY2025 (ended **Sep 27, 2025**): **$416,161M**. Microsoft FY2025 (Jul 2024 – **Jun 30, 2025**): **$281,724M**; FY2026 (to Jun 30, 2026): $331,839M. ✅ States which periods are compared and why | AAPL-FY25 · p32 · MSFT-FY26 · p50 | test |
| 52 | Which of these companies made the most profit last year? | cross-doc, period | "Last year" is ambiguous; **either reading passes if stated and applied consistently**: (a) each company's latest fiscal year → **Microsoft $133.7B** (FY ended Jun 2026), NVIDIA $120.1B (Jan 2026), Apple $112.0B (Sep 2025), Amazon $77.7B, JPMorgan $57.0B, AMD $4.3B, Tesla $3.8B (Dec 2025); or (b) periods closest to calendar 2025 (D-010) → **NVIDIA $120.1B** leads (Microsoft's FY2026 runs to Jun 2026; its FY2025 was $101.8B). ✅ States the reading and notes the different fiscal year-ends. ❌ Saying one rule and ranking by another *(key revised 2026-10-26: Sonnet used reading (b))* | MSFT-FY26 p50 · NVDA-FY26 p51 · AAPL-FY25 p32 · AMZN-FY25 p37 · JPM-FY25 p49 · AMD-FY25 p74 · TSLA-FY25 p53 | dev |
| 53 | Which company spends the most on research and development? | cross-doc, period | ⚠️ Microsoft **$35,562M** (FY26) and Apple **$34,550M** (FY25) lead; NVIDIA $18,497M; AMD $8,091M; Tesla $6,411M. ✅ Amazon reports "**technology and infrastructure**" ($108,521M), *not* R&D, so it isn't comparable; JPMorgan reports no R&D line. ❌ Ranking Amazon #1 on R&D without that caveat | MSFT-FY26 p50 · AAPL-FY25 p32 · NVDA-FY26 p51 · AMD-FY25 p74 · TSLA-FY25 p53 · AMZN-FY25 p37 | test |
| 54 | Is Tesla more profitable than Apple? | cross-doc, calc, jargon | No. Net margin Tesla **4.0%** (2025: $3,794M ÷ $94,827M) vs Apple **26.9%** (FY25: $112,010M ÷ $416,161M); gross margin Tesla 18.0% vs Apple 46.9% *calc*. ✅ Explains margin plainly | TSLA-FY25 p53 · AAPL-FY25 p32, p27 | dev |
| 55 | Which company has the most debt, and is that a bad thing? | analysis, cross-doc | Rubric: ✅ explains that JPMorgan is a **bank**: deposits and borrowing are its raw material, not comparable with a tech company's debt; ✅ compares the non-banks' debt with cited figures and periods; ✅ explains that debt isn't automatically bad (ability to repay, cash, profits). ❌ Ranking JPMorgan's liabilities against Apple's debt without that caveat. ❌ Invented totals | (several) | test |

## Unanswerable
The right answer says the filings don't contain it. Inventing an answer is a fail.

| # | Question | Types | Expected answer / rubric | Source · Page | Set |
|---|---|---|---|---|---|
| 20 | What will NVIDIA's revenue be next year? | unanswerable | Must say 10-Ks don't give revenue forecasts; may offer the latest actual figure. Inventing a forecast is a **fail** | — | test |
| 21 | What was Intel's revenue in 2025? | unanswerable | Must say Intel's financials aren't in these documents (Intel only appears as a competitor) | — | dev |
| 56 | How did Google do compared with Microsoft this year? | unanswerable (partial) | ✅ Says Alphabet/Google's filings aren't included; may give Microsoft's figures. ❌ Any Google numbers | — | dev |

*2026-10-25: #14 and #15 were reworded to name NVIDIA and AMD (written when the corpus only had those two). #25's rubric was corrected after the fact-checker found AMD's private investments (p73).*
