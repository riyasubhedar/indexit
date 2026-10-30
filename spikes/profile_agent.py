"""Latency spike: timeline of one agent run, split into startup, model turns, tool time and answer writing.

  uv run python spikes/profile_agent.py "question" [--model sonnet] [--effort low]
"""

import argparse
import asyncio
import dataclasses
import time

from claude_agent_sdk import AssistantMessage, ResultMessage, StreamEvent, SystemMessage, ToolUseBlock, UserMessage, query

from indexit.agent import _options

parser = argparse.ArgumentParser()
parser.add_argument("question")
parser.add_argument("--model")
parser.add_argument("--effort")
parser.add_argument("--save", help="write the full answer to this file")
args = parser.parse_args()


async def main():
    options = dataclasses.replace(_options(args.model, args.effort), include_partial_messages=True)
    start = time.monotonic()
    now = lambda: time.monotonic() - start
    last, first_text, models, out_tokens = 0.0, None, set(), 0
    timeline = []  # (label, seconds)

    def mark(label):
        nonlocal last
        t = now()
        timeline.append((label, t - last))
        last = t

    async for msg in query(prompt=args.question, options=options):
        if isinstance(msg, SystemMessage) and msg.subtype == "init":
            mark("startup (Claude Code + MCP server launch)")
        elif isinstance(msg, StreamEvent):
            delta = msg.event.get("delta", {})
            if msg.event.get("type") == "content_block_delta" and delta.get("type") == "text_delta" and first_text is None:
                first_text = now()
        elif isinstance(msg, AssistantMessage):
            models.add(msg.model)
            out_tokens += (msg.usage or {}).get("output_tokens", 0)
            tools = [b.name.removeprefix("mcp__indexit__") for b in msg.content if isinstance(b, ToolUseBlock)]
            mark(f"model turn → {', '.join(tools)}" if tools else "model turn → writes answer")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            mark("tool execution (MCP server)")
        elif isinstance(msg, ResultMessage):
            total = now()
            print(f"\nmodel: {', '.join(sorted(models))} · effort: {args.effort or 'default'}")
            for label, secs in timeline:
                print(f"  {secs:6.1f}s  {label}")
            print(f"  ------\n  {total:6.1f}s  TOTAL  ({msg.num_turns} turns, ~{out_tokens} output tokens)")
            if first_text:
                print(f"  {first_text:6.1f}s  until the first word of the answer appears (if streamed)")
            print(f"\n--- answer: {len(msg.result or '')} characters ---\n{(msg.result or '')[:600]}…")
            if args.save:
                open(args.save, "w").write(msg.result or "")


asyncio.run(main())
