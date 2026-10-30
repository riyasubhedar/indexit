"""The "brain" (D-009): writes the answer from retrieved passages. Claude API today; swappable later."""

from dataclasses import dataclass

import anthropic

from indexit.prompts import API_SYSTEM_PROMPT

MODEL = "claude-opus-5-5"
EFFORT = "high"  # how hard the model thinks; higher = better reasoning over numbers, more output tokens


@dataclass
class Answer:
    text: str
    input_tokens: int
    output_tokens: int


class ClaudeBrain:
    def __init__(self, model: str = MODEL, effort: str = EFFORT):
        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort

    def answer(self, question: str, passages: list[dict]) -> Answer:
        context = "\n\n".join(
            f'<passage file="{p["doc"]}" page="{p["page"]}">\n{p["text"]}\n</passage>' for p in passages
        )
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=API_SYSTEM_PROMPT,
            output_config={"effort": self.effort},
            # If a safety classifier declines, retry server-side on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": f"<passages>\n{context}\n</passages>\n\nQuestion: {question}"}],
        )
        if response.stop_reason == "refusal":
            text = "IndexIt couldn't answer this question (the model declined)."
        else:
            text = "".join(block.text for block in response.content if block.type == "text")
        return Answer(text=text, input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
