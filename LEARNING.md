# IndexIt — Learning Notes

Plain-English explanations of the concepts we use, added as we go.

---

## RAG (Retrieval-Augmented Generation)

An LLM doesn't know what's in *your* PDFs, and you can't paste 2,000 pages into every question. RAG works like an open-book exam:
1. **Index** (once): split documents into small pieces ("chunks") and store them in a searchable index.
2. **Retrieve** (each question): find the handful of chunks most relevant to the question.
3. **Generate**: give the LLM the question + those chunks and tell it to answer only from them, with citations.

**Embedding:** a list of numbers that represents the *meaning* of a piece of text. Texts with similar meanings get similar numbers, so "profit" can match "net income" even though the words differ. A **vector database** stores these lists and finds the closest matches quickly.

---

## Types of RAG (simplest → most advanced)

| Type | What it adds | Fixes what problem | 10-K example |
|---|---|---|---|
| **1. Simple (naive) RAG** | Text chunks → embeddings → top matches → LLM | The basics | "What does the company do?" → finds the Item 1 Business text |
| **2. Hybrid search** | Keyword search (BM25) alongside meaning search | Embeddings are fuzzy on exact terms, tickers, years and numbers | "FY2023 diluted EPS" needs exact matching |
| **3. Better chunking + metadata** | Split along the document's own structure (sections, whole tables); tag each chunk with company, year, section, page | Chunks cut tables in half; can't tell which company or year a chunk is from | Keeps the Income Statement table whole and labelled "Apple · FY2024 · Item 8 · p.28" |
| **4. Contextual retrieval** | Prepend a one-line summary of where the chunk sits in the document | A chunk saying "revenue grew 8%" doesn't say *whose* revenue | "From Apple's FY2024 10-K, MD&A, Services segment: revenue grew 8%" |
| **5. Reranking** | A second, more careful model re-orders the top ~30 matches | The first search is fast but rough | Pushes the actual table above prose that merely mentions it |
| **6. Multimodal RAG** | Handles **tables and images**, not just running text (see below) | Simple RAG mangles tables and can't see charts | "How did gross margin trend over 3 years?" answered from the table or chart |
| **7. Structured / Text-to-SQL** | Tables loaded into a real database; the LLM writes queries | LLMs are unreliable at arithmetic across many numbers | "Average R&D spend as % of revenue over 3 years" |
| **8. Agentic RAG** | The LLM plans and runs *several* searches, reasoning between them | One search can't answer broad or multi-part questions | "Is this company healthy?" → looks up revenue trend, margins, debt and cash flow, then synthesizes |
| *(Graph RAG)* | Builds a knowledge graph of entities and relationships | Questions about relationships across many docs | "Which of these companies share suppliers?" (probably not needed for us) |

These aren't exclusive. Real systems **stack** several of them. Our plan: start at 1, measure, add layers.

---

## What is multimodal RAG, and why not simple RAG?

"Multimodal" = more than one kind of input: **text + tables + images (charts, page layouts)**.

**Why simple RAG fails on financial filings:** a PDF text extractor reads left to right and flattens a table like this:

```
                      2024      2023      2022
Net sales          391,035   383,285   394,328
Cost of sales      210,352   214,137   223,546
Gross margin       180,683   169,148   170,782
```

into a stream like: `Net sales 391,035 383,285 394,328 Cost of sales 210,352 ...`. Then the chunker may split it mid-table, so the **year headers end up in a different chunk from the numbers**. The LLM sees numbers without knowing which year they belong to. It guesses, or it gives up. Charts are worse: to a text extractor they're invisible.

**Three ways to do multimodal RAG:**

| Approach | How | Good at | Weak at |
|---|---|---|---|
| **A. Convert everything to text** | Tables → structured text (Markdown/HTML, headers kept); charts → an LLM writes a description at index time | Cheap to query, works with normal text search | Descriptions can miss detail; anything they omit is lost |
| **B. Search page images directly** (ColPali-style) | Turn each *page image* into embeddings and search pages visually | Layout-heavy, chart-heavy pages | Exact keyword/number search; heavier storage |
| **C. Hybrid** (our plan) | Search with A (text + structured tables + descriptions), then send the **actual page images** of the top hits to a vision LLM at answer time | Precise search *and* the LLM "sees" the real table or chart, which helps it check the numbers | More parts to build; images cost more tokens per question |

---

## How do tables and charts get into a text-based index?

**Key idea: what you search on and what you hand to the AI can be different things.** Like a library catalog card vs. the book itself:
- **Search representation** (the catalog card): text written to match how people phrase questions. This is what gets embedded and keyword-indexed.
- **Answer representation** (the book): the real content (full table, page image) attached to the same record, which goes to the AI once the record is found.

Every chunk in the index is one record:

```
id:            apple-fy24-p28-t1
type:          table                      # text | table | chart
company:       Apple   fiscal_year: 2024   section: Item 8   page: 28
search_text:   "Apple FY2024 Consolidated Statements of Operations (income statement).
                Rows: Net sales, Cost of sales, Gross margin, R&D, Operating income,
                Net income, EPS. Years: 2024, 2023, 2022."
content:       | Line item | 2024 | 2023 | 2022 |      ← the whole table as Markdown
               | Net sales | 391,035 | 383,285 | 394,328 | ...
image_path:    pages/apple-fy24/p28.png           ← used by the multimodal layer
embedding:     [0.012, -0.84, ...]                ← computed from search_text
```

**Why a separate search_text for tables?** Embeddings capture *meaning*, and a grid of numbers has little meaning to embed. A question like "How profitable was Apple?" matches the words "income statement, net income, operating income", not "391,035". So we embed the table's title, row and column labels, and a one-line summary, and keep the numbers in `content`.

**How each layer handles each kind of content:**

| Content | Smart chunking (no vision) | + Multimodal layer |
|---|---|---|
| Prose | Split by section; search_text = content | Same |
| Table | Parser rebuilds it as Markdown. search_text = title + labels + summary. Big tables split by row groups, **with headers repeated in every piece** | Also store the page image and send it with the table, so the AI can catch extraction errors |
| Chart | ❌ Only its caption and nearby text are searchable; the chart's data is lost | At indexing, a vision AI **writes a text description** of the chart ("line chart, 5-yr cumulative return, Apple $100→$310 vs S&P $100→$190"), which becomes search_text. Page image stored for answering |

**At question time:** search the `search_text` (meaning + keywords, filtered by company/year) → pick the top records → send their `content` (+ `image_path` images, if multimodal) to Claude → answer with page citations.

*Side note:* image embeddings exist too (e.g. CLIP, ColPali), so you can search images directly without converting them to text first. That's approach B above, and we're not starting there.

---

---

**For 10-Ks specifically:** most of the value is in **tables** (financial statements, segment data) and prose (risk factors, MD&A). Charts are rarer. So structured table extraction (type 3 + approach A) will probably give the biggest win, and page images (approach C) act as a safety net. The baseline-first plan will show us whether that's true.

---

## Claude API vs. Ollama, and why RAM matters

Both fill the **same slot** in the pipeline, the "brain" LLM that reads retrieved chunks and writes the answer. They differ in **where the model runs**:
- **Claude API:** the model runs on Anthropic's data-center hardware. We send text over the internet and pay per token. No hardware limits on our side.
- **Ollama:** free software that downloads *open-weight* models (Llama, Qwen, Gemma…) and runs them **on your Mac**. Free per use and offline, but limited by your hardware.

**Why 8 GB RAM is a constraint:** a model *is* billions of numbers (parameters), and all of them must sit in memory while it runs.
- Compressed ("4-bit quantized"), each parameter takes about 0.5 bytes → a 3B model ≈ 2 GB, a 7–8B model ≈ 4–5 GB, a 70B model ≈ 40 GB.
- macOS + apps already use about 3–4 GB of the 8, and long prompts (our ~10K tokens of tables) need extra working memory.
- So **3–4B models are the realistic ceiling**; 7–8B models only squeeze in with swapping to disk, which is very slow. Frontier models like Claude are far larger and run on data-center GPUs.
- Small models are noticeably worse at what we need most: reasoning across table numbers, following "cite the page" rules, and saying "not in the documents" instead of guessing.

**Not every model is big:** the *embedding* model (D-004) is small (~100–500 MB), so it runs locally without trouble. The memory issue only affects the brain.

---

## MCP (Model Context Protocol)

A standard "plug" that lets AI apps (Claude Code, Claude Desktop and others) use outside tools and data. You write a small **MCP server** that advertises tools (name + description + inputs). The AI app decides when to call them, and reads the results.

For IndexIt, an MCP server would expose **search only**. The AI app connected to it becomes the brain. That flips who's in charge:
- **IndexIt app:** *our code* decides what to search (once) and which model answers, with our prompt.
- **MCP:** *the AI* decides what to search, how many times, and how to answer. That makes it agentic RAG (type 8 above) with no extra code, but we give up control over model, prompt and format.

---

## Overfitting, and dev vs. test sets

**Overfitting** = getting good at *your test* instead of at *the real job*. If we keep tweaking prompts until our 25 questions pass, IndexIt may just have learned the quirks of NVIDIA and AMD filings, and of questions written by someone who had already read them.

The standard fix is to split the questions:
- **Dev set**: questions we look at, debug and tune on freely.
- **Test set**: questions we **never tune on**, run only when making a decision. It's the "real exam".

If dev scores go up but test scores don't, we're overfitting. A bigger, more varied set of filings helps for the same reason: it makes the problem closer to real life (more companies means harder "which filing?" searches, and more fiscal-year calendars).
