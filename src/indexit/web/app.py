"""IndexIt web app (D-023): a local, single-user page over the Claude Code agent.

  uv run indexit app              # opens http://127.0.0.1:8765

Listens on 127.0.0.1 only, so nothing outside this Mac can reach it. Answers stream to the page as
newline-delimited JSON events: "conversation" (which saved conversation this belongs to), "step" (a
search or page read, for the research trail), "text" (answer words as they're written), "done" (the
final answer + stats) or "error".

Conversations are saved in data/conversations/<id>.json. Going back to one resumes its Claude Code
session, so Claude remembers it; if that session is gone, Claude gets a recap of the earlier Q&A instead.
"""

import asyncio
import json
import math
import re
import secrets
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pymupdf
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from indexit import library
from indexit.agent import AgentRun, AgentSession, dig_deeper_questions
from indexit.documents import FILINGS_DIR, PROJECT_DIR, aliases_for, describe, format_filings, list_filings
from indexit import figures
from indexit.tables import page_tables

MODEL, EFFORT = "sonnet", "high"  # D-021
STATIC = Path(__file__).parent / "static"
CONVERSATIONS_DIR = PROJECT_DIR / "data" / "conversations"
SECONDS_PER_PAGE, SECONDS_PER_FILING = 1.0, 20  # measured 2026-10-29: a 94-page 10-K was ready in ~1 min 50 s
RECAP_EXCHANGES = 5  # how many earlier Q&As Claude gets when a conversation's session can't be resumed
_NEW = object()


# ---------- Saved conversations ----------

def _new_id() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"


def _conversation_path(conversation_id: str) -> Path | None:
    if not re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", conversation_id or ""):  # never a path from outside
        return None
    return CONVERSATIONS_DIR / f"{conversation_id}.json"


def load_conversation(conversation_id: str) -> dict | None:
    path = _conversation_path(conversation_id)
    return json.loads(path.read_text()) if path and path.exists() else None


def save_conversation(conversation: dict) -> None:
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    conversation["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _conversation_path(conversation["id"]).write_text(json.dumps(conversation, indent=1))


def list_conversations() -> list[dict]:
    items = []
    for path in CONVERSATIONS_DIR.glob("*.json"):
        c = json.loads(path.read_text())
        items.append({"id": c["id"], "title": c["title"], "updated": c["updated"], "questions": len(c["exchanges"])})
    return sorted(items, key=lambda c: c["updated"], reverse=True)


def _recap(conversation: dict) -> str:
    earlier = conversation["exchanges"][-RECAP_EXCHANGES:]
    lines = [f"Q: {e['question']}\nA: {e['answer'][:1500]}" for e in earlier]
    return ("Earlier in this conversation (context only; the filings are still your only source of facts):\n\n"
            + "\n\n".join(lines) + "\n\nNew question:")


# ---------- The Claude Code session ----------

class Conversations:
    """Owns the one Claude Code session in a single worker task (the SDK client must stay in the task that
    opened it). Questions queue up and run one at a time. A fresh session is kept open for the next new
    conversation, so its first question doesn't wait for start-up; going back to a saved conversation
    reopens (resumes) that conversation's session."""

    def __init__(self) -> None:
        self._jobs: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()

    def ask(self, conversation_id: str | None, question: str) -> asyncio.Queue:
        events: asyncio.Queue = asyncio.Queue()
        self._jobs.put_nowait((conversation_id, question, events))
        return events

    def new(self) -> None:
        self._jobs.put_nowait(_NEW)

    async def _run(self) -> None:
        session, owner = await self._try_open(), None  # owner: the conversation the open session belongs to
        try:
            while True:
                job = await self._jobs.get()
                if job is _NEW:
                    if owner is not None or session is None:
                        await self._close(session)
                        session, owner = await self._try_open(), None
                    continue
                conversation_id, question, events = job
                conversation, resumed = None, False
                try:
                    conversation = load_conversation(conversation_id) or {
                        "id": _new_id(), "title": question[:80], "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "claude_session_id": None, "exchanges": [],
                    }
                    events.put_nowait({"type": "conversation", "id": conversation["id"]})
                    prompt = question
                    if owner != conversation["id"]:
                        if not (owner is None and session and not conversation["exchanges"]):  # else: use the fresh one
                            await self._close(session)
                            session = None
                            if conversation["exchanges"] and conversation["claude_session_id"]:
                                session = await self._try_open(conversation["claude_session_id"])
                                resumed = session is not None
                            if session is None:
                                session = await self._open()
                                if conversation["exchanges"]:
                                    prompt = f"{_recap(conversation)}\n{question}"
                        owner = conversation["id"]
                    filings_now = format_filings()
                    if session.filings != filings_now:  # filings added or removed since this session started
                        prompt = f"(The filings library changed. Filings available now:\n{filings_now})\n\n{prompt}"
                        session.filings = filings_now
                    run, steps = await self._answer(session, prompt, events)
                    if run.answer and not run.error:
                        self._save(conversation, question, run, steps)
                    elif resumed and run.error != "plan_limit":  # that saved session can't be resumed:
                        conversation["claude_session_id"] = None  # use a recap next time
                        save_conversation(conversation)
                        await self._close(session)
                        session, owner = None, None
                except Exception as error:  # a broken session is replaced on the next question
                    events.put_nowait({"type": "error", "message": f"Something went wrong: {error}"})
                    if resumed:  # that saved session can't be resumed: use a recap next time
                        conversation["claude_session_id"] = None
                        save_conversation(conversation)
                    await self._close(session)
                    session, owner = None, None
                finally:
                    events.put_nowait(None)
        finally:
            await self._close(session)

    async def _answer(self, session: AgentSession, prompt: str, events: asyncio.Queue) -> tuple[AgentRun, list[str]]:
        labels = {f.file: f.label for f in list_filings()}
        steps: list[str] = []

        def on_tool_call(t, tool, args):
            steps.append(_describe(tool, args, labels))
            events.put_nowait({"type": "step", "text": steps[-1]})

        run = await session.ask(
            prompt,
            on_text=lambda text: events.put_nowait({"type": "text", "text": text}),
            on_tool_call=on_tool_call,
        )
        if run.error == "plan_limit":
            events.put_nowait({"type": "error", "message": run.answer})
            return run, steps
        if run.error or not run.answer:
            events.put_nowait({"type": "error", "message": "Claude didn't return an answer. Please ask again."})
            return run, steps
        tools = [tool for _, tool, _ in run.tool_calls]
        events.put_nowait({
            "type": "done",
            "answer": run.answer,
            "dig_deeper": dig_deeper_questions(run.answer),
            "seconds": round(run.seconds, 1),
            "searches": tools.count("search_filings"),
            "pages_read": tools.count("read_page"),
        })
        return run, steps

    @staticmethod
    def _save(conversation: dict, question: str, run: AgentRun, steps: list[str]) -> None:
        tools = [tool for _, tool, _ in run.tool_calls]
        conversation["exchanges"].append({
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "question": question, "answer": run.answer,
            "steps": steps, "seconds": round(run.seconds, 1),
            "searches": tools.count("search_filings"), "pages_read": tools.count("read_page"),
            "tool_calls": [{"t": round(t, 1), "tool": tool, "input": args} for t, tool, args in run.tool_calls],
            "models": run.models, "api_equivalent_usd": run.api_equivalent_usd,
        })
        conversation["claude_session_id"] = run.session_id or conversation["claude_session_id"]
        save_conversation(conversation)

    @staticmethod
    async def _open(resume: str | None = None) -> AgentSession:
        session = AgentSession(MODEL, EFFORT, resume=resume)
        session.filings = format_filings()  # the list its system prompt was given
        await session.__aenter__()
        return session

    async def _try_open(self, resume: str | None = None) -> AgentSession | None:
        try:
            return await self._open(resume)
        except Exception:
            return None

    @staticmethod
    async def _close(session: AgentSession | None) -> None:
        if session:
            try:
                await session.__aexit__(None, None, None)
            except Exception:
                pass


def _describe(tool: str, args: dict, labels: dict[str, str]) -> str:
    """A research step in plain words, e.g. 'Searching Apple filings for "net sales by category"'."""
    if tool == "search_filings":
        where = f"{args['company']} filings" if args.get("company") else "the filings"
        return f'Searching {where} for "{args.get("query", "")}"'
    if tool == "read_page":
        return f"Reading {labels.get(args.get('file'), args.get('file'))}, p.{args.get('page')}"
    if tool == "list_filings":
        return "Checking which filings are available"
    if tool == "compare_companies":
        metric = {"rd": "R&D", "rd_to_revenue": "R&D as a share of revenue"}.get(
            args.get("metric"), str(args.get("metric", "")).replace("_", " "))
        year = f" for FY{args['fiscal_year']}" if args.get("fiscal_year") else ""
        return f"Comparing {metric} across companies{year}"
    return f"Using {tool}"


conversations = Conversations()


class Indexer:
    """Indexes confirmed filings one at a time, each in its own process (Docling's memory is released when it
    ends). Progress goes into the library file, which the page polls. Unfinished work resumes on start-up."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        for name in library.unfinished():
            self._queue.put_nowait(name)
        self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()

    def add(self, name: str) -> None:
        self._queue.put_nowait(name)

    async def _run(self) -> None:
        while True:
            name = await self._queue.get()
            entry = library.active_filings().get(name)
            if entry is None:
                continue
            if entry["status"] not in ("searchable", "ready"):
                library.update(name, status="indexing", progress="Indexing the text")
            library.update(name, tables="running")
            log = (PROJECT_DIR / "data" / "indexing.log").open("a")
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "indexit.library", "index", name,
                stdout=asyncio.subprocess.PIPE, stderr=log, cwd=PROJECT_DIR,
            )
            async for line in process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue  # library output that isn't ours
                if event.get("stage") == "searchable":
                    library.update(name, status="searchable", progress="Extracting tables")
                elif event.get("stage") == "tables":
                    library.update(name, progress=f"Extracting tables: p.{event['done']} of {event['total']}")
            code = await process.wait()
            log.close()
            if code == 0:
                library.update(name, status="ready", tables="done", progress="")
            elif library.active_filings().get(name, {}).get("status") == "searchable":
                library.update(name, tables="failed", progress="Tables failed; text is searchable")
            else:
                library.update(name, status="failed", tables="failed", progress="Indexing failed")


indexer = Indexer()


# ---------- Routes ----------

async def index(request: Request) -> HTMLResponse:
    """The page, with its CSS/JS links stamped with their last-change time, so a normal reload always picks
    up new versions (browsers otherwise keep serving old copies from their cache)."""
    html = (STATIC / "index.html").read_text()
    for asset in ("app.css", "app.js"):
        html = html.replace(f"/static/{asset}", f"/static/{asset}?v={int((STATIC / asset).stat().st_mtime)}")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


async def filings(request: Request) -> JSONResponse:
    return JSONResponse({
        "folder": str(FILINGS_DIR),
        "filings": [
            {"file": f.file, "label": f.label, "company": f.company, "fiscal_year": f.fiscal_year,
             "period_end": f.period_end, "pages": f.pages, "aliases": aliases_for(f.company)}
            for f in list_filings()
        ],
    })


async def ask(request: Request) -> StreamingResponse:
    body = await request.json()
    question = str(body.get("question", "")).strip()[:2000]
    if not question:
        return JSONResponse({"error": "Empty question"}, status_code=400)
    events = conversations.ask(body.get("conversation_id"), question)

    async def stream():
        while (event := await events.get()) is not None:
            yield json.dumps(event) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


async def new_conversation(request: Request) -> JSONResponse:
    conversations.new()
    return JSONResponse({"ok": True})


async def conversation_list(request: Request) -> JSONResponse:
    return JSONResponse({"conversations": list_conversations()})


async def conversation(request: Request) -> JSONResponse:
    saved = load_conversation(request.path_params["id"])
    if saved is None:
        return JSONResponse({"error": "Unknown conversation"}, status_code=404)
    return JSONResponse(saved)


async def library_state(request: Request) -> JSONResponse:
    """The library for the sidebar: companies -> filings with status, plus files waiting for confirmation."""
    library.pick_up_dropped_files()
    companies: dict[str, list] = {}
    for name, e in library.active_filings().items():
        path = FILINGS_DIR / name
        companies.setdefault(e["company"], []).append({
            "file": name, "label": f"{e['company']} FY{e['fiscal_year']} 10-K", "fiscal_year": e["fiscal_year"],
            "period_end": e.get("period_end"), "pages": describe(path).pages if path.exists() else None,
            "status": e["status"], "tables": e.get("tables"), "progress": e.get("progress", ""),
            "source": e.get("source"), "added": e.get("added"),
        })
    return JSONResponse({
        "companies": [{"company": c, "filings": sorted(f, key=lambda x: x["fiscal_year"], reverse=True)}
                      for c, f in sorted(companies.items(), key=lambda kv: kv[0].lower())],
        "incoming": library.incoming(),
        "sec_contact_set": library.sec_contact() is not None,  # whether one is saved; never the address
    })


def _year(value) -> int | None:
    return int(value) if str(value or "").strip().isdigit() else None


async def library_upload(request: Request) -> JSONResponse:
    params = request.query_params
    data = await request.body()
    if not data or len(data) > library.MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "Choose a PDF (up to 150 MB)."}, status_code=400)
    card = library.stage(data, params.get("filename", "filing.pdf"), params.get("company", ""),
                         _year(params.get("year")), "upload")
    return JSONResponse(card)


async def library_fetch(request: Request) -> JSONResponse:
    from indexit.sec import SecError, fetch

    body = await request.json()
    company, year = str(body.get("company", "")).strip(), _year(body.get("year"))
    if not company or not year:
        return JSONResponse({"error": "Enter the company and fiscal year."}, status_code=400)
    try:
        data, name, details = await asyncio.to_thread(fetch, company, year)
    except SecError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    card = await asyncio.to_thread(library.stage, data, name, company, year, "sec", details)
    return JSONResponse(card)


def _minutes_to_index() -> int:
    """Rough time until everything queued or indexing (including what was just added) is ready."""
    seconds = sum(SECONDS_PER_FILING + describe(FILINGS_DIR / n).pages * SECONDS_PER_PAGE for n in library.unfinished())
    return max(1, math.ceil(seconds / 60))


async def library_confirm(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        name = library.confirm(str(body.get("id")), str(body.get("company", "")), _year(body.get("year")) or 0)
    except (ValueError, FileNotFoundError) as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    indexer.add(name)
    entry = library.active_filings()[name]
    return JSONResponse({"file": name, "label": f"{entry['company']} FY{entry['fiscal_year']} 10-K",
                         "minutes": _minutes_to_index()})


async def library_cancel(request: Request) -> JSONResponse:
    library.cancel(str((await request.json()).get("id")))
    return JSONResponse({"ok": True})


async def library_remove(request: Request) -> JSONResponse:
    try:
        library.remove(str((await request.json()).get("file")))
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"ok": True})


async def library_reindex(request: Request) -> JSONResponse:
    name = str((await request.json()).get("file"))
    if name not in library.active_filings():
        return JSONResponse({"error": "Unknown filing."}, status_code=400)
    library.update(name, tables="pending", progress="Waiting to index")
    indexer.add(name)
    return JSONResponse({"ok": True})


async def save_sec_contact(request: Request) -> JSONResponse:
    try:
        library.save_sec_contact(str((await request.json()).get("value", "")))
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    return JSONResponse({"ok": True})


def _filing(file: str):
    """Only files in the filings folder, never arbitrary paths."""
    return next((f for f in list_filings() if f.file == file), None)


async def pdf(request: Request):
    filing = _filing(request.path_params["file"])
    if filing is None:
        return JSONResponse({"error": "Unknown file"}, status_code=404)
    return FileResponse(FILINGS_DIR / filing.file, media_type="application/pdf",
                        headers={"Content-Disposition": "inline"})


async def page(request: Request) -> JSONResponse:
    """A cited page's structured tables (Docling) and plain text, for the citation side panel."""
    filing = _filing(request.query_params.get("file", ""))
    number = int(request.query_params.get("page", "0") or 0)
    if filing is None or not 1 <= number <= filing.pages:
        return JSONResponse({"error": "Unknown page"}, status_code=404)
    with pymupdf.open(FILINGS_DIR / filing.file) as doc:
        text = doc[number - 1].get_text()
    return JSONResponse({
        "label": filing.label, "file": filing.file, "page": number, "text": text,
        "tables": [{"title": t.title, "rows": _rows(t.compact)} for t in page_tables(FILINGS_DIR / filing.file, number)],
    })


# The Compare view's figures, in the order of its chips (D-026). Reading them uses no plan: they come
# from the key-figures table, not from Claude.
COMPARE_METRICS = ["revenue", "net_income", "net_margin", "operating_margin", "gross_margin", "rd",
                   "rd_to_revenue", "revenue_growth", "cash", "debt"]


async def compare(request: Request) -> JSONResponse:
    """One figure across every company, ranked, with sources, plus rule-based insights."""
    metric = request.query_params.get("metric", "revenue")
    year = request.query_params.get("year", "")
    if metric not in COMPARE_METRICS or (year and not year.isdigit()):
        return JSONResponse({"error": "Unknown figure or year"}, status_code=400)
    result = await asyncio.to_thread(figures.comparison, metric, int(year) if year else None)
    result["insights"] = await asyncio.to_thread(figures.insights, result)
    result["metrics"] = [{"id": m, "name": figures.short_name(m)} for m in COMPARE_METRICS]
    result["companies"] = sorted({f.company for f in list_filings()})
    return JSONResponse(result)


async def compare_pair(request: Request) -> JSONResponse:
    """Two companies side by side on every figure, with sources and rule-based insights."""
    first, second = request.query_params.get("a", ""), request.query_params.get("b", "")
    year = request.query_params.get("year", "")
    if year and not year.isdigit():
        return JSONResponse({"error": "Unknown year"}, status_code=400)
    try:
        result = await asyncio.to_thread(figures.side_by_side, first, second, int(year) if year else None)
    except ValueError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
    result["all_companies"] = sorted({f.company for f in list_filings()})
    return JSONResponse(result)


def _rows(markdown: str) -> list[list[str]]:
    """Markdown table -> rows of cells (header first), skipping the |---| separator."""
    rows = []
    for line in markdown.splitlines():
        if re.fullmatch(r"\|?[\s|:-]+\|?", line):
            continue
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


@asynccontextmanager
async def lifespan(app: Starlette):
    FILINGS_DIR.mkdir(parents=True, exist_ok=True)  # a fresh copy of the repo starts with an empty library
    library.pick_up_dropped_files()
    conversations.start()
    indexer.start()
    yield
    await conversations.stop()
    await indexer.stop()


app = Starlette(
    routes=[
        Route("/", index),
        Route("/api/filings", filings),
        Route("/api/ask", ask, methods=["POST"]),
        Route("/api/new", new_conversation, methods=["POST"]),
        Route("/api/conversations", conversation_list),
        Route("/api/conversations/{id}", conversation),
        Route("/api/page", page),
        Route("/api/compare", compare),
        Route("/api/compare/pair", compare_pair),
        Route("/api/library", library_state),
        Route("/api/library/upload", library_upload, methods=["POST"]),
        Route("/api/library/fetch", library_fetch, methods=["POST"]),
        Route("/api/library/confirm", library_confirm, methods=["POST"]),
        Route("/api/library/cancel", library_cancel, methods=["POST"]),
        Route("/api/library/remove", library_remove, methods=["POST"]),
        Route("/api/library/reindex", library_reindex, methods=["POST"]),
        Route("/api/settings/sec-contact", save_sec_contact, methods=["POST"]),
        Route("/pdf/{file:path}", pdf),
        Mount("/static", StaticFiles(directory=STATIC), name="static"),
    ],
    lifespan=lifespan,
)


def serve(port: int = 8765, open_browser: bool = True) -> None:
    import threading
    import webbrowser

    import uvicorn

    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
