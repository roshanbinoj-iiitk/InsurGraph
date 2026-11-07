"""Project paths, splits and model registry."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_PDF_DIR = RAW_DIR / "pdfs"
GOLD_DIR = DATA_DIR / "gold"
SYNTH_DIR = DATA_DIR / "synthetic"
INTERIM_DIR = DATA_DIR / "interim"
PROMPTS_DIR = ROOT / "prompts"
RUNS_DIR = ROOT / "runs"
CACHE_DIR = ROOT / "cache"

# Dev/test split is by submission pack, because inconsistencies span documents.
DEV_PACKS = ("PACK000001",)
TEST_PACKS = ("PACK000002",)

# Bump when the extraction schema changes so cached LLM calls are invalidated.
SCHEMA_VERSION = "v1"


@dataclass(frozen=True)
class ModelSpec:
    """One LLM endpoint plus the free-tier limits we throttle against."""

    name: str
    provider: str  # "gemini" | "groq" | "local"
    model_id: str
    rpm: int | None = None
    tpm: int | None = None
    max_output_tokens: int = 2048
    extra: dict = field(default_factory=dict)


MODELS: dict[str, ModelSpec] = {
    # Planned free-tier API models (need GEMINI_API_KEY / GROQ_API_KEY).
    "gemini-flash-lite": ModelSpec(
        "gemini-flash-lite", "gemini", "gemini-3.5-flash-lite", rpm=15, tpm=250_000
    ),
    "gpt-oss-120b": ModelSpec(
        "gpt-oss-120b",
        "groq",
        "openai/gpt-oss-120b",
        rpm=30,
        tpm=8_000,
        extra={"reasoning_effort": "low"},
    ),
    "gpt-oss-20b": ModelSpec(
        "gpt-oss-20b",
        "groq",
        "openai/gpt-oss-20b",
        rpm=30,
        tpm=8_000,
        extra={"reasoning_effort": "low"},
    ),
    "qwen-judge": ModelSpec("qwen-judge", "groq", "qwen/qwen3.8-27b", rpm=30, tpm=8_000),
    # Local models served by LM Studio (OpenAI-compatible endpoint, no quota).
    "gemma-4-e4b": ModelSpec("gemma-4-e4b", "local", "google/gemma-4-e4b"),
    "qwen3.5-9b": ModelSpec(
        "qwen3.5-9b",
        "local",
        "huihui-qwen3.5-9b-abliterated",
        extra={"reasoning_effort": "none"},
    ),
}

LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def pack_of(doc_id: str) -> str:
    """Submission pack id from a document id like ``PACK000001_04_policy_schedule``."""
    return doc_id.split("_", 1)[0]


def split_of(doc_id: str) -> str:
    pack = pack_of(doc_id)
    if pack in DEV_PACKS or pack.startswith("SYNDEV"):
        return "dev"
    if pack in TEST_PACKS or pack.startswith("SYNTEST"):
        return "test"
    raise ValueError(f"Unknown pack for {doc_id}")
