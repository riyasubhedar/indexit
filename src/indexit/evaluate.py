"""Agent eval (D-008, D-016): run golden questions through a config, then fact-check every answer.

A separate fact-checker agent (Opus, high effort, same locked-down IndexIt tools) opens the cited
pages and lists wrong or unsupported claims. Accuracy is the headline metric: an answer with
any wrong or unsupported claim FAILS, however complete it is.

Results go to eval/runs/<timestamp>/ (one JSONL row per question + summary.md).
"""

import asyncio
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

from indexit.agent import PLAN_LIMIT, AgentSession, dig_deeper_questions
from indexit.documents import PROJECT_DIR, format_filings
from indexit.prompts import fact_checker_prompt

GOLDEN = PROJECT_DIR / "eval" / "golden_questions.md"
RUNS_DIR = PROJECT_DIR / "eval" / "runs"
CHECKER = {"model": "opus", "effort": "high"}

CHECK_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "covered_points": {"type": "array", "items": {"type": "string"}},
            "missed_points": {"type": "array", "items": {"type": "string"}},
            "coverage": {"type": "number", "description": "0-1 share of answer-key points covered correctly"},
            "wrong_claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"claim": {"type": "string"}, "correct": {"type": "string"}, "evidence": {"type": "string"}},
                    "required": ["claim", "correct", "evidence"],
                },
            },
            "unsupported_claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"claim": {"type": "string"}, "why": {"type": "string"}},
                    "required": ["claim", "why"],
                },
            },
            "claims_checked": {"type": "integer"},
            "format_ok": {"type": "boolean"},
            "format_issues": {"type": "string"},
        },
        "required": [
            "covered_points", "missed_points", "coverage", "wrong_claims",
            "unsupported_claims", "claims_checked", "format_ok", "format_issues",
        ],
    },
}


SETS = ("dev", "test", "extra")


def load_golden(path: Path = GOLDEN, subset: str = "all") -> list[dict]:
    """Rows of golden_questions.md: | # | Question | Types | Expected | Source | Set |, grouped by the
    "## <company>" heading above each table. `subset`: dev, test, extra, all, or e.g. "dev,test"."""
    wanted = SETS if subset == "all" else tuple(subset.split(","))
    rows, group = [], ""
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            group = line[3:].strip()
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0].isdigit() and cells[1] and cells[-1] in SETS:
            row = {
                "id": int(cells[0]), "question": cells[1], "types": cells[2], "group": group,
                "expected": " | ".join(cells[3:-2]), "source": cells[-2], "set": cells[-1],
            }
            if row["set"] in wanted:
                rows.append(row)
    return rows


def parse_config(spec: str) -> dict:
    """"sonnet" -> {model: sonnet}; "opus:low" -> {model: opus, effort: low}."""
    model, _, effort = spec.partition(":")
    return {"name": spec, "model": model or None, "effort": effort or None}


def parse_ids(spec: str | None, available: list[int]) -> list[int]:
    if not spec:
        return available
    ids = []
    for part in spec.split(","):
        start, _, end = part.partition("-")
        ids += range(int(start), int(end or start) + 1)
    return [i for i in ids if i in available]


# ---- Search-only eval (free, no LLM): does retrieval find the expected pages and the right company? ----

_CODES = {
    "NVDA": "NVIDIA", "AMD": "Advanced Micro Devices", "AAPL": "Apple", "MSFT": "Microsoft",
    "AMZN": "Amazon.com", "TSLA": "Tesla", "JPM": "JPMorgan Chase",
}
# "Mentions vs. about" probes for companies the golden set doesn't cover yet: (question, company it's about).
_COMPANY_PROBES = [
    ("What are the biggest risks for Microsoft?", "Microsoft"),
    ("What was Microsoft's revenue in fiscal year 2026?", "Microsoft"),
    ("What are Apple's biggest risks?", "Apple"),
    ("Who does Tesla compete with?", "Tesla"),
    ("How fast is AWS growing?", "Amazon.com"),
    ("How much money did JPMorgan make in 2025?", "JPMorgan Chase"),
    ("Does Microsoft depend on NVIDIA chips?", "Microsoft"),
]


def expected_pages(source: str) -> list[tuple[str, int, int]]:
    """"NVDA-FY26 · p51 (also p78) · AMD-FY25 p74" -> [(NVIDIA, 2026, 51), (NVIDIA, 2026, 78), (AMD…, 2025, 74)]."""
    found, current = [], None
    # Read filing codes and page numbers left to right, so "NVDA-FY26 · p51 (also NVDA-FY25 p52)" puts
    # p51 in FY26 and p52 in FY25.
    for code, year, start, end in re.findall(r"\b([A-Z]{2,5})-FY(\d{2})\b|\bp(\d+)(?:[–-](\d+))?", source):
        if code:
            current = (_CODES[code], 2000 + int(year))
        elif current:
            found += [(*current, page) for page in range(int(start), int(end or start) + 1)]
    return found


def key_figures(expected: str) -> list[str]:
    """Exact figures in an answer key that a filing page would print, e.g. "$4,335M" -> "4,335", "$1,448.75".

    Only comma-grouped numbers count: computed percentages ("65.5% *calc*") never appear in a filing.
    """
    return sorted(set(re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", expected)))


def search_eval(k: int = 8, tables: list[str] | None = None, subset: str = "dev") -> str:
    """Search decisions use the dev set only (D-017/D-019); `subset` can widen it for reporting."""
    from indexit.documents import list_filings
    from indexit.search import TABLE, retrieve

    filings = {f.file: f for f in list_filings()}
    questions = [g for g in load_golden(subset=subset) if expected_pages(g["source"])]
    lines = []
    # "table" or "table+hybrid"; with no tables: the live index, plain vs company-aware
    modes = [(TABLE, False, None), (TABLE, True, None)] if not tables else [
        (t.removesuffix("+hybrid"), True, t.endswith("+hybrid")) for t in tables
    ]
    for table, by_company, hybrid in modes:
        pages_found, figure_shares, precisions, misses = 0, [], [], []
        by_group = {}  # per-company breakdown; the last mode's is shown
        for g in questions:
            expected = expected_pages(g["source"])
            results = retrieve(g["question"], k, by_company=by_company, table=table, hybrid=hybrid)
            got = {(filings[r["doc"]].company, filings[r["doc"]].fiscal_year, r["page"]) for r in results}
            companies = {e[0] for e in expected}
            precisions.append(sum(filings[r["doc"]].company in companies for r in results) / len(results))
            found = bool(got & set(expected))
            pages_found += found
            if not found:
                misses.append(f"#{g['id']}")
            by_group.setdefault(g["group"], []).append(found)
            if figures := key_figures(g["expected"]):
                text = " ".join(r["text"] for r in results)
                figure_shares.append(sum(fig in text for fig in figures) / len(figures))
        for question, company in _COMPANY_PROBES:
            results = retrieve(question, k, by_company=by_company, table=table, hybrid=hybrid)
            if results:  # empty when an index version lacks that company's filings
                precisions.append(sum(filings[r["doc"]].company == company for r in results) / len(results))
        mode = f"{table}{' + hybrid' if hybrid else ''}, {'company-aware' if by_company else 'plain'}"
        lines.append(
            f"| {mode} | {pages_found}/{len(questions)} | {statistics.mean(figure_shares):.0%} "
            f"({len(figure_shares)} Qs) | {statistics.mean(precisions):.0%} | {', '.join(misses) or '-'} |"
        )
    header = [
        f"Set: {subset} ({len(questions)} questions with expected pages)",
        f"| Index, search mode | Expected page in top {k} | Key figures in results | Right-company share | Page misses |",
        "|---|---|---|---|---|",
    ]
    per_group = ["", f"Per company (last mode): expected page in top {k}"] + [
        f"- {group}: {sum(found)}/{len(found)}" for group, found in by_group.items()
    ]
    return "\n".join(header + lines + per_group)


def _shorthand_legend() -> str:
    """"NVDA-FY26 = NVIDIA FY2026 10-K, …" for every company code, so the fact-checker can read answer keys."""
    from indexit.documents import list_filings

    codes = {name: code for code, name in _CODES.items()}
    return ", ".join(
        f"{codes.get(f.company, f.company)}-FY{str(f.fiscal_year)[2:]} = {f.label}" for f in list_filings()
    )


async def answer(config: dict, question: str):
    async with AgentSession(config["model"], config["effort"]) as session:
        return await session.ask(question)


async def fact_check(item: dict, answer_text: str) -> tuple[dict, dict]:
    """(the checker's structured verdict, metadata about the checking run)."""
    prompt = (
        f"Answer-key shorthand: {_shorthand_legend()}. Pages are PDF page numbers.\n\n"
        f"QUESTION:\n{item['question']}\n\nANSWER KEY (type: {item['types']}; source: {item['source']}):\n"
        f"{item['expected']}\n\nINDEXIT'S ANSWER:\n{answer_text}"
    )
    async with AgentSession(**CHECKER, system_prompt=fact_checker_prompt(format_filings()), output_format=CHECK_SCHEMA) as s:
        run = await s.ask(prompt)
    meta = {"seconds": round(run.seconds, 1), "tool_calls": len(run.tool_calls), "models": run.models,
            "usage": run.usage, "api_equivalent_usd": run.api_equivalent_usd, "error": run.error}
    return run.structured_output or {"error": run.error or "no structured output", "raw": run.answer}, meta


def _run_metadata(configs: list[str], subset: str, ids: list[int]) -> dict:
    """Everything needed to trace results back to the exact setup that produced them."""
    import hashlib
    from importlib.metadata import version

    from indexit import prompts, search
    from indexit.documents import list_filings

    prompt_text = prompts.agent_system_prompt(format_filings()) + prompts.fact_checker_prompt(format_filings())
    return {
        "started": datetime.now().isoformat(timespec="seconds"), "configs": configs, "set": subset, "question_ids": ids,
        "checker": CHECKER, "index_table": search.TABLE, "hybrid": search.HYBRID, "prefer_latest": search.PREFER_LATEST,
        "top_k": search.TOP_K, "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest()[:12],
        "claude_agent_sdk": version("claude-agent-sdk"), "filings": [f.label for f in list_filings()],
    }


def _complete(row: dict) -> bool:
    """A finished, graded answer, not a failed check and not a plan-limit message recorded as an answer."""
    return "error" not in row["check"] and row.get("error") != "plan_limit" and not (
        PLAN_LIMIT.search(row["answer"]) and len(row["answer"]) < 200
    )


def _latest_run() -> Path:
    """The newest run folder (named by timestamp); log files next to the folders are ignored."""
    return max(p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "run.json").exists())


def _load_rows(out_dir: Path) -> dict[tuple[str, int], dict]:
    rows = {}
    for path in out_dir.glob("*.jsonl"):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            rows[(row["config"], row["id"])] = row  # a later line (e.g. a retried check) replaces an earlier one
    return rows


async def run_eval(configs: list[str], ids_spec: str | None = None, subset: str = "dev", resume: str | None = None) -> Path:
    """Answer + fact-check each question with each config, alternating configs per question so an interrupted
    run leaves every config with the same questions done. `resume`: a run folder, or "latest"."""
    items = {g["id"]: g for g in load_golden(subset=subset)}
    ids = parse_ids(ids_spec, list(items))
    if resume:
        out_dir = _latest_run() if resume == "latest" else Path(resume)
        meta = json.loads((out_dir / "run.json").read_text())
        configs, ids, subset = meta["configs"], meta["question_ids"], meta["set"]
        items = {g["id"]: g for g in load_golden(subset=subset)}
        print(f"Resuming {out_dir.name}")
    else:
        out_dir = RUNS_DIR / datetime.now().strftime("%Y-%m-%d_%H%M")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run.json").write_text(json.dumps(_run_metadata(configs, subset, ids), indent=2))
    done = {key for key, row in _load_rows(out_dir).items() if _complete(row)}
    for qid in ids:
        item = items[qid]
        for spec in configs:
            if (spec, qid) in done:
                continue
            config = parse_config(spec)
            print(f"[{spec}] #{qid} ({item['group']}) {item['question'][:60]}…", flush=True)
            run = await answer(config, item["question"])
            if run.error == "plan_limit":
                raise SystemExit(f"Stopped: {run.answer} Resume afterwards with: uv run indexit eval --resume {out_dir}")
            check, check_meta = await fact_check(item, run.answer)
            if check_meta["error"] == "plan_limit":
                raise SystemExit(f"Stopped during fact-check: plan limit reached. Resume with: uv run indexit eval --resume {out_dir}")
            wrong, unsupported = check.get("wrong_claims", []), check.get("unsupported_claims", [])
            body = run.answer.split("## Dig deeper", 1)[0]
            row = {
                "config": spec, "id": qid, "group": item["group"], "set": item["set"], "types": item["types"],
                "question": item["question"], "answer": run.answer, "models": run.models, "error": run.error,
                "seconds": round(run.seconds, 1),
                "first_text_seconds": round(run.first_text_seconds, 1) if run.first_text_seconds else None,
                "turns": run.turns, "tool_calls": [{"t": round(t, 1), "tool": tool, "input": inp} for t, tool, inp in run.tool_calls],
                "answer_words": len(body.split()), "dig_deeper": dig_deeper_questions(run.answer),
                "usage": run.usage, "api_equivalent_usd": run.api_equivalent_usd,
                "check": check, "check_meta": check_meta,
                "passed": "error" not in check and not wrong and not unsupported and check.get("format_ok", False),
            }
            with open(out_dir / f"{spec.replace(':', '-')}.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")
            verdict = "PASS" if row["passed"] else f"FAIL ({len(wrong)} wrong, {len(unsupported)} unsupported)"
            if "error" in check:
                verdict = f"CHECK ERROR ({check['error']}), will retry on resume"
            print(f"    {verdict} · coverage {check.get('coverage', 0):.0%} · answer {run.seconds:.0f}s · check {check_meta['seconds']:.0f}s", flush=True)
    rows = _load_rows(out_dir)
    results = {spec: [rows[(spec, q)] for q in ids if (spec, q) in rows and _complete(rows[(spec, q)])] for spec in configs}
    summary = _summary(results)
    (out_dir / "summary.md").write_text(summary)
    print("\n" + summary)
    return out_dir


def tokens(usage: dict | None) -> dict[str, int]:
    """Token totals across the models in one run's usage record (Claude Code adds a tiny Haiku
    housekeeping call; it's included, since it's part of what the run consumed)."""
    totals = {"input": 0, "cached": 0, "output": 0, "thinking": 0}
    for model in (usage or {}).values():
        if not isinstance(model, dict):
            continue
        totals["input"] += model.get("inputTokens", 0) + model.get("cacheCreationInputTokens", 0)
        totals["cached"] += model.get("cacheReadInputTokens", 0)
        totals["output"] += model.get("outputTokens", 0)
        totals["thinking"] += model.get("thinkingTokens", 0)
    return totals


async def recheck(run_dir: str, ids: list[int], configs: list[str] | None = None) -> None:
    """Re-run the fact-check (not the answer) for these questions, e.g. after an answer key was revised.
    The new record is appended and replaces the old one."""
    out_dir = _latest_run() if run_dir == "latest" else Path(run_dir)
    items, rows = {g["id"]: g for g in load_golden()}, _load_rows(out_dir)
    for (spec, qid), row in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if qid not in ids or (configs and spec not in configs) or not _complete(row):
            continue
        check, check_meta = await fact_check(items[qid], row["answer"])
        if check_meta["error"] == "plan_limit":
            raise SystemExit("Stopped during recheck: plan limit reached.")
        wrong, unsupported = check.get("wrong_claims", []), check.get("unsupported_claims", [])
        row = {**row, "check": check, "check_meta": check_meta, "rechecked": datetime.now().isoformat(timespec="seconds"),
               "passed": "error" not in check and not wrong and not unsupported and check.get("format_ok", False)}
        with open(out_dir / f"{spec.replace(':', '-')}.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"[{spec}] #{qid} rechecked: {'PASS' if row['passed'] else f'FAIL ({len(wrong)} wrong, {len(unsupported)} unsupported)'}")


def summarize(run_dir: str) -> str:
    """Rebuild summary.md from a run's saved records (e.g. after changing the summary format)."""
    out_dir = _latest_run() if run_dir == "latest" else Path(run_dir)
    meta, rows = json.loads((out_dir / "run.json").read_text()), _load_rows(out_dir)
    results = {spec: [rows[(spec, q)] for q in meta["question_ids"] if (spec, q) in rows and _complete(rows[(spec, q)])]
               for spec in meta["configs"]}
    summary = _summary(results)
    (out_dir / "summary.md").write_text(summary)
    return summary


def _summary(results: dict[str, list[dict]]) -> str:
    def pct(values, q):
        values = sorted(values)
        return values[min(len(values) - 1, int(q * len(values)))] if values else 0

    lines = [
        "## Overall",
        "| Config | **Accuracy** (no wrong/unsupported claims) | Wrong claims | Unsupported | Avg coverage | Median / 90th pct time | Avg words | Avg searches | 3 follow-ups | Format OK | ≈API $ |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for spec, rows in results.items():
        n, ok = len(rows), [r for r in rows if "error" not in r["check"]]
        if not n:
            continue
        lines.append(
            f"| {spec} ({', '.join(sorted({m for r in rows for m in r['models']}))}) | **{sum(r['passed'] for r in rows)}/{n}** "
            f"| {sum(len(r['check'].get('wrong_claims', [])) for r in ok)} "
            f"| {sum(len(r['check'].get('unsupported_claims', [])) for r in ok)} "
            f"| {statistics.mean(r['check'].get('coverage', 0) for r in ok) if ok else 0:.0%} "
            f"| {statistics.median(r['seconds'] for r in rows):.0f}s / {pct([r['seconds'] for r in rows], 0.9):.0f}s "
            f"| {statistics.mean(r['answer_words'] for r in rows):.0f} "
            f"| {statistics.mean(len(r['tool_calls']) for r in rows):.1f} "
            f"| {sum(len(r['dig_deeper']) == 3 for r in rows)}/{n} "
            f"| {sum(r['check'].get('format_ok', False) for r in ok)}/{n} "
            f"| {sum(r['api_equivalent_usd'] or 0 for r in rows):.2f} |"
        )
    lines += ["", "## Tokens (average per question)",
              "| Config | Answer: new input | Answer: cached input | Answer: output | of which thinking | Fact-check: total |",
              "|---|---|---|---|---|---|"]
    for spec, rows in results.items():
        if not rows:
            continue
        answer_tokens = [tokens(r["usage"]) for r in rows]
        check_usage = [tokens(r["check_meta"].get("usage")) for r in rows if r["check_meta"].get("usage")]
        avg = lambda key: statistics.mean(t[key] for t in answer_tokens)
        check_total = (f"{statistics.mean(sum(t.values()) for t in check_usage):,.0f}" if check_usage
                       else "not recorded in this run")
        lines.append(f"| {spec} | {avg('input'):,.0f} | {avg('cached'):,.0f} | {avg('output'):,.0f} | {avg('thinking'):,.0f} | {check_total} |")
    specs = list(results)
    groups = sorted({r["group"] for rows in results.values() for r in rows})
    lines += ["", "## Accuracy per company", "| Company | " + " | ".join(specs) + " |", "|---" * (len(specs) + 1) + "|"]
    for group in groups:
        cells = []
        for rows in results.values():
            in_group = [r for r in rows if r["group"] == group]
            cells.append(f"{sum(r['passed'] for r in in_group)}/{len(in_group)}" if in_group else "-")
        lines.append(f"| {group} | " + " | ".join(cells) + " |")
    by_id = {spec: {r["id"]: r for r in rows} for spec, rows in results.items()}
    ids = sorted({r["id"] for rows in results.values() for r in rows})
    lines += ["", "## Question by question",
              "| # | Company | " + " | ".join(f"{s} (verdict · coverage · time)" for s in specs) + " |",
              "|---|---" + "|---" * len(specs) + "|"]
    for qid in ids:
        cells = []
        for spec in specs:
            r = by_id[spec].get(qid)
            if r is None:
                cells.append("-")
                continue
            c = r["check"]
            mark = "✅" if r["passed"] else f"❌ {len(c.get('wrong_claims', []))}w/{len(c.get('unsupported_claims', []))}u"
            cells.append(f"{mark} · {c.get('coverage', 0):.0%} · {r['seconds']:.0f}s")
        group = next(by_id[s][qid]["group"] for s in specs if qid in by_id[s])
        lines.append(f"| {qid} | {group} | " + " | ".join(cells) + " |")
    problems = [
        f"- **{r['config']} #{r['id']}** ({r['group']}) {kind}: {c['claim']} → {c.get('correct') or c.get('why')}"
        for rows in results.values() for r in rows
        for kind, key in (("WRONG", "wrong_claims"), ("UNSUPPORTED", "unsupported_claims"))
        for c in r["check"].get(key, [])
    ]
    return "\n".join(lines + ["", "## Flagged claims", *(problems or ["- none"])]) + "\n"
