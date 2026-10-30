"""Command line entry point.

  uv run indexit index data/filings       # build/refresh the index (free, local)
  uv run indexit filings                  # list filings with company / fiscal year (free, local)
  uv run indexit search "question"        # show retrieved passages only (free, local)
  uv run indexit ask "question"           # one search + answer with the Claude API (paid, API key)
  uv run indexit ask-agent "question"     # Claude Code researches via the MCP tools (Pro subscription)
  uv run indexit app                      # the IndexIt web page on this Mac (http://127.0.0.1:8765)
"""

import argparse
import asyncio
import sys
from pathlib import Path

from indexit.documents import describe
from indexit.embedder import Embedder
from indexit import clean_pipeline, docling_pipeline, simple_pipeline
from indexit.search import retrieve
from indexit.store import ChunkStore, file_hash

# Index versions: pipeline name -> (chunking function, LanceDB table). Kept side by side for comparisons.
PIPELINES = {
    "simple": (simple_pipeline.chunk_pdf, "simple_v1"),
    "clean": (clean_pipeline.chunk_pdf, "clean_v2"),
    "docling": (docling_pipeline.chunk_pdf, "docling_v3"),  # clean text + structured tables (D-022)
}


def store_chunks(store: ChunkStore, embedder: Embedder, pdf: Path, chunks: list, digest: str) -> None:
    """Embed a filing's passages and replace its rows in the index."""
    vectors = embedder.embed_passages([c.embed_text or c.text for c in chunks])
    rows = [
        {"id": c.id, "doc": c.doc, "doc_hash": digest, "page": c.page, "text": c.text, "context": c.context,
         "kind": c.kind, "vector": v}
        for c, v in zip(chunks, vectors)
    ]
    store.replace_doc(pdf.name, rows)


def index_folder(folder: Path, pipeline: str, rebuild: bool = False) -> None:
    chunk_pdf, table = PIPELINES[pipeline]
    store, embedder = ChunkStore(table), Embedder()
    if rebuild:  # re-chunk every file, e.g. after changing the pipeline code (unchanged PDFs are skipped otherwise)
        store.drop()
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDFs found in {folder}")
    indexed = store.indexed_hashes()
    for pdf in pdfs:
        digest = file_hash(pdf)
        if indexed.get(pdf.name) == digest:
            print(f"✓ unchanged, skipping: {pdf.name}")
            continue
        filing = describe(pdf)
        if pipeline == "docling":
            print(f"→ extracting tables with Docling: {filing.label} ({filing.pages} pages)…", flush=True)
            chunks = chunk_pdf(pdf, progress=lambda done, total, n: print(f"   p{done}/{total}: {n} tables", flush=True))
        else:
            chunks = chunk_pdf(pdf)
        print(f"→ indexing {filing.label} ({pdf.name}): {len(chunks)} passages")
        if filing.company == pdf.stem or not filing.fiscal_year:
            print(f"  ⚠️  couldn't read company/fiscal year from the cover page; citations will show the file name")
        store_chunks(store, embedder, pdf, chunks, digest)
    for doc in store.remove_docs_not_in({p.name for p in pdfs}):
        print(f"✗ removed (no longer in folder): {doc}")
    store.build_keyword_index()  # for hybrid (keyword + meaning) search


def ask_agent(question: str, model: str | None, effort: str | None, once: bool) -> None:
    from indexit.agent import AgentSession, dig_deeper_questions

    def show_call(seconds, tool, tool_input):
        detail = tool_input.get("query") or f"{tool_input.get('file', '')[:40]} p.{tool_input.get('page', '')}"
        print(f"  [{seconds:5.1f}s] {tool}: {detail}", flush=True)

    def show_text(text):
        print(text, end="", flush=True)

    async def conversation():
        nonlocal question
        async with AgentSession(model, effort) as session:
            while True:
                print(f"\n❓ {question}\nResearching…", flush=True)
                run = await session.ask(question, on_text=show_text, on_tool_call=show_call)
                first = f"first words at {run.first_text_seconds:.0f}s · " if run.first_text_seconds else ""
                print(f"\n\n[{first}{run.seconds:.0f}s total · {len(run.tool_calls)} tool calls", end="")
                if run.api_equivalent_usd is not None:
                    print(f" · ≈${run.api_equivalent_usd:.2f} if billed via API (covered by subscription)", end="")
                print("]")
                if run.error:
                    print(f"[ended with: {run.error}]")
                options = dig_deeper_questions(run.answer)
                if once or not options:
                    return
                try:
                    choice = (await asyncio.to_thread(input, f"\nDig deeper? Pick 1-{len(options)}, or Enter to finish: ")).strip()
                except EOFError:
                    return
                if not (choice.isdigit() and 1 <= int(choice) <= len(options)):
                    return
                question = options[int(choice) - 1]

    asyncio.run(conversation())


def main() -> None:
    parser = argparse.ArgumentParser(prog="indexit")
    commands = parser.add_subparsers(dest="command", required=True)
    index_parser = commands.add_parser("index")
    index_parser.add_argument("folder", type=Path)
    index_parser.add_argument("--pipeline", choices=PIPELINES, default="clean", help="chunking version (default: clean; docling = + tables)")
    index_parser.add_argument("--rebuild", action="store_true", help="re-index every file (after changing chunking code)")
    commands.add_parser("filings")
    commands.add_parser("search").add_argument("question")
    commands.add_parser("ask").add_argument("question")
    agent_parser = commands.add_parser("ask-agent")
    agent_parser.add_argument("question")
    agent_parser.add_argument("--model", help="Claude model alias: opus, sonnet or haiku (default: account default)")
    agent_parser.add_argument("--effort", choices=["low", "medium", "high"], help="thinking depth (lower = faster)")
    agent_parser.add_argument("--once", action="store_true", help="answer once; don't offer dig-deeper questions")
    eval_parser = commands.add_parser("eval", help="run golden questions through agent configs and fact-check them")
    eval_parser.add_argument("--configs", help='comma-separated, e.g. "opus:low,sonnet,haiku" (default: sonnet; with --recheck: all)')
    eval_parser.add_argument("--questions", help='question ids, e.g. "1-5,22" (default: all in the set)')
    eval_parser.add_argument("--set", default="dev", help='dev, test, extra, all, or e.g. "dev,test" (default: dev)')
    eval_parser.add_argument("--resume", help='continue an interrupted run: its folder in eval/runs, or "latest"')
    eval_parser.add_argument("--recheck", help='with --resume: re-run only the fact-check for these question ids, e.g. "52"')
    commands.add_parser("eval-summary", help="rebuild a run's summary.md from its records").add_argument(
        "run", nargs="?", default="latest", help='run folder in eval/runs, or "latest" (default)'
    )
    app_parser = commands.add_parser("app", help="open the IndexIt web page (local only)")
    app_parser.add_argument("--port", type=int, default=8765)
    app_parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    search_eval_parser = commands.add_parser("eval-search", help="free, search-only eval (no LLM)")
    search_eval_parser.add_argument("--tables", help='index versions to compare, e.g. "simple_v1,clean_v2"')
    search_eval_parser.add_argument("--set", default="dev", help="question set (default: dev; search is tuned on dev only)")
    args = parser.parse_args()

    if args.command == "index":
        index_folder(args.folder, args.pipeline, args.rebuild)
    elif args.command == "filings":
        from indexit.documents import list_filings

        for f in list_filings():
            print(f"{f.label:<36} fiscal year ended {f.period_end}  {f.pages:>3} pages  {f.file}")
    elif args.command == "search":
        for rank, hit in enumerate(retrieve(args.question), 1):
            print(f"\n#{rank}  {hit['doc'][:50]}  p.{hit['page']}  (distance {hit['_distance']:.3f})")
            print(f"   {hit['text'][:300]}…")
    elif args.command == "ask":
        from indexit.llm import ClaudeBrain

        answer = ClaudeBrain().answer(args.question, retrieve(args.question))
        print(answer.text)
        print(f"\n[tokens: {answer.input_tokens} in / {answer.output_tokens} out]")
    elif args.command == "ask-agent":
        ask_agent(args.question, args.model, args.effort, args.once)
    elif args.command == "eval":
        from indexit.evaluate import run_eval

        if args.recheck:
            from indexit.evaluate import parse_ids, recheck

            ids = parse_ids(args.recheck, list(range(1, 10_000)))
            asyncio.run(recheck(args.resume or "latest", ids, args.configs.split(",") if args.configs else None))
        else:
            asyncio.run(run_eval((args.configs or "sonnet").split(","), args.questions, args.set, args.resume))
    elif args.command == "eval-summary":
        from indexit.evaluate import summarize

        print(summarize(args.run))
    elif args.command == "app":
        from indexit.web.app import serve

        serve(args.port, open_browser=not args.no_browser)
    elif args.command == "eval-search":
        from indexit.evaluate import search_eval

        print(search_eval(tables=args.tables.split(",") if args.tables else None, subset=args.set))
