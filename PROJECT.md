# IndexIt — Project Log

> Living document. Read this first at the start of every session; update it at the end.
> Sections: Vision → Scope → Current State → Next Steps → Open Questions → Decisions → Session Log.

---

## 1. Vision

Point IndexIt at a folder of financial PDFs (annual reports, 10-Ks, investor decks, research papers) and ask questions in plain English. It answers from the **text, tables and charts**, cites the exact document and page, and works out **which report(s)** to look in without being told.

**Why it's hard (and worth learning):**
- Financial PDFs keep their important numbers in tables and charts, not prose. Basic text extraction mangles both.
- Questions often span documents ("How did Company A's operating margin compare with Company B's in FY24?").
- Numbers have to be exact. A plausible but wrong figure is worse than "I don't know".

**Team:** Riya (product: users, questions, quality bar, priorities) + Claude (engineering: architecture, implementation, cost analysis).

**Target user (decided 2026-10-20):** non-experts like Riya who find annual filings too dense and **don't know what to look at**. This changes the product: it isn't just lookup. Answers must
- explain jargon in plain language ("operating margin = how much of each $1 of sales is left after running the business"),
- give context (is this good or bad? compared with last year?),
- eventually point the user toward what's worth asking ("suggested questions" / "key things to check in a 10-K").

**Document type for MVP:** US SEC **10-K** filings (PDF). 10-Ks have a standard structure (Item 1 Business, 1A Risk Factors, 7 MD&A, 8 Financial Statements…) that we can use for metadata and navigation. They are mostly text and tables, with fewer charts than glossy annual reports.

---

## 2. MVP Scope

**In:**
- Pick a local folder with about 10 financial PDFs and index everything in it.
- Re-indexing is incremental: only new or changed files get processed.
- Ask a question without naming a document. The system finds the relevant pages across all reports.
- Answers cover text, tables and charts, with citations (file + page) and a view of the source page.
- A simple local UI.

**Out (for now):** multi-user and auth, cloud hosting, scanned/OCR-heavy PDFs (revisit if the test files need it), live market data, cross-document SQL analytics.

---

## 3. Current State

**Status:** Baseline simple RAG built. **MCP server + Claude Code agent built and working** on Riya's Pro subscription (personal use only). Riya is the only user (2026-10-23). Next: try the latency experience, then decide whether an API version is needed. Not yet formally scored.
**Last updated:** 2026-11-01
**Latest (2026-11-01):** key-figures table + `compare_companies` tool + Compare view in the app (D-026). Cross-company eval 8/9, answers 30–45% faster and up to 6× cheaper; extracted figures match the SEC's XBRL data (251/254 exact, 0 different).

**Code** (`src/indexit/`):
| File | Role |
|---|---|
| `simple_pipeline.py` | Step 1 baseline: PyMuPDF page text → fixed 1,500-char pieces (200 overlap); metadata = file + page only |
| `embedder.py` | Local embeddings, `BAAI/bge-small-en-v1.5` (D-004) |
| `store.py` | LanceDB index in `data/index/`, table `simple_v1`; incremental by file hash (D-005) |
| `llm.py` | Claude Opus 5.5 brain, effort `high`, D-012 two-part answer prompt, server-side refusal fallback |
| `cli.py` | `uv run indexit index <folder>` · `filings` · `search "<q>"` (free) · `ask "<q>"` (API key) · `ask-agent "<q>"` (Pro subscription) |
| `search.py` | Shared retrieval used by the CLI and the MCP server |
| `documents.py` | Filing metadata from the cover page: company, fiscal year, period end |
| `prompts.py` | Shared prompts: D-012 format + D-010/D-011 rules; API and agent variants |
| `mcp_server.py` | **MCP server** (D-013): `list_filings`, `search_filings`, `compare_companies` (D-026), `read_page` tools + `indexit_answer` prompt. `read_page` only opens files from the filings folder (path traversal tested ✅) |
| `figures.py` | **Key figures** (D-026): rules read each filing's income statement and balance sheet from the Docling cache; checks; `comparison()` (ranked, with sources), `compare()` (text for the agent), `insights()` (rule-based sentences for the app) |
| `agent.py` | **Claude Code brain** (D-014) via the Agent SDK, locked to IndexIt tools (6 guardrail layers, see file docstring) |

**Agent mode results (2026-10-23, Riya's Pro subscription):**
| Question | Time | Tool calls | ≈API-equivalent cost | Quality |
|---|---|---|---|---|
| "AMD net income 2025?" (simple) | 26–31 s | 3 (list → search → read_page p74) | ≈$0.08 | ✅ Correct, cited p74, explained terms |
| #22 "AMD growth, drivers, sustainable?" (analysis) | 63 s | 8 (7 searches, several in parallel) | ≈$0.29 | ✅ Very strong: segment table, multi-year history, export-control charges and $360M reversal, margin trends, labelled interpretation. Spot-checked 3 new facts against the PDFs, all correct. ⚠️ Missed the **$853M one-time IRS tax benefit** (mentioned the tax swing only generically) |
- **Security finding:** the first run exposed Riya's **claude.ai connectors** (her other connected apps) to the agent. `tools=[]` only removes *built-in* tools. Calls would still have been blocked (allowed_tools + dontAsk + hook), but tools must not even be visible. Fixed with `strict_mcp_config`, `ENABLE_CLAUDEAI_MCP_SERVERS=false`, and a fail-closed check that aborts if any non-IndexIt tool appears. Side effect: ~140 fewer tool definitions → cost ≈$0.82 → ≈$0.08 per simple question.
**Latency study (2026-10-25)**, `spikes/profile_agent.py`, one run per cell (noisy, directional only):

Where the time went (Opus 5.5, default effort, "Where does NVIDIA's money come from?", 36 s): startup 3 s · deciding searches ~5 s · first search 5.9 s (embedding model load) · **writing the answer ~21 s (60%)** · first word visible at 26 s.

Free fixes applied: (1) MCP server pre-loads the embedding model at launch (first search 5.9 s → 3.6 s); (2) filings list injected into the agent prompt, so no `list_filings` round trip.

| Config | Q7 total / first word | #22 total / first word | #22 checklist (10 items) |
|---|---|---|---|
| Opus 5.5, default (medium) | 36 s / 26 s | 63 s / – | 7/10 (most thorough, 7.7k chars) |
| Opus 5.5, **low** effort | 27 s / 11 s | 30 s / 22 s | 6/10 (dropped R&D, OpenAI) |
| **Sonnet 5.5**, default | 20 s / 15 s | 24 s / 16 s | 6/10 (dropped R&D, OpenAI) |
| **Haiku 5.5**, default | 19 s / 12 s | 30 s / (preamble) | 8/10 (one reasoning slip on units vs price; a new claim verified ✅ p64) |
- **Every config missed the $853M tax benefit and the investment gains (p70)**, so it's a **retrieval** gap, not a model gap. Step 2 (cleaner chunks) should help every model.
- Answers run 4–7.7k characters, and writing them is the biggest time cost. Answer length is a product lever (Q9).
- `ask-agent` now takes `--model opus|sonnet|haiku` and `--effort low|medium|high`.

- **Agentic search beats the single-search baseline:** for analysis questions the agent's multiple targeted searches + `read_page` work around the baseline's noise (it read the full p74 table instead of relying on chunks).

**Baseline index:** 1,556 passages from 4 filings, built in ~1.5 min. A re-run skips unchanged files ✅.

**First free retrieval observations (search only, no LLM):**
- ✅ Simple lookups ("NVIDIA FY2026 revenue") find the right income statement page as #1.
- ❌ **Boilerplate noise:** the browser-printed AMD PDFs repeat a header/footer (date, title, URL, "34/125") on every page. Each page's last short piece is mostly footer, and these crowd the results (3 of the top 5 for "AMD net income 2025"). Step 2 fix: strip repeated headers/footers and drop tiny pieces.
- ⚠️ "AMD net income 2025" found the *Comprehensive Income* statement (p75, which happens to show net income) rather than the main income statement (p74). It's correct by luck.

**Machine:** Apple M1, **8 GB RAM**. Python 3.12 project managed by `uv` (installed 2026-10-20 to `~/.local/bin`). Run code with `uv run python ...`. Dependencies: `pymupdf`, `docling`.

**Sample corpus** (originally `data/sample/`, now `data/filings/` (D-024), 4 files, ~480 pages):
| File | Company | Fiscal year | Pages | Income statement page |
|---|---|---|---|---|
| `177440d5-…pdf` | NVIDIA | FY2025 (ended Jan 26, 2025) | 130 | 52 |
| `e361e58a-…pdf` | NVIDIA | FY2026 (ended Jan 25, 2026) | 93 | 51 |
| `February 5, 2025 - 10-K…AMD.pdf` | AMD | FY2024 (ended Dec 28, 2024) | 125 | 67 |
| `February 4, 2026 - 10-K…AMD.pdf` | AMD | FY2025 (ended Dec 27, 2025) | 133 | 74 |
Two files have random UUID names, so company and year **must be detected from the content**, not from the filename.

**Corpus expanded 2026-10-25 → 14 filings, 6 companies, 4,953 passages** (`uv run indexit filings`):
| Company | Filings | Fiscal year ends | Why it helps |
|---|---|---|---|
| NVIDIA | FY2025, FY2026 | late January | original |
| AMD | FY2024, FY2025 | late December | original |
| **Apple** | FY2023, FY2024, FY2025 | late **September** | new calendar; consumer brand |
| **Microsoft** | FY2025, FY2026 | **June 30** | hardest period alignment (FY2026 = Jul 2025–Jun 2026) |
| **Amazon** | FY2023, FY2024, FY2025 | Dec 31 | retail + cloud; 3-year history |
| **Tesla** | FY2024, FY2025 | Dec 31 | auto/energy; popular with retail investors |
- Cover-page detection had to be fixed: Amazon writes "Commission File **No.**" with underscores before the name, and Microsoft's cover has **no "(Exact name of registrant)" label** (the name is followed by its state). Added a fallback that reads the run of capitalised words and stops at the state name. Indexing now **warns** if a cover can't be read.
- Indexing took 1 min 42 s (only the 10 new files; the 4 unchanged ones were skipped).
- **Free retrieval test:** "Microsoft revenue fiscal 2026" → 2 of the top 5 hits are **AMD** pages. The *which-company* confusion now exists, which is exactly what the expansion was meant to expose. Clear company-named questions (Tesla R&D, Apple iPhone) still route correctly.
- **Bank added 2026-10-25: JPMorgan Chase FY2024 + FY2025** (436 / 410 pages; 2,843 passages = **36% of the index**). Corpus now **16 filings / 7 companies / 7,796 passages**. Still missing: pharma.
  - Cover detection fix #2: JPM's **two-column cover** interleaves text ("For the fiscal year ended Commission file December 31, 2024 number 1-5805 JPMorgan Chase & Co."). Patterns now allow text in between; the suffix trim also handles "& Co.".
  - Free retrieval tests on the 16-filing index:
    - ✅ JPM's size doesn't flood other companies' queries (Apple net income → 8/8 Apple).
    - ❌ **Mentions vs. about:** "biggest risks for Microsoft" → 4/8 hits from NVIDIA/AMD pages that *mention* Microsoft (AMD: "If we lose Microsoft Corporation's support…"). Fix idea: company-aware filtering using the filing metadata.
    - ⚠️ **Bank segment trap:** "JPMorgan net income 2025" surfaces *segment* net income ($4.5B, $18.2B) as top hits. Quoting these as firm-wide profit would be wrong content. Must be in the test set.
    - ⚠️ **Aggregate cross-company questions** ("Which company has the most debt?") can't be covered by 8 passages; they need per-company searches (agent) and a caveat that bank debt isn't comparable to a tech company's.

**Parsing spike results (2026-10-20)**, script in `spikes/docling_page.py`:
- *Raw text (simple RAG input):* one value per line; year headers sit 40+ lines away from the numbers.
- *PyMuPDF table finder:* dropped the year header row, duplicated every column, garbled the Revenue row. ❌
- *Docling:* reproduced NVIDIA's and AMD's income statements exactly: year headers, parenthesized negatives, section rows. ✅ Speed ≈ 3–4 s/page on the M1, so the full corpus takes about 30 min, one time, free, local.
- Only 12 embedded images across all 4 filings, so charts are close to irrelevant for 10-Ks. That supports keeping multimodal as a conditional layer.
- The one recurring chart, the 5-year **stock performance graph**, has its data printed as a table right below it (NVDA-FY26 p35, AMD-FY25 p62), so text + table extraction already captures it.
- **Page numbers:** cite the PDF page index (what a viewer shows). The AMD PDFs were browser-printed, so their footer numbers differ (printed "46" = PDF page 62).

---

## 4. Next Steps

0000000. **(2026-11-01) Key figures (D-026): built and measured.** Next: re-run #57 (units fix) with the next eval; run the cross-company **test** questions (#5, 51, 53, 55) once, when the system is final; portfolio case study: update the system design (new tool, key-figures store) when Riya wants it on the site. Deferred: industry groups (SEC SIC codes as suggestions, once 3+ companies share an industry) and company trends in the Compare view.

000000. **(2026-10-27) Decided and built; stage 2 running:**
   1. ~~Answering model~~ ✅ **Sonnet 5.5 high** (D-021 accepted). No Opus re-run: Opus would need to clearly *beat* Sonnet (Sonnet is also faster and ~2.5× lighter), the gap is wide, and each eval question uses the plan twice (answer + Opus check). If Sonnet errors persist, try Opus only on the failed questions.
   2. ~~Prompt fixes~~ ✅ (`prompts.py`): no outside knowledge anywhere; follow-ups mustn't assume unverified facts; summary words ("more than half", "nearly doubled", "mainly") only when computed, keep the filing's hedges; don't skip items between figures; "the filing doesn't say" only after a specific search; apply a stated rule to every company.
   3. ~~Docling use~~ ✅ **small-to-big**: `search_filings` appends the structured tables of each result page (D-022).
   4. ~~Agent depth~~ ✅ built-in reading via (3); `read_page` now for text around a figure or tables outside the results.
   - **Scorecard (Riya's format):** `eval/model_comparison.md`: numerical precision / chart reading / cross-report synthesis / latency-cost per model, one table per run.
   5. ~~Dev 27 on Sonnet high~~ ✅ run `2026-10-27_1854`: **25/27 (was 23), 0 wrong claims (was 4), 0 serious errors (was 2), coverage 93% (was 89%)**, numbers 13/13. #52 fixed; #22 now an omission (still misses the $853M one-off); new: #18 minor, #25 moderate (a negative claim from a jargon retrieval gap: "non-marketable equity securities"). **Cost doubled: $0.048 → $0.094 per answer** (tables + more searches), 14 → 16 s. Details: `eval/model_comparison.md`.
   6. ~~Test set (19), once~~ ✅ run `2026-10-27_1911`: **15/19 strict, 0 wrong claims, 0 serious errors**. 3 wording overreaches (#23 "not a stable source", #27 "record" sales, #43 "falls through to profit"), all in summary lines. **1 broken output (#53): Sonnet typed its tool calls as text and stopped**, 1 in ~140 answers. Honest estimate: ~80% strict, 0 serious. Don't tune on test questions.
   - **Output guard: deferred to the UI phase (Riya, 2026-10-28).** Answers are good when they come out; the guard only catches a broken reply (~1 in 140). Riya is the only user and can re-ask. Build it with the UI (retry once, or show "try again"), before anyone else uses IndexIt.
   7. ~~Table budget~~ ✅ **Riya (2026-10-28): don't sacrifice accuracy. Keep the full 16k-char budget.** The jargon gap (JPM, AMD p73): a retrieval fix that helps all questions (e.g. query expansion), not a one-term prompt hint.
00000. *(2026-10-26, superseded by 000000)* Decisions for 2026-10-27: model; prompt fixes; Docling small-to-big vs table passages; agent depth; then dev eval → test once.
0000. **(2026-10-25, eval set v2 merged):** `eval/golden_questions.md` is the **single eval file**: 56 questions, grouped by company, each with a **Set** column. **27 dev / 19 test / 10 extra**, balanced at **3 dev + 2 test per company** (+ cross-company 4/4, unanswerable 2/1). Original NVIDIA/AMD questions went to test only if IndexIt had never answered them (#5, 13, 16, 20, 23, 24); 10 overlapping originals → `extra` (regression only). `--set dev|test|extra|all` on `eval` and `eval-search`; scores are reported **per company**. **Search decisions use dev only.**
   - **New dev search baseline (clean_v2, company-aware):** expected page in top 8 **11/25**, key figures 43%, right company 98%. Per company: NVIDIA 2/3, **AMD 0/3, Apple 0/3, JPMorgan 0/3**, Microsoft 2/3, Amazon 2/3, Tesla 2/3, cross 3/4. The old NVIDIA/AMD-heavy set overstated search quality.
   - ~~**[Riya]** Review #26–56~~ ✅ approved 2026-10-26.
   - ~~**[Claude]** Reranker retest; Apple/JPM/AMD misses~~ ✅ D-020 (dev search 11 → 14/25; reranker not adopted).
   - **IN PROGRESS (started 2026-10-26 16:4x): stage 1 model comparison**: all **27 dev** questions, **Opus 5.5 (default effort) vs Sonnet 5.5**, each answer fact-checked by Opus (high effort). Riya chose all 27 over a trimmed set: rare errors need more questions to show up, and every company stays covered. Log: `eval/runs/stage1_dev_opus_vs_sonnet.log`; results: the newest `eval/runs/<timestamp>/` (`run.json` setup snapshot, `opus.jsonl`/`sonnet.jsonl` per-answer records, `summary.md`). If interrupted: `uv run indexit eval --resume latest`.
   - Eval runner upgrades for this run: configs **alternate per question** (an interrupted run stays balanced); **resume** (redoes any errored fact-check); per-answer records include the answering model, tokens, time to first word, **the agent's exact search queries**, answer length, follow-ups, API-equivalent cost, and fact-check timing; the fact-checker's answer-key legend now covers all 16 filings (it had only NVIDIA/AMD); the summary has overall, per-company and question-by-question tables plus every flagged claim. Smoke test passed (#21, both models).
   - **Token logging (Riya, mid-run):** answer tokens were already recorded per answer (`usage`: new input, cached input, output and thinking tokens per model). Added: **fact-checker tokens** (from the next run on; this run has only the checker's cost), a **Tokens** table in the summary, and `uv run indexit eval-summary [run|latest]` to rebuild a summary from saved records. **After this run ends, re-run `eval-summary latest`**: the running process will write its summary in the old format.
   - **Bug found and fixed:** `--resume latest` / `eval-summary latest` picked the *log file* (its name sorts after the timestamped folders), so resume would have failed. "latest" now means the newest folder containing `run.json`.
   - **Effort mismatch (caught by Riya):** "default effort" meant **Opus = medium** but **Sonnet = high** (different defaults). This was Claude's oversight, not a choice. Fix: keep the run and **add `opus:high`** to the same run folder (queued to start automatically when stage 1 ends; log `eval/runs/stage1b_dev_opus_high.log`). Result: three columns, Opus-medium / **Opus-high vs Sonnet-high** (the fair comparison) plus what extra effort buys Opus.
   - **Honest status on "multimodal" (2026-10-26):** IndexIt is **text-only** RAG: cleaned chunks + metadata filters + an agent. **Docling (D-003) was chosen in the spike but never wired in**, so tables are still flattened PyMuPDF text. **Plan (Riya):** finish the Opus-high run → classify flagged errors by cause (table misread / retrieval / reasoning) → **wire in Docling tables** and measure → multimodal (page images) only if table errors remain. Open: Riya to decide whether to build multimodal anyway as a learning goal.
   - **Stage 1 results (2026-10-26, run `2026-10-26_1639`, dev 27):**
| Config | Accuracy | Wrong | Unsupported | Claims checked | Coverage | Median time | Words | Searches | ≈API $ (27 Qs) |
|---|---|---|---|---|---|---|---|---|---|
| Opus 5.5, medium | 18/27 | 6 | 7 | 454 | 93% | 18 s | 291 | 2.4 | $3.32 |
| Sonnet 5.5, high | **23/27** | 4 | 2 | 433 | 90% | 14 s | 266 | 1.8 | $1.30 |
     Per company: JPMorgan **Opus 0/3 vs Sonnet 3/3**; Amazon 1/3 vs 3/3; Microsoft 3/3 vs 2/3; the rest similar.
     **Claude verified the key flags against the PDFs:** Opus #47 ✅ real and misleading ("$95.6B costs → $57.0B net income" silently skips the $14.2B provision and taxes; p49); Opus #49 ✅ real (business deposits are 47%, not "more than half"; p105); Opus #38 ✅ overstated ("primarily from Anthropic" → stated as all; AMZN p45); Opus #21 ✅ minor (NVIDIA also names Intel, p9); Opus #18 ✅ a **follow-up question with a false premise** ("why did gross margin go up FY24→FY26", it went 72.7% → 71.1%); Sonnet #22 ✅ real (said the filing doesn't identify one-offs; it does: $853M tax benefit, p70). **Sonnet #52: the answer key was too rigid**: Sonnet chose NVIDIA under the calendar-2025 reading (D-010), defensibly, but contradicted its own stated rule. Key revised to accept either reading if applied consistently; #52 to be re-checked for all configs.
     **Pattern:** Opus (medium) makes more *inferential overreach* ("mainly from", "more than half", outside knowledge in interpretation), especially on JPMorgan's dense bank detail. Sonnet is more conservative but can miss key one-offs. New error type: **follow-up questions with false premises**, so "dig deeper" suggestions need to be accurate too.
   - **Pro plan limit hit (2026-10-26, ~evening):** the Opus-high pass hit "You've hit your session limit · resets 9:10pm". Claude Code returns this as a *successful* result, so **11 records held the limit message instead of an answer** (one, #44, even got fact-checked and looked done). Fixed: (1) the agent flags that text as `plan_limit`; (2) the eval **stops immediately** and prints the resume command; (3) resume and summaries ignore limit-message records. Added `eval --resume <run> --recheck <ids>` (re-grade without re-answering). Resumed after the reset: 11 Opus-high questions + #52 re-check for opus/sonnet (log `eval/runs/stage1c_resume.log`).
   - **Then:** Claude spot-checks flagged claims against the PDFs → stage 2: the 19 test questions on the winner(s).
000. *(earlier 2026-10-25)* Riya asked Claude to draft balanced questions for the 5 new companies. 31 drafted in `eval/balanced_questions_draft.md` (#26–56: 5 each for Apple, Microsoft, Amazon, Tesla and JPMorgan, plus 6 cross-company), answers verified directly in the PDFs, with ⚠️ traps (e.g. Apple's 2024 one-time $10.2B tax charge, Microsoft's $5.0B OpenAI gain, JPM segment vs firm net income, JPM average vs year-end deposits, Amazon "technology and infrastructure" ≠ R&D, Tesla regulatory credits ≈ 53% of net income). Suggested split: 13 test / 18 dev. **[Riya]** Review and adjust the split → **[Claude]** move them into the dev/test files.
00. **(2026-10-25, after corpus expansion):**
   - **[Riya]** Write 10–15 **test-set** questions (user's voice) in `eval/test_questions.md`. Don't look at IndexIt's answers to them first.
   - **[Claude]** Verify the test answer keys against the pages. Add a few dev questions on the new companies.
   - **[Claude]** Retrieval fixes that help every model: ~~company-aware search~~ ✅ D-018 · ~~boilerplate removal / clean index~~ ✅ D-019. Next retrieval candidates: the reranker retest on the bigger question set; scoring retrieval on the agent's own queries; Docling tables (step 2b). Track with `uv run indexit eval-search` (free).
   - Then the model comparison (D-016) on dev + test.
0a. *(2026-10-25, earlier; superseded by 00)*:
   - **[Riya]** Approve the eval run (uses Pro plan usage; ~1–1.5 min per question per config including fact-checking). Proposal: **10 representative questions × 3 configs** (`opus:low`, `sonnet`, `haiku`) ≈ 45 min, then the full 25 on the top 1–2 configs.
   - **[Claude]** Then: fix retrieval gaps the eval exposes (e.g. AMD p70 facts), re-score.
0. *(2026-10-23, superseded where noted)*:
   - **[Riya]** Try `uv run indexit ask-agent "<question>"` on a few golden questions and judge the latency and answer experience.
   - **[Claude]** Build an agent-mode eval runner (runs the golden set through `ask-agent`, records time, tool calls and answers; free on Pro but uses plan limits) so agent quality is scored, not eyeballed.
   - **[Claude]** Simple app UI (Streamlit) over the agent with live "searching…" progress, which makes 30–60 s waits feel acceptable.
   - **[Both]** After that, decide whether an API version is needed (D-009). The API key / paid steps below are on hold.
1. ~~**[Riya]** Put 10-K PDFs in `data/sample/`~~ ✅ Done (4 filings).
2. ~~**[Riya]** Answer Q6 and Q7~~ ✅ → D-010, D-011.
3. **[Riya]** Review Claude's 21 draft golden questions in `eval/golden_questions.md`; edit them and add your own in a real user's voice. *(Original task:)* Write 15–20 golden questions **as the target user would ask them**, including vague ones ("Is this company making money?", "What are the biggest risks?") alongside precise ones ("What was FY2024 net income?"). Template: `eval/golden_questions.md`.
4. **[Riya]** Confirm D-009 (Claude API for the "brain", everything else local).
5. ~~**[Claude]** Python env + parsing spike~~ ✅ Done; Docling chosen (D-003).
6. **[Riya]** Create a Claude API key (console.anthropic.com → API Keys, add a small amount of credit) and add `export ANTHROPIC_API_KEY=...` to `~/.zshrc`. Never paste the key into chat or project files. Billing is **prepaid credits**, separate from any claude.ai subscription; keep auto-reload off and set a low monthly spend limit.
   - **[Claude]** The eval runner must print the **$ cost per question and per run**, computed from token usage.
7. **[Claude]** Build the eval runner (Phase 3): golden set → `ask` → score. Numeric questions are checked automatically; rubric questions (#22–25) are graded by a Claude judge. Estimated first full run ≈ **$2–3** (25 questions × ~$0.05 answer + judge calls); get Riya's go-ahead before running.
8. ~~**[Claude]** Build~~ ✅ Done 2026-10-21 (baseline built; scoring pending). *(Original:)* Build a **simple text RAG baseline first** (see D-001 revision), score it on the golden set, and show where it fails.

Open questions Q2, Q3 and Q5 are answered (see below). Q1 is partly answered. Q4 is deferred, since costs get discussed when an action spends money.

### Roadmap
| Phase | Goal | Done when |
|---|---|---|
| 0 | Design + parsing spike | Parser chosen based on real files |
| 1 | Ingestion pipeline | Folder → parsed pages, tables, chart descriptions → chunks + metadata → vector index |
| 2 | Retrieval + answering (CLI) | Ask a question and get an answer with citations |
| 3 | Eval harness | Golden set runs automatically and reports a score we can track |
| 4 | UI (Streamlit) | Choose folder, index, chat, see the cited page |
| 5 | Quality upgrades | Reranker, query routing, table→SQL for numeric questions, multi-year comparisons |

---

## 5. Open Questions (for Riya)

- **Q1. Who is the user?** ✅ Non-experts who don't know what to look at in filings. *Still open:* their top 5 questions (these go into the golden set).
- **Q2. Which reports?** ✅ US 10-Ks.
- **Q3. Privacy / local vs. API?** ✅ Discussed 2026-10-20. 10-Ks are public filings, so privacy isn't a blocker. See D-009.
- **Q4. Budget:** ⏸ Deferred. Discuss cost at the point an action spends money (working agreement).
- **Q5. Must every number be cited to a page?** ✅ Yes.
- **Q8. Should IndexIt give interpretation, or only facts?** (Raised by Riya's analysis questions #22–25.) Questions like "Is this growth sustainable?" go beyond what the filing says. Recommendation: yes, give interpretation, but structure every answer as **"What the filing says"** (cited facts) → **"What this might mean"** (clearly labelled interpretation) → no buy/sell advice. Not using outside knowledge as if it came from the filing.
- **Q9. Answer length (2026-10-25):** writing the answer is ~60% of response time, and current answers are 4–7.7k characters. Options: (a) keep full answers; (b) **"Quick answer first"**: ~150–250 words with the key facts + a "Go deeper" button for the full analysis; (c) user picks Quick/Deep before asking. Recommendation: (b).
- **Q10. Default model/effort for agent mode:** pick after the agent eval runs all 25 questions on 2–3 configs (Opus-low, Sonnet, Haiku). One run each isn't enough to choose. Note: Opus typically uses Pro plan limits faster than Sonnet/Haiku.
- **Q6 ✅ → D-010. Q7 ✅ → D-011.** (Original wording below.)
- **Q6. What does "2025" mean?** (Found in the spike.) NVIDIA's fiscal year ends in January, so *NVIDIA FY2026* covers mostly calendar 2025. AMD's ends in December, so *AMD FY2025* is calendar 2025. When a user asks "Compare NVIDIA and AMD revenue in 2025", should we match fiscal-year labels or calendar periods, and should the answer explain the mismatch? (Recommendation: match by period end date and explain it in plain English. It's exactly the kind of trap our non-expert user wouldn't know about.)
- **Q7. Overlapping data:** each 10-K repeats the previous 2–3 years. NVIDIA FY2025 revenue appears in *both* NVIDIA filings, and companies sometimes restate old numbers. Recommendation: prefer the **most recent filing** for any figure, and mention a restatement if the numbers differ.

---

## 6. Decisions

Format: ID · Title · Status (Proposed / Accepted / Superseded) · Context · Options · Decision · Why · Cost/Trade-off.

### D-001 · Overall architecture · **Proposed**
**Options considered:**
| Option | How it works | Pros | Cons |
|---|---|---|---|
| A. Stuff everything into the LLM | Send all PDFs with every question | Zero infrastructure; best possible "understanding" | 10 reports ≈ 2,000+ pages, which is over the per-request PDF limit (600 pages). Every question re-pays for all tokens, so it costs dollars per question. Doesn't scale. |
| B. Text RAG | Extract text → chunk → embed → retrieve → answer | Cheap, standard, scales | Loses tables and charts, which are the core of financial reports |
| C. Vision-only RAG (ColPali-style) | Embed page *images*; retrieve pages; vision LLM reads them | Great for charts and layout | Weaker at exact keyword/number search; heavier storage; still maturing |
| **D. Hybrid multimodal RAG** | Parse text + tables (structured) + charts (LLM-written descriptions) → chunks with rich metadata → hybrid search → send top chunks **plus the page images** to Claude | Good on text, tables and charts; precise citations; scales to hundreds of docs | More moving parts to build |

**Proposed decision:** D. Keep A as an *eval oracle*: for one question about one report, the "send the whole document" answer is a useful quality reference.

**Revision 2026-10-20: build progressively.** Build B (simple text RAG) first as a **baseline**, score it on the golden set, then add layers (structured tables → page images to a vision LLM → hybrid search → reranking → agentic multi-step). Each layer has to earn its place with a measurable score improvement. *Clarified 2026-10-20:* smart chunking + metadata is the **foundation**, not an alternative to multimodal. Vision (page images) is a **conditional** layer, added only if the eval shows table-extraction errors or failed chart questions. That is good engineering practice, and it lets Riya see why each piece exists. Concepts are explained in [LEARNING.md](LEARNING.md).

### D-002 · LLM choice per job · **Proposed**
Different jobs have different quality and cost needs (prices per 1M tokens, input/output, as of 2026-10):
- Haiku 5.5: $0.10 / $0.50 · Sonnet 5.5: $2 / $10 · Opus 5.5: $4 / $20. The Batch API gives 50% off for jobs that aren't time-sensitive, such as indexing.

**Indexing cost** (~2,000 pages; describing a page image ≈ 1.5K input + 300 output tokens):
| Model for chart/table descriptions | Approx. one-time cost | Batch API |
|---|---|---|
| Haiku 5.5 | ~$0.60 | ~$0.30 |
| Sonnet 5.5 | ~$12 | ~$6 |
| Opus 5.5 | ~$24 | ~$12 |
Only pages with charts or complex tables need the LLM, often 20–40% of pages, so real costs are lower.

**Per-question cost** (~10K tokens of retrieved text + ~5 page images ≈ 18K input, ~800 output):
- Opus 5.5 ≈ $0.09 · Sonnet 5.5 ≈ $0.04 · Haiku 5.5 ≈ $0.002

**Proposed:** Opus 5.5 for answering, since accuracy on numbers is the product. Run a Haiku vs. Sonnet bake-off for chart descriptions using the golden set, then pick based on the score. **Riya to decide budget (Q4).**

### D-003 · PDF parser · **Accepted 2026-10-20: Docling** (based on the spike; see Current State)
PyMuPDF is kept only for fast tasks (page images, quick text scans for metadata).
Candidates: **Docling** (open source, strong table structure, free, local) · PyMuPDF (very fast, weak on tables) · paid parsers such as LlamaParse (good, but cost and a vendor dependency) · Claude reading every page (best quality, highest cost).
**Proposed:** Docling for structure + PyMuPDF for page images + Claude vision only for chart and complex-table pages. Confirm with the spike on real files.

### D-004 · Embeddings · **Accepted 2026-10-21: `BAAI/bge-small-en-v1.5`, local** (re-evaluate with the eval set)
Options: local open-source embedding model (free, private, good enough to start) vs. a hosted API such as Voyage, which has finance-tuned models (better retrieval, small cost).
**Proposed:** start local behind an interface so the model can be swapped later. Measure with the eval set before paying.

### D-005 · Vector store · **Accepted 2026-10-21: LanceDB**
Options: LanceDB (embedded, file-based, has full-text + vector **hybrid search**) · Chroma (simple, weaker hybrid search) · Qdrant (server-based; overkill for an MVP).
**Proposed:** LanceDB. No server to run, it's just files in the project folder, and it handles hybrid search. Financial questions depend on exact terms like "EBITDA", tickers and fiscal years, where keyword search beats pure semantic search.

### D-006 · Language + UI · **Proposed**
**Python** (best PDF/ML ecosystem) + **Streamlit** for the MVP UI (fast to build, easy to read for a non-engineer). A proper web frontend can come later if needed.

### D-007 · "Which PDF?" routing · **Proposed**
Don't make the user choose. At index time, pull **document metadata** (company, fiscal year, report type) and attach it to every chunk. At question time, pull entities from the question ("Infosys", "FY23") and use them as filters, then search across all documents. Also prepend a short context line to each chunk ("Infosys FY23 Annual Report, Segment results, p.142"), a technique called *contextual retrieval*, which clearly improves retrieval accuracy.

### D-009 · Local vs. Claude API · **Proposed (2026-10-20)**
**Only two jobs need a large "brain" model:** (1) reading chart and table page images during indexing, and (2) writing the final answer. Everything else (PDF parsing, embeddings, vector database, UI) runs locally for free.

| Option | Pros | Cons |
|---|---|---|
| All local (Ollama + an open model) | No per-use cost, fully offline | On an 8 GB M1, only small (~3–4B) vision models fit. They're slow and make mistakes reading dense financial tables, and the user persona *needs* correct numbers and good plain-English explanations. |
| **Local system + Claude API for the brain** | Top-tier accuracy on tables, charts and explanation; no hardware limits | Costs money per use; needs internet; page content leaves the machine (acceptable: 10-Ks are public) |

**Proposed:** everything local except the brain calls, which go to the Claude API. Put the LLM behind a small interface so a local model can be swapped in later as a learning experiment.

**Alternatives discussed 2026-10-21** (Claude disclosed a possible bias here, since it's recommending its own maker's API):
| Option | Notes |
|---|---|
| **Anthropic Claude API** (recommended) | Strong at reading tables and careful reasoning; native PDF/image input; **built-in citations** that point to page numbers (fits Q5); prompt caching lowers repeat cost; the same account Riya already uses. |
| OpenAI GPT API | Comparable top-tier quality; mature ecosystem; also offers embeddings. |
| Google Gemini API | Strong at long documents and images; often cheaper per token. |
| Open models via hosted providers (OpenRouter, Together, Groq, etc.) | Cheapest; one key reaches many models; quality varies on dense tables. |
| Local via Ollama | Free and offline, but limited by 8 GB RAM (see above). |
**Why it's low-risk:** the LLM sits behind one small interface, so switching providers means changing configuration, not rewriting. Plan: start with Claude, then run a **bake-off on the golden set** across 2–3 providers once the eval harness exists (Phase 3). Let the score decide.

### D-010 · Fiscal-period alignment · **Accepted 2026-10-21**
Match companies by **period end date**, not by the "FY" label. Answers explain the mismatch in plain English (e.g. "NVIDIA's fiscal 2026 ran Jan 2025 – Jan 2026, roughly calendar 2025"). Implementation: store `period_start`, `period_end` and `fiscal_year_label` per document and per table column.

### D-011 · Duplicate figures across filings · **Accepted 2026-10-21**
Default to the **most recent filing** for any figure. If the user explicitly refers to an older report ("in AMD's 2024 annual report…"), use that one. Mention it when a newer filing restated the number.

### D-012 · Answer format: facts vs. interpretation · **Accepted 2026-10-21**
Every answer has two clearly separated parts:
1. **What the filing says**: facts only, each with a citation (file + page).
2. **What this might mean**: plain-English interpretation, clearly labelled as IndexIt's reading, not the company's.
Rules: no buy/sell/hold advice; no outside knowledge presented as if it came from the filing; if the documents don't cover something, say so.

### D-013 · Expose retrieval as an MCP server · **Accepted + built 2026-10-23** (Riya's idea)
Wrap the *search* half of IndexIt as an MCP server so Claude Code / Claude Desktop can use it as a tool. The AI client then acts as the brain.
- **Tools:** `list_filings()` (which docs, company, fiscal year) · `search_filings(query, k)` (top passages with file + page) · `read_page(file, page)` (full page, to check a table) · plus an MCP *prompt* carrying the D-012 answer format.
- **Pros:** answers come from Claude Code's own model, so no API credits are needed if Riya's Claude Code runs on a subscription. **Agentic RAG for free**: Claude Code can search several times and refine, which is what questions #22–25 need. Small to build (~1 file), since retrieval is already separate from the brain. Teaches MCP.
- **Cons:** not the product for the target user (non-experts won't use Claude Code). Less control: model, effort and system prompt belong to Claude Code, so the D-012 format is a request, not a guarantee. Harder to score reproducibly. Subject to subscription usage limits.
- **Proposed:** build **both front doors on one shared core**. The MCP server is for development, exploration and power users. The IndexIt app (Claude API) is for target users and the official eval scores.
```
                ┌─ MCP server ──→ Claude Code / Desktop (brain = client's model)
 core (index + ─┤
   search)      └─ IndexIt app ─→ Claude API (brain = llm.py, D-012 enforced)  ← eval runs here
```

### D-014 · App → Claude Code (subscription) → MCP · **Accepted for personal use, built 2026-10-23** (Riya's idea)
Riya decided: she's the only user for now. Build the Claude Code version first, experience the latency, *then* decide on the API version. Guardrails come from both a prompt (behavior) **and** configuration (enforcement); see `agent.py`.
**Later idea (parked):** let others download IndexIt and use *their own* Claude subscription. ⚠️ The same Agent SDK note applies ("does not allow third party developers to offer claude.ai login or rate limits for their products… unless previously approved"), so distributing it that way would need Anthropic's approval; otherwise each user brings an API key. Revisit before any distribution.
Riya has **Claude Pro**. Idea: the IndexIt app runs Riya's Claude Code in the background (Agent SDK / `claude -p`), and Claude Code answers by calling the IndexIt MCP server.
- **Policy (checked 2026-10-23, Agent SDK docs):** *"Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Use the API key authentication methods… instead."* → **For other users, the brain must use an API key.** A Pro subscription can't power an app that other people use.
- **Personal use** (Riya, on her own Mac, asking her own questions) is Riya using her own Claude Code through a nicer front end. That's reasonable for a learning project (Claude's reading, not legal advice).
- **Technical caveats even for personal use:** slower (Claude Code start-up + several searches ≈ 30 s–2 min per answer); Claude Code is a coding agent, so it needs our own system prompt; **security**: filings are untrusted text, so Claude Code must be limited to the IndexIt MCP tools only (no Bash/Edit/Write), otherwise injected text in a PDF could trigger actions on the Mac; it shares Pro usage limits with Riya's coding.
- **Proposed:** make the brain a switch (extends D-009):
  - `brain = claude-code`: Agent SDK, IndexIt MCP tools only, Riya's subscription. **Personal/local mode.**
  - `brain = api`: `llm.py` with an API key. **Required for anyone else**, and used for the official eval.
  Both use the same MCP server and core, so the eval can compare them.

### D-015 · Short answers + 3 "dig deeper" questions, streamed; no UI yet · **Accepted 2026-10-25** (Riya)
- Answers are short (~150–250 words) but **complete for the question asked**: they open by directly answering it (company + period), cover every part briefly, and never mention what was left out.
- Instead of a "Go deeper" button, every answer ends with **exactly 3 follow-up questions** that build on the answer and that the filings can answer. The user picks one, and it continues in the **same session** (faster: 18 s → 13 s on the test).
- The answer streams as it's written (CLI). Finding: little perceived gain so far, because thinking and searching dominate and the writing itself is quick.
- **No UI until the logic is right.** Everything is CLI for now: `uv run indexit ask-agent "<q>"`.

### D-016 · Choose models on accuracy first, speed second · **Accepted 2026-10-25** (Riya)
"The user won't have any idea" if something is wrong, so **an answer with any wrong or unsupported claim fails**, however complete or fast. Implemented in `evaluate.py`: a separate **fact-checker agent** (Opus, high effort, same locked-down tools) opens the cited pages, checks every number, date, name and calculation, and returns structured JSON (wrong / unsupported claims, coverage of answer-key points, format). Ranking: accuracy → coverage → speed.
- Caveat: Claude is grading Claude. This is mitigated by requiring page evidence for each flag, and by Claude spot-checking flagged claims against the PDFs before trusting them.
- Pilot (Sonnet, #6 + #25): #6 PASS (handled the fiscal-year trap); #25 FAIL: an **unsupported overclaim** ("AMD doesn't invest in AI customers"). The checker's evidence was verified (AMD FY25 p73), and the golden rubric for #25 was corrected.
- Possible later option: a built-in fact-check step before showing answers. It conflicts with streaming, so decide after seeing error rates.

### D-017 · Avoid overfitting: bigger corpus + held-out test set · **Accepted 2026-10-25** (Riya's idea)
Tuning prompts and choosing models on 4 filings / 2 companies risks optimising for our own test. So:
1. **Corpus:** expanded to 14 filings / 6 companies (see Current State). Later: add a bank and a pharma company to test very different statements and jargon.
2. ~~Dev set = the current 25~~ → **Superseded 2026-10-25 by eval set v2:** one file, 56 questions, Set column (27 dev / 19 test / 10 extra), balanced 3 dev + 2 test per company. See Next Steps 0000.
3. **Test set:** never tune on it; run it only at decision points (e.g. model choice). Claude drafted most of the test questions (from the PDFs, without IndexIt), so Riya adding her own is still valuable.
4. Model selection (D-016) runs on dev + test after this.

### D-018 · Company-aware search ("mentions vs. about") · **Built 2026-10-25**
- **Problem:** pages that *mention* a company in another company's 10-K outranked its own filing ("Microsoft's risks" → AMD's "If we lose Microsoft's support…").
- **Fix (`search.py`, `documents.py`):** detect companies named in the question (company name + aliases such as AMD, AWS, JPM, MSFT; matching ignores case except ambiguous aliases like "Chase") → search **only those companies' filings** (LanceDB pre-filter on file names). If several companies are named, each gets an equal share (≥3 passages). If none is named, search everything. The MCP `search_filings` tool takes an optional `company` to pin one explicitly; the agent prompt explains when to use it.
- **Why metadata filtering rather than re-embedding:** no re-index needed, deterministic, and it uses the cover-page metadata we already trust. *Later option:* prefix each passage with "Company FYxxxx 10-K, section…" before embedding (contextual retrieval) to also improve ranking *within* a filing.
- **Measured with the new free `uv run indexit eval-search`:**
| Search mode | Expected page in top 8 (23 golden Qs) | Right-company share (golden + 7 probes) |
|---|---|---|
| plain (before) | 11/23 | 85% |
| company-aware | 11/23 | **92%** |
  Per probe: "Microsoft's biggest risks" 50% → **100%**; "Microsoft revenue FY2026" 62% → **100%**; "Does Microsoft depend on NVIDIA chips?" 0% → 50% (now split Microsoft/NVIDIA, which is correct for a two-company question). Agent check: the Microsoft risks answer cites only Microsoft's filings, 15 s.
- **What it didn't fix:** the expected page is still missing in 12/23 golden questions. These are *within-filing* ranking problems (boilerplate footers, near-duplicate statements, chunking), the next retrieval target.
- Known limitation: a lowercase "chase" isn't recognised as JPMorgan (so the verb isn't mistaken for the bank).

### D-019 · Cleaned index `clean_v2` (within-filing search fix) · **Accepted + live 2026-10-25**
**Diagnosis of the 12/23 page misses:** (A) footer junk pieces (#3, #17, #19); (B) everyday wording vs filing wording ("making money", "where does the money come from", #4, #5, #7, #9, #23); (C) outdated questions #14/#15, now reworded to name NVIDIA and AMD; (D) a strict metric: the answer was on *another* page (#3 p75, #12 balance sheet). Added a fairer metric: **key figures in results** (do the answer key's exact figures appear in what search returned?).

**What we tried, measured with `eval-search` / `spikes/ablate_chunking.py` / `spikes/rerank.py`** (23 golden Qs with pages; 12 with key figures):
| Variant | Expected page in top 8 | Key figures | Verdict |
|---|---|---|---|
| simple_v1 (baseline) | 11/23 | 67% | |
| + boilerplate removal, line-aware pieces, tail merge | **12/23** | 67% | ✅ adopted. **Junk passages in top-8 results: 54 → 0** |
| + context line *embedded* ("[AMD FY2025 10-K · Item 8 · p.74] …") | 9/23 | 67% | ❌ hurts with our small embedding model. Context now stored separately and shown to the agent as `section=` |
| + hybrid keyword search (LanceDB full-text index + RRF) | 10/23 | 67% | ❌ no help on raw user wording; off (`HYBRID=False`). Retest on agent-written queries |
| + reranker MiniLM-L6 (top 30 → 8) | 14/23 | 67% | ⏸ +2 questions (could be noise), +0.5 s per search; retest on the larger dev + test set |
| + reranker bge-reranker-base | 13/23 | 62% | ❌ slower (3 s) and no better |
- **Not fixed by search tweaks:** category B (everyday wording). In agent mode the agent rewrites questions into filing language itself. Check: "How has AMD's stock done…" → the agent searched "AMD stock performance graph cumulative total return…" and hit p62 in one search. So the raw-question eval *understates* agent-mode retrieval. Next: log the agent's own queries during evals and score retrieval on those.
- Section labels: each page gets the 10-K Item it belongs to (a heading near the top labels the page; one lower down applies from the next page; table-of-contents pages are skipped).
- **Accuracy finding (agent check, Sonnet):** the AMD stock answer had correct numbers but a **wrong conclusion**: "AMD ($271) trailed the S&P 500 ($199)" (it *beat* it; verified AMD FY24 p53). This is the "right numbers, wrong words" error type. Evidence for D-016's model comparison.

### D-020 · Latest-filing-first search + section label fixes · **Built 2026-10-26**
Diagnosis of the balanced-dev misses (Apple, AMD, JPMorgan at 0/3): (1) **older filings crowd out the latest**: Apple has 3 years of filings, so "Apple iPhone revenue" returned FY2023/FY2024 statements; (2) **JPMorgan section labels were wrong**: its annual report follows the formal Items with no Item headings, so MD&A pages were labelled "Item 15"/"Item 1A". These labels are shown to the agent, so this was a wrong-content risk; (3) **everyday words vs jargon** ("bad loans" vs "provision for credit losses"). *Not fixed on purpose:* a glossary written from these dev misses would be overfitting; the agent already rewrites queries into filing language.
- **Latest first (`search.py`, D-011 applied to search):** per company, ¾ of the passages come from the latest filing + the filing for any fiscal year the question names ("2024"); ¼ stay open to older filings.
- **Sections (`clean_pipeline.py`):** a capitalised heading at the top of a page starts a section ("EXECUTIVE OVERVIEW" → "Executive Overview"); Item headings must have punctuation after the number (a wrapped "Item 15 of this Annual Report…" had relabelled NVIDIA's MD&A as Item 15); backwards Item jumps are treated as cross-references. Verified: every filing's Items now run in order, and JPMorgan shows Executive Overview, Consolidated Results of Operations, Credit Portfolio, Capital Risk Management…
- **`index --rebuild`:** re-chunks every file. Without it, unchanged PDFs are skipped, so pipeline code changes would silently not reach the index.
- **Scorer bug fixed:** "NVDA-FY26 · p51 (also NVDA-FY25 p52)" had put p51 under FY25; codes and pages are now read left to right.
- **Dev results (company-aware, clean_v2):**
| | Expected page in top 8 | Key figures |
|---|---|---|
| before | 11/25 | 43% |
| **latest-first + fixes** | **14/25** | **55%** |
| + MiniLM reranker | 14/25 | 60% |
| + bge-reranker-base | 12/25 | 52% |
  Per company now: NVIDIA 2/3, AMD 1/3, Apple 1/3, Microsoft 2/3, Amazon 2/3, Tesla 2/3, **JPMorgan 0/3** (jargon gap), cross-company 4/4.
- **Reranker: not adopted.** Two tests (NVIDIA/AMD set: +2 pages; balanced dev: +0 pages, +5% figures) show a small, inconsistent gain for +0.6 s per search, and the agent runs several searches per answer.

### D-022 · Docling structured tables (step 2b) · **Accepted 2026-10-27: small-to-big**
- **Design:** keep the clean text pipeline for prose, and add **each Docling table as its own passage** (`docling_pipeline.py`, index `docling_v3`): the full markdown table with real column headers ("| | Years ended – September 27, 2025 | …"). **Searched by its title + row/column labels, not the numbers** (`embed_text`). Title = the sentence just before the table, joined with the line above when that sentence is a units line ("CONSOLIDATED STATEMENTS OF OPERATIONS (In millions…)"). Tables > 3,000 chars are split into row groups, each repeating the header.
- **`read_page` now also returns that page's structured tables**, so the agent reads clean tables when checking numbers. This is likely the biggest win.
- **Cache:** `data/parsed/<file hash>.tables.json` (`tables.py`), so re-indexing never re-runs Docling for an unchanged PDF.
- **Speed (corrected):** earlier "30–60 min for 16 filings" was wrong. Measured with models loaded: **1.3 s/page OCR off vs 1.5 on** (same tables; digital PDFs don't need OCR), and 0.9 s/page on Apple FY25 (80 pages → 50 tables in 73 s). Full corpus ≈ 2,440 pages ≈ 40–55 min, one time. Run in batches of 40 pages for memory (8 GB). Log: `data/docling_index.log`.
- **Built 2026-10-26 (~23:10):** all 16 filings → **2,308 tables**; `docling_v3` = 6,567 text + 2,308 table passages. 13 "cells dropped from the table" warnings across ~2,440 pages. **Spot-check: 10 key tables (all 7 companies, incl. JPM capital/deposits) kept every figure checked** (`data/parsed/`).
- **Search result: no change.** clean_v2 and docling_v3 both score 14/25 pages and 55% key figures (dev). Diagnosis: table passages searched by *labels only* rank too low (NVIDIA's revenue-by-market table: distance 0.46 vs 0.22–0.30 for text). Spike `spikes/table_embedding.py`: searching tables by *full text* puts 38 (vs 15) table passages in the top 8 but finds **fewer** pages (13/25): they crowd out text passages from the *same* pages.
- **Conclusion:** search already finds table pages through the text passages; the value of Docling is in **what Claude reads**, not in finding pages. **Proposed design (for Riya, 2026-10-27): "small-to-big" retrieval**: search text passages as now, and attach the **structured tables of each result's page** to what `search_filings` returns. This also fixes the agent's never-opens-pages habit for tables, and replaces separate table passages (`search.TABLE` stays `clean_v2` until decided). It must be measured with an **answer eval** (search scores can't show it by construction).

- **Built 2026-10-27 (Riya: go):** `search_filings` returns the passages, then *"Structured tables from the pages above"*: every Docling table on each result page, in rank order, each page once, capped at **16,000 chars (~4k tokens)** per search (`TABLE_BUDGET_CHARS`). Tables are **compacted** (Docling's cell padding removed: median 2.9k → 1.3k chars per page, same cells). Sample searches: 5–13 tables, 5–9k chars. Search index unchanged (`clean_v2`); `docling_v3`/`v3b` kept for reference. The fact-checker sees the same tool output, so it verifies against the same tables.

### Finding (2026-10-26): the agent is agentic but *shallow*, and mostly ignores `read_page`
From the stage 1 tool-call logs (27 dev questions):
| Config | Searches | `read_page` calls | Questions with ≤1 tool call |
|---|---|---|---|
| Opus medium | 60 | 5 | 8/27 |
| Opus high | 65 | 4 | 8/27 |
| Sonnet | 48 | **0** | 12/27 |
- The prompt's "use read_page before quoting numbers from a table" is largely ignored; answers come from search snippets after 1–2 searches. Example: Sonnet #22 searched twice, stopped, and missed AMD's $853M one-off (p70).
- **Impact on D-022:** the structured tables in `read_page` will rarely be seen, so the Docling **table passages in search results** matter more.
- **Options (to decide with Riya):** (a) stronger prompt rule ("read the page before stating any number"): cheap, but models follow such rules loosely; (b) **built-in reading**: `search_filings` attaches the full page + its structured tables for the top hits. Reliable, pairs with Docling, adds tokens and latency; (c) a verification pass before answering: most accurate, slowest. Claude's recommendation: (b), measured on dev.

### D-021 · Answering model: Sonnet 5.5 (default/high effort) · **Accepted 2026-10-27** (Riya; to be confirmed on the test set)
Evidence: `eval/runs/2026-10-26_1639/analysis.md` (27 dev questions, every flag verified by Claude against the filings).
| Config | Strict accuracy | Answers with a serious error | Median time | ≈API $ (27 Qs) |
|---|---|---|---|---|
| Opus 5.5 medium | 18/27 | 5 | 18 s | $3.32 |
| Opus 5.5 high | 16/27 | 5 | 19 s | $3.63 |
| **Sonnet 5.5 high** | **23/27** | **2** | **14 s** | **$1.30** |
- **More effort made Opus *worse*:** longer, more interpretive answers with outside knowledge ("2.3 billion devices") and loose quantifiers ("margins nearly doubled"). For a user who can't spot mistakes, that's a risk.
- Opus covers slightly more of the answer key (93–94% vs 89%); Sonnet's misses are omissions, which are safer than wrong statements.
- The checker is Opus, so any self-preference bias would favour Opus. Opus scoring worse strengthens the result.
- **Prompt fixes indicated for every model:** no outside facts/numbers even in "What this might mean"; follow-up questions mustn't assume unverified facts; avoid loose quantifiers unless computed.

### D-023 · UI: local web app, typewriter style · **Accepted + built 2026-10-29** (Riya)
- **Riya's choices:** local web app (over Streamlit: full design control, natural streaming, one persistent Claude session); **Courier Prime** (a readable typewriter face; Special Elite rejected as tiring to read); **scrolling thread + "New conversation"**; rotating **thinking verbs** while Claude researches.
- **Run:** `uv run indexit app` → http://127.0.0.1:8765 (listens on this Mac only). Code: `src/indexit/web/` (`app.py` Starlette server, `static/` page). No new installs: Starlette/uvicorn came with `mcp`; now declared in `pyproject.toml`.
- **How it works:** one worker task owns the Claude Code session (the SDK client must stay in the task that opened it); questions queue and run one at a time; the session is opened at start-up and again right after "New conversation", so questions don't wait for start-up. Answers stream as JSON lines: `step` (research trail), `text` (words as written), `done`, `error` (incl. the Pro limit message). Model: **Sonnet 5.5 high** (D-021). Same guardrails as the CLI agent.
- **Design:** paper + ink, one ribbon-red accent reserved for sources, pencil-grey "What this might mean · my reading" margin note (makes D-012's fact/interpretation split visible), dig-deeper questions as clickable cards (asked in the same conversation), status verbs typed out letter by letter (only the status; the answer appears at real speed, no fake delay), research trail collapses to "2 searches · 12 s". Light + dark mode.
- **Tables (Riya asked whether indexed tables reach the output):** Claude reads them in every search, but answers are text. Now **every citation is a link** that opens a side panel with **that page's Docling tables** (the filing's own data, not model output, so no accuracy risk) + "Open this page in the PDF" + the page text. Filings drawer lists the folder's filings.
- **Safety:** answer text is escaped before rendering (filing text is data, never HTML); PDFs/pages served only for files in the filings folder (path tricks → 404).
- **Logging:** every Q&A is saved locally to `data/conversations/<session>.jsonl` (question, answer, the agent's searches, time, cost) for replaying real queries later.
- **Tested 2026-10-29:** endpoints, path safety, a live question (Tesla, 2 searches, 12 s), the renderer against every citation format seen in evals (incl. `pp.63, 68`, `pp.37–38`, multi-source `;`), screenshots in light/dark and of the citation panel. Not yet: Riya's own hands-on test.
- **Revised 2026-10-29 (Riya):** accent **red → ink green** (#2e6b3f light / #86c596 dark; feels more promising), errors keep a muted red; send button = **arrow icon**; header spans the full window with **"+ New conversation" at the far right** (History · Filings · New conversation).
- **Saved conversations (Riya):** each conversation is saved to `data/conversations/<id>.json` (question, answer, research steps, stats, Claude session id). **History** panel lists them, newest first; opening one redraws it and **resumes its Claude Code session** (SDK `resume`), so follow-ups keep full memory. If a session can't be resumed (e.g. Claude Code cleaned up old transcripts, ~30 days), Claude gets a recap of the last 5 Q&As instead. A fresh session stays pre-opened for the next new conversation. Tested: follow-up in the same conversation (8 s, no new search), a second conversation, hopping back (remembered the 26.2% figure, 6 s). Riya's two pre-history questions (Amazon/AWS) were converted into a saved conversation; the old log `2026-10-29_150513.jsonl` is kept.
- **Deferred:** output guard (see 2026-10-28); a downloadable desktop app wrapper; deleting/renaming conversations.

### D-024 · Two-column app + filings library (add, index, remove) · **Accepted + built 2026-10-29** (Riya)
- **Layout (Riya):** two columns, **1/3 | 2/3**. Left: **Conversations** (fixed height ~34% of the window, scrolls) above **Library** (rest of the height, scrolls), always visible ("nothing hidden, but minimal"); right: the conversation. "+ New conversation" sits in the left column's header. Citation tables slide over the conversation column. Narrow windows: the left column becomes an overlay behind a "Conversations & library" button. Replaces the earlier History and Filings drawers.
- **Library:** one row per company with its filing count. Click a company to see its filings (year, period end, pages, source, Open PDF, Remove, Retry on failure). Indexing progress shows inline under the company ("FY2025 · Searchable · Extracting tables: p.40 of 84…").
- **Folder (Riya: "anything added should be in a folder"):** filings moved `data/sample` → **`data/filings`** (no re-index: the index stores file names). `data/filings/library.json` is the library: per file the company / fiscal year / period end (overriding the cover where corrected), **aliases learned at add time** (the name the user typed, the SEC ticker; no manual alias list for new companies), status (`queued → indexing → searchable → ready`, or `failed`), tables (`pending/running/done/failed`), source, added date, file hash. A folder without `library.json` still works as a plain folder of PDFs (evals, CLI).
- **Revised (Riya, 2026-10-29):** "+ New conversation" is a small link like "+ Add filing". **Adding a filing opens a centred modal** with room to breathe, in two steps in the same window: *Add a filing* (company, year, method, drop zone or SEC contact) → *Check before adding* (the confirmation card). A card left unconfirmed shows as "N filing waiting for your check · Review" in the Library.
- **Adding (Riya: company + year for both methods; card always):**
  - *Upload* (revised by Riya 2026-10-29): **no company/year asked**; the cover page supplies them and the card shows them for checking/editing. **Bulk upload**: drop or choose several PDFs at once; one card per file plus **"Add all N"**. (Trade-off: no typed-vs-cover cross-check for uploads; the card is the check.)
  - *Fetch from the SEC*: company name or ticker + fiscal year → EDGAR company list → that fiscal year's 10-K (by period-of-report year, IndexIt's FY convention) → HTML with images inlined → **printed to PDF with headless Chrome** so page citations work like uploads (`sec.py`).
  - Every added file lands in `data/incoming/<id>/` and gets a **confirmation card**: what IndexIt read from the cover vs what was typed, with warnings (year mismatch, company mismatch, unreadable cover, not a 10-K, scanned/no text → blocked, exact duplicate → blocked, a second filing for the same company-year, older than the latest). Company/year are editable; "Add to library" moves it into `data/filings`.
  - PDFs dropped straight into `data/filings` in Finder get a card too; cancelling one moves it to `removed/` (it's the user's own file).
- **Indexing (Riya: searchable before tables):** one filing at a time, each in **its own process** (`python -m indexit.library index <file>`; Docling's memory is freed when it ends, which matters on 8 GB). Text first → searchable; then Docling tables → ready. Unfinished jobs resume when the app restarts. Log: `data/indexing.log`. **Measured:** a 94-page 10-K was searchable **16 s** after confirming and ready (with tables) after **~1 min 50 s**.
- **Open conversations learn about new filings:** if the library changed since a Claude session started, the next question carries the current filings list.
- **Remove:** takes the filing out of search (index rows deleted), marks it removed in the library, and **moves the PDF to `data/filings/removed/`** (recoverable, never deleted).
- **SEC contact (privacy, Riya):** the SEC requires a contact email on automated requests. Riya types it into the app's own form; the server saves it to `data/settings.json` (permissions 600) and sends it only in the request header to sec.gov. No endpoint returns it (the page only learns whether one is saved). **Claude never reads that file or logs the value.**
- **Fix found by testing:** the live index `clean_v2` predated the `kind` column, so adding rows failed; added the column (all existing rows `text`).
- **Tested 2026-10-29:** duplicate upload (blocked, with year-mismatch and older-than-latest warnings), cancel, a full add → index → ready → remove cycle on a modified copy (cleaned up afterwards), search eval unchanged after the folder move (14/25, 55%), screenshots of all states, one live question in the new layout. **SEC fetch tested by Riya (2026-10-29):** Walmart FY2025 → printed to a 132-page PDF, confirmed, indexed (ready with tables). Bug found: the printed web cover has fill-in underlines, so the cover-read name was ". ____ Walmart". Fixed: names are cleaned of underlines/punctuation/SEC suffixes (`_short_name`); **SEC fetches use the SEC's company name**; and a filing for a company already in the library takes **the library's existing name** (matched by ticker or name, e.g. SEC "AMAZON COM INC" → "Amazon.com"). Walmart's entry corrected to "Walmart" (alias WMT).

### D-025 · No multimodal layer: scoped out on evidence · **Accepted 2026-10-30** (Riya)
- **Decision:** drop the multimodal RAG build (charts as images, page-image search). IndexIt stays text + structured tables.
- **Evidence:** 12 embedded images across the first four filings (parsing spike, 2026-10-20); the recurring stock-performance chart prints its data as a table below it; Docling keeps every key figure checked with its headers (D-022); the one chart-type eval question was answered from text; no eval error traced to a missing image.
- **Why it matters (Riya):** the project began as "multimodal RAG"; working through what the documents and the user actually need showed it wasn't, and that judgement is the learning. Multimodal remains the right tool for chart-heavy documents (investor decks, ESG reports, scans) if IndexIt ever covers them.
- Supersedes the "multimodal (page images) only if table errors remain" plan and the investor-deck learning project.

### D-026 · Key-figures table + compare tool + Compare view · **Accepted + built 2026-11-01** (Riya)
- **Why:** questions that rank companies ("who spends most on R&D?") took one search per company: 7 searches at 7 companies, ~100 at 100. Riya picked this from the "If I took it further" list.
- **Choices (Riya):** (1) **rules in code** read the figures (free, instant, repeatable, run when a filing is added; anything unsure is left out and the agent falls back to search), not Claude reading each statement or SEC XBRL (no page citations); (2) **income statement + balance sheet**: revenue, cost of revenue, gross profit, R&D, operating income, net income, cash, total assets, debt (EPS left out: not comparable across companies); (3) **a compare tool** (`compare_companies(metric, fiscal_year, companies)`), not text-to-SQL.
- **How:** pick the consolidated statement by title (not MD&A summaries or long captions); read each column's period end and units from the headers; match row labels to standard names (bracketed notes ignored); net income = the company's own share; debt = debt lines on the face of the balance sheet; banks (a "Deposits" liability) excluded from cost, R&D, cash and debt comparisons. Checks drop figures that don't add up. Latest filing wins (D-011); restatements are noted. Ratios and growth are calculated by code, with their inputs and units shown.
- **Evidence:** figures vs SEC XBRL: 251/254 exact, 0 different. Cross-company eval (run `2026-11-01_1328`): 8/9, 100% coverage, median 10 s; #52 went from 7 searches / 25 s / $0.19 to 2 calls / 14 s / $0.03. The one flag came from missing units in the tool's output (fixed).
- **App (Riya):** *+ Add · Compare* in the Library header; Compare opens in the main pane: figure chips, a year picker, ranked bars with period and source page, what's not compared and why, and **rule-based insights** (leader, lowest, anything below zero, rank divergence) each with *Ask IndexIt why →* (starts a new conversation; plan usage only when clicked). No Claude-written summaries (cost per view, overreach risk). **Side by side (Riya, 2026-11-01):** a second tab compares two companies on every figure (Size and growth · Profitability · Investment · Balance sheet), each value with its page, a Difference column (× for amounts, percentage points for ratios), missing lines per company, a fiscal-year note when year-ends differ, and rule-based pair insights (relative size, growth in opposite directions, the widest margin gaps of 3+ points). Banks are now also excluded from total-asset comparisons. **Industry groups deferred (Riya):** with 10 companies most industries have one or two members; revisit with SEC industry codes (SIC) as suggestions once the library has 3+ companies in several industries. Company trends deferred.
- **Limits:** labels outside the known list stay blank (e.g. Amazon's "technology and infrastructure" is not R&D, by design); Amazon and Alphabet show long-term debt only; cash excludes short-term investments (stated in the notes).

### D-008 · Evaluation-first · **Proposed**
Build the golden question set **before** tuning. Every later decision (parser, model, chunk size, reranker) gets judged by its score instead of by gut feel. This is the main place where product judgment drives engineering.

---

## 7. Session Log

### 2026-10-19 — Kickoff
- Set the MVP scope and the working model (PM + engineering partner).
- Proposed the hybrid multimodal RAG architecture and decisions D-001 to D-008, with a cost model.
- Next: Riya provides sample PDFs + golden questions + answers to Q1–Q5; Claude runs the parsing spike.

### 2026-10-20 — Persona, scope, local vs. API, RAG types
- User = non-experts who don't know what to look at in filings. The product must explain, not just look things up.
- MVP documents = 10-Ks only.
- Cost is discussed when an action spends money, not upfront.
- Proposed D-009 (local system + Claude API brain), driven by the 8 GB M1 limits.
- Revised D-001: build simple RAG as a baseline first, then add layers driven by eval scores.
- Wrote [LEARNING.md](LEARNING.md) explaining the types of RAG.
- Clarified: smart chunking is the foundation; multimodal is conditional. Explained search text vs. content records.
- Riya added 4 10-Ks (NVIDIA FY25/FY26, AMD FY24/FY25). Installed uv + Python 3.12 project.
- Parsing spike: Docling ✅ vs PyMuPDF ❌ on income statements → D-003 accepted. Found two product questions: fiscal-year mismatch (Q6) and overlapping/restated data (Q7).

### 2026-10-21 — Decisions + golden set draft
- Riya accepted D-010 (align by period end date, explain the mismatch) and D-011 (latest filing unless the user asks for an older one).
- Discussed alternatives to the Claude API (added to D-009). Plan: start with Claude, then bake off providers on the golden set in Phase 3.
- Claude drafted 21 golden questions with verified answers and pages (`eval/golden_questions.md`); `spikes/find.py` is the search helper.
- Explained the roles of Claude API vs. Ollama and the 8 GB RAM limit (LEARNING.md).
- Riya added 4 analysis questions (#22–25: growth sustainability, revenue stability, geopolitics, investing in customers). Claude researched the rubrics. Findings: AMD's 2025 profit includes an $853M one-time tax benefit; NVIDIA's private investments rose from $3.4B to $22.3B, but the 10-K doesn't say whether investees buy NVIDIA chips; AMD gave OpenAI a share warrant tied to GPU purchases. These questions need rubric grading (an LLM judge) and multi-step retrieval. Raised Q8 (interpretation vs. facts only).
- Riya accepted Q8 → **D-012** (two-part answers: cited facts / labelled interpretation; no advice).
- Built the simple RAG baseline (see Current State): installed sentence-transformers, lancedb, anthropic (SDK 2.1). Indexed the 4 filings. Free retrieval tests surfaced boilerplate-footer noise. No API key on the machine yet, so `ask` hasn't been run.

### 2026-10-23 — MCP + Claude Code agent
- Riya: Pro subscriber and the only user. Wants App → Claude Code → MCP, with guardrails, then a latency check before deciding on the API.
- Verified the policy in the Agent SDK docs: subscription login can't power apps for other users (D-014 note).
- Built `mcp_server.py`, `agent.py`, `documents.py`, `prompts.py`, `search.py` and the `ask-agent`/`filings` commands. Installed claude-agent-sdk 0.2.173 (bundles Claude Code 2.1.309) and mcp 2.3.0.
- Found and fixed exposure of claude.ai connectors to the agent. Added a fail-closed guardrail.
- Results: simple question ~30 s; analysis question #22 ~63 s with 8 tool calls and a very strong, verified answer.

### 2026-10-25 — Latency optimisation
- Profiled where time goes: answer writing ≈ 60%. Applied embedding-model warm-up and the filings list in the prompt.
- Compared Opus default / Opus low / Sonnet / Haiku on Q7 and #22: 2–3× faster options all keep the core facts. All missed the p70 facts, a retrieval issue. Raised Q9 (answer length) and Q10 (default model).
- Riya: shorter answers + 3 dig-deeper questions (not a button), streaming, **no UI yet**, and quality over speed → D-015, D-016.
- Built: new short-answer prompt; `AgentSession` (persistent multi-turn session, streaming); interactive dig-deeper loop in `ask-agent` (`--once` to skip); `evaluate.py` + `uv run indexit eval --configs … --questions …` with a fact-checker agent. The fail-closed guardrail caught the SDK's internal `StructuredOutput` tool, which is now allowed only for structured-output sessions.
- Pilot eval: Sonnet 1/2 pass; the checker found a real overclaim on #25.
- Corpus: Riya added Apple, Microsoft, Amazon, Tesla, then JPMorgan (16 filings / 7 companies). Fixed cover detection twice (Amazon/Microsoft formats; JPM two-column cover) → D-017.
- Company-aware search (D-018) + free `eval-search`. Cleaned index `clean_v2` is live (D-019), with ablations of the context line, hybrid search and rerankers. Found a "right numbers, wrong conclusion" error in a Sonnet answer.
- Remaining latency levers, not built yet: streaming the answer in the UI; a persistent session (no startup per question); quick-answer-first; better retrieval (fewer searches); an answer cache.

### 2026-10-27 — Model decided, prompt fixes, small-to-big tables
- Riya: is an Opus second chance worth the plan usage? Claude: no. Sonnet led clearly (23 vs 18/16 strict, 2 vs 5 serious), and Opus would have to beat it, not tie. But Sonnet isn't error-free (2/27 serious, misses more of the key: 89% vs 93%). → **D-021 accepted.**
- Built the prompt fixes and small-to-big tables (D-022); agent depth handled by built-in tables.
- Riya asked to run the test set on Sonnet high to see if errors are resolved. Claude ran **dev first**: the errors to check were found on dev, and the test set must be run only once, on the final system, so it stays an honest score. Test next if dev is clean.
- Dev result (run `2026-10-27_1854`): 25/27, 0 serious errors (stage 1: 23/27, 2 serious); cost per answer ~2×. Dev was clean enough → test set started.
- Test set (run `2026-10-27_1911`): 15/19 strict, 0 serious; 1 broken output (#53, tool calls written as text) → output guard proposed.

### 2026-10-28
- Riya: no output guard for now; answers are good and broken replies are rare (1/140). → Deferred to the UI phase.
- Riya: keep the full table budget (accuracy over plan usage). Asked how to enhance search. Claude proposed, cheapest first: (A) score search on the agent's own logged queries, (B) a larger/finance embedding model, (C) a glossary of standard 10-K terms + keyword search on the expanded terms (must not come from eval misses), (D) a prompt nudge to retry with filing terms, (E) LLM plain-English labels per passage (~$1 via API, the only paid one). Recommended A→B→C, then a dev answer eval; E in reserve. Awaiting Riya.
- Riya: options must scale to ~100 companies with no manual upkeep → **glossary (C) dropped**. Revised plan (proposed): (A) score search on the agent's logged queries; (B) larger/finance embedding model; (D) automatic "weak match" signal from `search_filings` so the agent re-searches in filing terms only when needed; (E) Haiku plain-English labels per passage at index time (~6¢/filing via API, ~3¢ batch; ≈$1 now, ≈$20 for 300 filings; needs an API key; Riya's budget call). **Scaling flag:** all-company questions would need ~100 searches at 100 companies → roadmap: a key-figures table built automatically from Docling's financial-statement tables (text-to-SQL). Awaiting Riya on A→B→D.
- Riya: is enhancing search worth it? Claude: not now. 0 wrong facts in 46 answers; only ~1–2 of 46 problems involve search (#25). Agreed order: (1) wording-overreach fix, (2) completeness on "why" questions, (3) UI. Search options A–E parked (scalable ones only; glossary dropped).
- (1) Wording rules added to `prompts.py`: the opening sentences may only summarise cited bullets; no records/superlatives unless the filing says so; report risks the way the filing frames them, no own verdicts; describe absences as "I found no mention… in the filings", not as facts about the company. Examples deliberately not taken from eval questions. Note: the pattern was seen partly on **test** flags, so later test scores are slightly optimistic. Running dev (27) + extra (10) on Sonnet high (`eval/runs/stage3_wording_dev_extra.log`).

### 2026-10-29 — UI built (in parallel with the wording eval)
- Riya: local web app, Courier Prime, scrolling thread + New conversation, thinking verbs; asked whether indexed tables reach the output → citations open the page's tables (D-023).
- Built and tested `uv run indexit app`. Observation from the live Tesla answer: "What this might mean" introduced a number not in the bullets (car sales −9%, $72.5B → $65.8B), against the no-new-numbers rule. Track in the wording eval.
- Wording eval done: dev 24/27 (was 25/27), extra 10/10. Flags moved to different questions (#6 period, #22 overreach, #35 relationship direction): no measurable effect, within noise. Rules kept (no cost to coverage/format). Remaining error rate ≈1 in 10 answers, mixed causes → the next lever would be a verification pass (answer drafted, checked against sources, then shown), not more prompt rules. Details: `eval/model_comparison.md` stage 3.
- UI revisions (Riya): green accent, arrow send button, New conversation far right, saved conversations with History + session resume (D-023).
- Riya: two-column app (1/3 conversations + library, 2/3 conversation), fixed-height scrolling sections, add filings by upload or SEC fetch (company + year), card always, searchable before tables, everything in a folder; SEC contact entered in the app without Claude seeing it. Built and tested (D-024). SEC fetch pending Riya's contact email.
- Add-filing modal revised: company + year only for SEC fetch; bulk PDF upload with per-file cards + Add all. Fixed a duplicated-modal HTML bug from an earlier edit (cards rendered into a hidden copy). Tagline: "The fine print, made simple." (Riya); filing count moved under Library; Open · Delete on one line; page assets versioned + no-store so reloads always show changes.
- Riya fetched Walmart FY2025 from the SEC (works end to end); fixed the garbled company name from printed web covers; SEC/library names now preferred.
- Riya: indexing status as a pulsing hollow circle ○ "Indexing" → "✓ Done" (shown 1 min), no page counts (detail in a tooltip); after "Add to library", an "Added to your library" modal lists what was added + "It'll take about N minutes to IndexIt!" (estimate: 20 s per filing + 1 s per page for everything queued, from the 94-page measurement), closes itself after 10 s with a countdown bar.
- **Scope rule (Riya, 2026-10-29):** IndexIt had answered a UI bug note typed into it by guessing and offering options. New `SCOPE` block in both system prompts: in scope = the library's companies and 10-Ks, incl. explaining financial terms / where to find things (with a library example); anything else → only "IndexIt answers questions about the annual reports (10-Ks) in your library: <companies>. Ask about one of them." (no search, no guesses, no headings/follow-ups); a company not in the library → one sentence + "+ Add filing". Tested on 4 messages: out-of-scope replies in 3-5 s with 0 searches; the jargon question still gets a full cited answer. Unanswerable eval questions (#20/21/56) are about library companies, so unaffected; covered by the next dev eval.
- **Public repo prep (Riya: portfolio, public GitHub repo with guardrails):** `git init` (branch main, not yet committed or pushed); commit identity uses GitHub's private noreply address; `.gitignore` excludes `data/` (settings, conversations, filings, index), PDFs, logs, `.venv`; **pre-commit privacy check** (`scripts/check_private.py`, hook in `.githooks/`, enabled via `core.hooksPath`) blocks data/, PDFs, files >5 MB, email addresses (except no-reply), home-folder paths and API keys/tokens, printing findings masked. Proven on a planted test file. `--all` scan of the 60 publishable files (2 MB): clean. Riya: **removed the names of her connected apps entirely** (PROJECT.md, agent.py). Added a **private blocklist**: `.private-terms` (never committed, chmod 600) lists personal words the check refuses to publish; proven on a planted line. Pending: README, license, first commit, GitHub sign-in + push (her step).
- License (Riya): **none for now**. Public to read, all rights reserved (README states it). README drafted for the public repo.
- **First commit** `21cd404` (local only, 61 files; privacy check passed; author Riya Subhedar with the GitHub noreply address). Next: Riya's GitHub settings + empty `indexit` repo + sign-in on this Mac, then push on her go-ahead.
- **Published 2026-10-29:** https://github.com/riyasubhedar/indexit (public, all rights reserved). Commit re-authored to Riya's numbered GitHub noreply address before pushing. GitHub CLI 2.103.3 installed in `~/.local/bin` (checksum verified); Riya signed in via browser device code; key in the macOS keychain; `gh auth setup-git` connects git to it. Verified on GitHub: 61 files, nothing from data/ or PDFs.
- **Portfolio case study** for IndexIt built in the separate site repo `~/Documents/riyasubhedar.github.io` (local, not yet published): home + `projects/indexit/` case study, screenshots from the live app (light mode, 2x), same privacy guardrails.
- **2026-10-30, D-025 (Riya):** multimodal build dropped; the learning is that evidence showed 10-Ks don't need it. Updated CLAUDE.md, README, LEARNING.md (new section), and the portfolio site's Now section and case study.
- **2026-10-30: IndexIt declared complete (Riya: "happy with the current state").** The verification pass (draft checked claim by claim against its sources before display; est. +10 s and 1.5–2× plan usage per answer) is not planned; parked with the key-figures table and the search options. Portfolio: "Now" reads "IndexIt is complete. I'm choosing the next problem worth building for."; case study section 08 is now "If I took it further".
- **2026-10-30:** Captured how this project was run as a personal Claude Code skill, `riya-project-playbook` (project docs, eval-first practice, publishing guardrails, portfolio site), for use in every future project.
- **2026-11-01, D-026 (Riya): key-figures table.** Rules read every filing's income statement and balance sheet (`figures.py`); 251/254 figures match SEC XBRL exactly, 0 differ (`spikes/check_figures_xbrl.py`). New MCP tool `compare_companies`; prompt tells the agent to use it for rankings and search for the rest. Eval set: library grew to 10 companies → #52/#53 keys updated, #56 rewritten (no longer unanswerable), #57–59 added. Cross-company eval 8/9 (one flag from missing units in tool output, fixed); #52 7 searches → 2 calls, 25 → 14 s. **Compare view** in the app (Riya: *+ Add · Compare* in the Library; rule-based insights + *Ask IndexIt why*), checked in light, dark and phone screenshots. Portfolio: "key-figures table" removed from the case study's "If I took it further".
- **2026-11-01 (later):** Riya asked for industry comparisons; Claude's critique: right lens, but most industries in a 10-company library have 1–2 members, labels are slippery (Amazon: retail or cloud?) and "correlation" is noise at this size. **Riya: groups later, 1:1 now.** Built **Side by side** (two companies, every figure, sources, differences, pair insights); banks also excluded from total assets. Checked in light/dark/phone screenshots (NVIDIA vs AMD, Walmart vs Amazon).
