import json
import math
import logging
from pathlib import Path
from upstash_redis import Redis
from core.settings import settings


logger = logging.getLogger(__name__)
redis = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)
FAQ_FILE = Path(__file__).resolve().parents[1] / "cache" / "nawaloka_frequent_faqs.json"


# ── Seeding ───────────────────────────────────────────────────────────

def seed_faqs(embedder) -> None:
    """
    Call once at server startup. Reads nawaloka_frequent_faqs.json,
    embeds each question, and stores in Redis.

    Each FAQ is stored under  faq:<n>  as JSON:
        { "question": "...", "answer": "...", "embedding": [...] }

    faq:index holds the list of keys so the similarity check
    doesn't have to scan.
    """
    if not FAQ_FILE.is_file():
        logger.warning("[Cache] FAQ file not found: %s — skipping seed", FAQ_FILE)
        return

    with FAQ_FILE.open(encoding="utf-8") as f:
        faqs: list[dict] = json.load(f)

    # Wipe stale entries so a re-seed is idempotent
    existing_keys = redis.get(settings.faq_index_key)
    if existing_keys:
        for key in json.loads(existing_keys):
            redis.delete(key)

    index = []
    for i, faq in enumerate(faqs):
        question = faq.get("question", "").strip()
        answer   = faq.get("answer",   "").strip()
        if not question or not answer:
            continue

        embedding = embedder(question)          # list[float]
        key = f"{settings.faq_key_prefix}{i}"
        redis.set(key, json.dumps({
            "question":  question,
            "answer":    answer,
            "embedding": embedding,
        }))
        index.append(key)

    redis.set(settings.faq_index_key, json.dumps(index))
    logger.info("[Cache] Seeded %d FAQs into Redis", len(index))


# ── Similarity check ──────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def check_faq_cache(query_embedding: list[float]) -> str | None:
    """
    Returns the cached answer string if any FAQ question is similar
    enough to the user query, otherwise None.
    """
    index_raw = redis.get(settings.faq_index_key)
    if not index_raw:
        return None

    keys: list[str] = json.loads(index_raw)
    best_score  = -1.0
    best_answer = None

    for key in keys:
        raw = redis.get(key)
        if not raw:
            continue
        entry = json.loads(raw)
        score = _cosine_similarity(query_embedding, entry["embedding"])
        if score > best_score:
            best_score  = score
            best_answer = entry["answer"]

    if best_score >= settings.faq_similarity_threshold:
        logger.info("[Cache] Hit — similarity=%.4f", best_score)
        return best_answer

    logger.info("[Cache] Miss — best similarity=%.4f", best_score)
    return None