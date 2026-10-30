"""Claude Code brain (D-014): answers by researching through the IndexIt MCP server only.

Uses the logged-in Claude Code account (Riya's Pro subscription): personal, local use only.
Guardrails are enforced by configuration, not just by the prompt:
  1. tools=[]                    -> no built-in tools at all (no files, shell, web, subagents)
  2. allowed_tools + dontAsk     -> only IndexIt tools run; anything else is denied, never prompted
  3. PreToolUse hook             -> backstop that denies any non-IndexIt tool call
  4. setting_sources=[]          -> ignore Riya's personal Claude Code settings, memory and skills
  5. strict_mcp_config + ENABLE_CLAUDEAI_MCP_SERVERS=false
                                 -> no other MCP servers, incl. claude.ai connectors
  6. fail closed                 -> abort before answering if the session sees any non-IndexIt tool
"""

import re
import sys
import time
from dataclasses import dataclass, field

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    ToolUseBlock,
)

from indexit.documents import PROJECT_DIR, format_filings
from indexit.prompts import agent_system_prompt

INDEXIT_TOOLS = "mcp__indexit__"
# Claude Code returns this as a normal "successful" result when the subscription's usage limit is hit.
PLAN_LIMIT = re.compile(r"hit your (session|usage|weekly|daily)? ?limit", re.I)
STRUCTURED_OUTPUT_TOOL = "StructuredOutput"  # SDK-internal: only returns the JSON answer; allowed only with output_format
MAX_TURNS = 15


def _allowed_tool(tool: str, structured: bool) -> bool:
    return tool.startswith(INDEXIT_TOOLS) or (structured and tool == STRUCTURED_OUTPUT_TOOL)


@dataclass
class AgentRun:
    answer: str = ""
    seconds: float = 0.0
    first_text_seconds: float | None = None  # when the first word of the answer streamed in
    turns: int = 0
    tool_calls: list[tuple[float, str, dict]] = field(default_factory=list)  # (seconds since start, tool, input)
    available_tools: list[str] = field(default_factory=list)
    api_equivalent_usd: float | None = None  # what the run would cost on the API; covered by the subscription here
    structured_output: dict | None = None
    models: list[str] = field(default_factory=list)  # model(s) that actually answered, e.g. ["claude-opus-5-5"]
    usage: dict | None = None  # token counts from the final result
    session_id: str | None = None  # Claude Code session, resumable later (the app's saved conversations)
    error: str | None = None


def _only_allowed_tools(structured: bool):
    async def hook(hook_input, tool_use_id, context):
        tool = hook_input.get("tool_name", "")
        if _allowed_tool(tool, structured):
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"IndexIt agents may only use IndexIt tools, not {tool}.",
            }
        }

    return hook


def _options(
    model: str | None,
    effort: str | None = None,
    system_prompt: str | None = None,
    output_format: dict | None = None,
    resume: str | None = None,
) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=system_prompt or agent_system_prompt(format_filings()),
        mcp_servers={
            "indexit": {"type": "stdio", "command": sys.executable, "args": ["-m", "indexit.mcp_server"]},
        },
        tools=[],
        allowed_tools=[f"{INDEXIT_TOOLS}*"] + ([STRUCTURED_OUTPUT_TOOL] if output_format else []),
        permission_mode="dontAsk",
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[_only_allowed_tools(output_format is not None)])]},
        setting_sources=[],
        strict_mcp_config=True,
        env={"ENABLE_CLAUDEAI_MCP_SERVERS": "false"},
        max_turns=MAX_TURNS,
        cwd=PROJECT_DIR,
        model=model,
        effort=effort,  # low | medium | high; lower = less thinking before answering = faster
        output_format=output_format,
        include_partial_messages=True,  # stream the answer word by word
        resume=resume,  # continue an earlier session, with its full memory
    )


class AgentSession:
    """One conversation with Claude Code. Follow-up questions reuse the running session (no restart cost)."""

    def __init__(self, model: str | None = None, effort: str | None = None, **options):
        self._structured = options.get("output_format") is not None
        self._client = ClaudeSDKClient(options=_options(model, effort, **options))

    async def __aenter__(self) -> "AgentSession":
        await self._client.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.disconnect()

    async def ask(self, question: str, on_text=None, on_tool_call=None) -> AgentRun:
        run, start = AgentRun(), time.monotonic()
        await self._client.query(question)
        async for message in self._client.receive_response():
            if isinstance(message, SystemMessage) and message.subtype == "init":
                run.available_tools = message.data.get("tools", [])
                unexpected = [t for t in run.available_tools if not _allowed_tool(t, self._structured)]
                if unexpected:
                    raise RuntimeError(f"Guardrail: agent session exposed non-IndexIt tools {unexpected}; aborted.")
            elif isinstance(message, StreamEvent):
                delta = message.event.get("delta", {})
                if message.event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                    run.first_text_seconds = run.first_text_seconds or time.monotonic() - start
                    if on_text:
                        on_text(delta["text"])
            elif isinstance(message, AssistantMessage):
                if message.model not in run.models:
                    run.models.append(message.model)
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        call = (time.monotonic() - start, block.name.removeprefix(INDEXIT_TOOLS), block.input)
                        run.tool_calls.append(call)
                        if on_tool_call:
                            on_tool_call(*call)
            elif isinstance(message, ResultMessage):
                run.answer = message.result or ""
                if PLAN_LIMIT.search(run.answer) and len(run.answer) < 200:
                    run.error = "plan_limit"  # not an answer: the Pro plan's usage limit was reached
                run.turns = message.num_turns
                run.api_equivalent_usd = message.total_cost_usd
                run.structured_output = message.structured_output
                run.usage = message.model_usage or message.usage
                run.session_id = message.session_id
                if message.is_error and not run.error:
                    run.error = message.subtype
        run.seconds = time.monotonic() - start
        return run


async def ask_agent(question: str, model: str | None = None, effort: str | None = None, **callbacks) -> AgentRun:
    async with AgentSession(model, effort) as session:
        return await session.ask(question, **callbacks)


def dig_deeper_questions(answer: str) -> list[str]:
    """The numbered follow-up questions under the answer's "Dig deeper" heading."""
    section = answer.split("## Dig deeper", 1)[-1] if "## Dig deeper" in answer else ""
    return [q.strip().strip("*") for q in re.findall(r"^\s*\d+[.)]\s+(.+)$", section, re.M)]
