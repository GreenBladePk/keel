import os
import pytest
from keel.conflict.judge import LLMJudge
from keel.evals.runner import load_dataset, evaluate

# Gated live-LLM tests: run only when a provider key is set (deliberate, costs
# real calls). Provider-agnostic — picks whichever key is present, so it runs
# against Anthropic, OpenAI, or an OpenAI-compatible endpoint like RouterPlus
# (OPENAI_API_KEY + OPENAI_API_BASE).
_PROVIDER_KEYS = {"gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                  "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
_DEFAULT_MODEL = {"gemini": "gemini/gemini-2.0-flash",
                  "anthropic": "anthropic/claude-sonnet-5-5",
                  "openai": "openai/gpt-4.1-mini",
                  "openrouter": "openrouter/openai/gpt-4.1-mini"}


def _live_provider():
    for prov, env in _PROVIDER_KEYS.items():
        if os.environ.get(env):
            return prov
    return None


pytestmark = [pytest.mark.llm,
              pytest.mark.skipif(_live_provider() is None,
                                 reason="no LLM provider key set")]


@pytest.fixture
def _live(monkeypatch):
    prov = _live_provider()
    monkeypatch.setenv("KEEL_LLM_PROVIDER", prov)
    monkeypatch.setenv("KEEL_LLM_MODEL", os.environ.get("KEEL_LLM_MODEL", _DEFAULT_MODEL[prov]))
    return prov


async def test_real_contradiction(_live):
    out = await LLMJudge().judge(
        "orders API should use offset pagination",
        {"statement": "orders API uses cursor-based pagination", "rationale": ""})
    assert out.relation in {"contradicts", "supersedes"}
    assert out.evidence and out.evidence in "orders API uses cursor-based pagination"


async def test_eval_floor(_live):
    m = await evaluate(LLMJudge(), load_dataset())
    print(f"LLM eval precision={m.precision:.2f} recall={m.recall:.2f} f1={m.f1:.2f} n={m.n}")
    assert m.f1 >= 0.7
