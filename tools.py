"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
        listings = load_listings()
        results = []

        # Turn the user's description into individual lowercase keywords
        keywords = description.lower().split()

        for listing in listings:

            # Filter by maximum price
            if max_price is not None and listing["price"] > max_price:
                continue

            # Filter by size
            if size is not None:
                listing_sizes = [
                    part.strip().lower()
                    for part in listing["size"].replace("/", " ").split()
                ]

                if size.lower() not in listing_sizes:
                    continue

            # Combine searchable fields into one string
            searchable_fields = [
                listing["title"],
                listing["description"],
                listing["category"],
                listing["condition"],
                listing["brand"] or "",
                " ".join(listing["style_tags"]),
                " ".join(listing["colors"]),
            ]

            searchable_text = " ".join(searchable_fields).lower()

            # One point for each description keyword that matches
            score = 0
            for keyword in keywords:
                if keyword in searchable_text:
                    score += 1

            # Require stronger relevance for multi-word searches
            minimum_matches = 2 if len(keywords) >= 2 else 1

            if score < minimum_matches:
                continue

            results.append((score, listing))

        # Best matches first
        results.sort(key=lambda result: result[0], reverse=True)

        # Remove scores and enforce the configured result limit
        return [
            listing
            for score, listing in results[:config.SEARCH_RESULT_LIMIT]
        ]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
        items = wardrobe.get("items", [])

        # Handle an empty wardrobe
        if not items:
            prompt = f"""
    The user is considering this new item:
    {new_item}

    Their wardrobe is currently empty.

    Give a short, practical suggestion for how they could style this item
    using general clothing recommendations.
    """
            return generate(prompt)

        # Format wardrobe items for the model
        wardrobe_text = "\n".join(
            f"- {item['name']} | category: {item['category']} | "
            f"colors: {', '.join(item['colors'])} | "
            f"style: {', '.join(item['style_tags'])}"
            for item in items
        )

        # Format the new item
        new_item_text = (
            f"{new_item['title']} | "
            f"category: {new_item['category']} | "
            f"colors: {', '.join(new_item['colors'])} | "
            f"style: {', '.join(new_item['style_tags'])}"
        )

        prompt = f"""
    The user is considering buying this item:

    {new_item_text}

    Their current wardrobe contains:

    {wardrobe_text}

    Create one outfit using the new item and compatible pieces from the
    user's wardrobe.

    When appropriate, prioritize choosing a top, bottom, and shoes to form
    the base outfit. Do not invent wardrobe items that are not listed.

    Return a concise outfit suggestion that names the
    specific wardrobe pieces you selected and briefly explains why they
    work with the new item.
    """

        return generate(prompt)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
            # Guard against an empty outfit
        if not outfit or not outfit.strip():
            return "Cannot create a fit card because no outfit was provided."

        prompt = f"""
    Write a short, post-ready caption for this outfit.

    Outfit suggestion:
    {outfit}

    New item:
    - Item: {new_item['title']}
    - Price: ${new_item['price']:.2f}
    - Platform: {new_item['platform']}

    Requirements:
    - Write 2 to 4 sentences.
    - Mention the new item.
    - Mention its price exactly once.
    - Mention the platform exactly once.
    - Describe the specific vibe of the outfit.
    - Make it sound like something a person would actually post.
    - Do not write a generic product description.

    Return only the caption.
    """

        return generate(prompt)


# ── Tool 4: semantic_search ← UNIT 9 (capstone) ──────────────────────────────
#
# A fallback for when search_listings returns nothing because the user's words
# aren't in the listings ("retro t-shirt" vs "vintage graphic tee"). It keeps
# the same price and size filters, then ranks by meaning instead of keywords.

import json
import math
from pathlib import Path

from generate import embed

EMBEDDINGS_FILE = Path(__file__).parent / "data" / "listing_embeddings.json"


def _listing_text(listing: dict) -> str:
    """The text that represents a listing when it is embedded."""
    return " | ".join([
        listing["title"],
        listing["description"],
        listing["category"],
        ", ".join(listing["style_tags"]),
        ", ".join(listing["colors"]),
    ])


def _passes_filters(listing: dict, size: str | None, max_price: float | None) -> bool:
    """Same price and size rules as search_listings."""
    if max_price is not None and listing["price"] > max_price:
        return False
    if size is not None:
        sizes = [p.strip().lower() for p in listing["size"].replace("/", " ").split()]
        if size.lower() not in sizes:
            return False
    return True


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine of the angle between two vectors: 1 = same direction."""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def load_listing_embeddings() -> dict[str, list[float]]:
    """
    Listing id → embedding. Read from data/listing_embeddings.json; any listing
    missing from the file (or a file made with a different model/size) is
    embedded now and the file is rewritten. Normally this costs nothing per run.
    """
    listings = load_listings()
    stored = {}
    if EMBEDDINGS_FILE.exists():
        data = json.loads(EMBEDDINGS_FILE.read_text())
        if (data.get("model") == config.EMBED_MODEL
                and data.get("dimensions") == config.EMBED_DIMENSIONS):
            stored = data.get("embeddings", {})

    missing = [l for l in listings if l["id"] not in stored]
    if missing:
        vectors = embed([_listing_text(l) for l in missing])
        for listing, vector in zip(missing, vectors):
            stored[listing["id"]] = vector
        EMBEDDINGS_FILE.write_text(json.dumps({
            "model": config.EMBED_MODEL,
            "dimensions": config.EMBED_DIMENSIONS,
            "embeddings": stored,
        }))
    return stored


def semantic_search(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Find listings by meaning when keyword search found none.

    Returns up to config.SEMANTIC_RESULT_LIMIT listing dicts, best first, each
    with an added "similarity" key (cosine, -1 to 1). Only listings that pass
    the price/size filters AND score at least config.SEMANTIC_THRESHOLD are
    returned. Returns [] when nothing clears the threshold or the description
    is empty — the agent then stops early, as it did before this tool existed.
    """
    if not description or not description.strip():
        return []

    listings = [l for l in load_listings() if _passes_filters(l, size, max_price)]
    if not listings:
        return []

    stored = load_listing_embeddings()
    query_vector = embed([description])[0]

    scored = []
    for listing in listings:
        score = _cosine(query_vector, stored[listing["id"]])
        if score >= config.SEMANTIC_THRESHOLD:
            scored.append((score, listing))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {**listing, "similarity": round(score, 4)}
        for score, listing in scored[:config.SEMANTIC_RESULT_LIMIT]
    ]
