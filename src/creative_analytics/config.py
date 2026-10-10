from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CREATIVES_DIR = ROOT / "creatives"
WAREHOUSE_DIR = ROOT / "data" / "warehouse"
VIEWS_DIR = ROOT / "sql" / "views"
DATABASE_PATH = ROOT / "creative_analytics.duckdb"

RAW_TABLES = [
    "creatives",
    "creative_timeline",
    "viewers",
    "viewing_sessions",
    "biometric_events",
    "survey_responses",
]


@dataclass(frozen=True)
class Creative:
    creative_id: str
    filename: str
    creative_name: str
    brand: str
    creative_category: str


CREATIVES = [
    Creative(
        "norwich_you_are_not_alone",
        "You Are Not Alone - Norwich City.mp4",
        "You Are Not Alone",
        "Norwich City",
        "emotional_campaign",
    ),
    Creative(
        "coordown_assume_that_i_can",
        "Assume that I can - CoorDown.mp4",
        "Assume That I Can",
        "CoorDown",
        "social_awareness",
    ),
    Creative(
        "problem_with_attention",
        "The Problem with Attention.mp4",
        "The Problem with Attention",
        "Element Human",
        "educational_content",
    ),
    Creative(
        "elf_peyton_lip_oil",
        "E.L.F Cosmetics Lip Oil - @peytonxblack.mp4",
        "Lip Oil - @peytonxblack",
        "e.l.f. Cosmetics",
        "ugc_product_ad",
    ),
    Creative(
        "elf_caro_lip_oil",
        "E.L.F Cosmetics Lip Oil - @caro_manning.mp4",
        "Lip Oil - @caro_manning",
        "e.l.f. Cosmetics",
        "ugc_product_ad",
    ),
]



RANDOM_SEED = 42
N_VIEWERS = 500
CREATIVES_PER_VIEWER = (2, 3)
FIELDWORK_START = "2026-09-01"
FIELDWORK_DAYS = 14

AGE_GROUPS = {"18-24": 0.20, "25-34": 0.27, "35-44": 0.22, "45-54": 0.17, "55+": 0.14}
GENDERS = {"female": 0.50, "male": 0.47, "non_binary": 0.03}
REGIONS = {"UK": 0.40, "US": 0.30, "Europe": 0.20, "Other": 0.10}


@dataclass(frozen=True)
class ResponseProfile:
    completion_rate: float
    attention: float
    attention_decay: float
    engagement: float
    brand_recall: float
    likability: float
    purchase_intent: float
    emotional_impact: float


RESPONSE_PROFILES = {
    "norwich_you_are_not_alone": ResponseProfile(0.45, 0.66, 0.10, 0.68, 0.50, 4.0, 2.2, 4.3),
    "coordown_assume_that_i_can": ResponseProfile(0.60, 0.70, 0.06, 0.70, 0.45, 4.2, 2.3, 4.1),
    "problem_with_attention": ResponseProfile(0.55, 0.78, 0.08, 0.60, 0.30, 3.4, 2.4, 2.6),
    "elf_peyton_lip_oil": ResponseProfile(0.62, 0.68, 0.10, 0.62, 0.78, 3.7, 3.6, 2.8),
    "elf_caro_lip_oil": ResponseProfile(0.75, 0.74, 0.06, 0.66, 0.66, 3.9, 3.3, 2.9),
}
