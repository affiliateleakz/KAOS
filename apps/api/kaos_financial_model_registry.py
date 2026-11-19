"""Third-party financial AI provider catalog for KAOS.

Catalog metadata is *not* an inference implementation or proof of trading accuracy.
Models must pass licensing, loading, chronological evaluation, and paper-trade gates.
Do not grant execution authority based on a model being registered here.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FinancialModel:
    id: str
    source: str
    task: str
    runtime: str
    status: str = "NOT_CONFIGURED"
    execution_authority: bool = False


MODELS = (
    FinancialModel("fingpt", "https://github.com/AI4Finance-Foundation/FinGPT",
                   "financial-research-and-sentiment", "isolated-transformers-worker"),
    FinancialModel("trading_hero", "https://huggingface.co/fuchenru/Trading-Hero-LLM",
                   "financial-text-sentiment", "isolated-transformers-worker"),
    FinancialModel("tiger_trading", "https://huggingface.co/TigerTrading/TradingBot",
                   "experimental-financial-sentiment", "gated-adapter-worker"),
    FinancialModel("alphafin_stockgpt_stage1",
                   "https://huggingface.co/AlphaFin/StockGPT-Stage1",
                   "financial-language-evaluation", "isolated-adapter-worker"),
    FinancialModel("alphafin_stockgpt_stage2",
                   "https://huggingface.co/AlphaFin/StockGPT-Stage2",
                   "financial-language-evaluation", "isolated-adapter-worker"),
    FinancialModel("stockgpt_returns_research", "https://arxiv.org/abs/2404.05101",
                   "numerical-return-model-research", "research-implementation-required"),
)


def catalog():
    """Return honest user-visible model states without triggering downloads."""
    return [asdict(model) for model in MODELS]


def require_trading_validation(model_id: str, verified: dict) -> bool:
    """Check independently recorded validation; registry never enables live execution."""
    if model_id not in {m.id for m in MODELS}:
        return False
    necessary = ("license_approved", "weights_verified", "holdout_passed",
                 "paper_passed", "risk_approved", "operator_enabled")
    return all(verified.get(field) is True for field in necessary)
