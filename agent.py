"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import config
import trace
import re
import time
# from tools import search_listings, suggest_outfit, create_fit_card
# UNIT 4
from tools import suggest_outfit, create_fit_card
from mcp_client import call_tool
# UNIT 9 (capstone): fallback when keyword search returns nothing
from tools import semantic_search
# UNIT 9 improvement: call search_listings directly unless config.USE_MCP_SEARCH
from tools import search_listings

from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "semantic_results": [],      # UNIT 9: what semantic_search returned (only runs if search_results is empty)
        "search_method": None,       # UNIT 9: "keyword", "semantic", or None if nothing matched
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "timings_ms": {},            # UNIT 9: wall-clock ms per stage, for the latency breakdown
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    
    trace.start_trace()
    
    session = new_session(query, wardrobe)

    iteration_count = 1
    #print(f"Check iteration: {iteration_count}")
    trace.check_iterations(iteration_count)

    # Parse max price
    price_match = re.search(
        r"(?:under|max(?:imum)?|up to)\s*\$?\s*(\d+(?:\.\d+)?)",
        query,
        re.IGNORECASE,
    )
    max_price = float(price_match.group(1)) if price_match else None

    # Parse size
    size_match = re.search(
        r"\bsize\s+([A-Za-z0-9/]+)",
        query,
        re.IGNORECASE,
    )
    size = size_match.group(1) if size_match else None

    # Remove size and price phrases to get the description
    description = re.sub(
        r"\bsize\s+[A-Za-z0-9/]+",
        "",
        query,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"(?:under|max(?:imum)?|up to)\s*\$?\s*\d+(?:\.\d+)?",
        "",
        description,
        flags=re.IGNORECASE,
    )

    # Remove common filler phrases
    description = re.sub(
        r"\b(looking for|find me|i want|i need|a|an)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )

    description = " ".join(description.split()).strip(" ,.-")

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # Search for matching listings
    # UNIT 9 improvement: going through MCP starts a new mcp_server.py process
    # on every call — measured at 3.8–9.7 s on Render, vs ~0.4 ms direct. Same
    # function, same arguments, same return value; only the transport changes.
    _t = time.perf_counter()
    try:
        if config.USE_MCP_SEARCH:
            session["search_results"] = call_tool("search_listings", {
                "description": session["parsed"]["description"],
                "size": session["parsed"]["size"],
                "max_price": session["parsed"]["max_price"],
            })
        else:
            session["search_results"] = search_listings(
                session["parsed"]["description"],
                session["parsed"]["size"],
                session["parsed"]["max_price"],
            )
    finally:
        stage = "search_listings_mcp" if config.USE_MCP_SEARCH else "search_listings"
        session["timings_ms"][stage] = round((time.perf_counter() - _t) * 1000, 1)
    trace.step(
        "search_listings (via MCP)" if config.USE_MCP_SEARCH else "search_listings",
        inputs=session["parsed"],
        returned=session["search_results"],
    )

    if session["search_results"]:
        session["search_method"] = "keyword"
        session["selected_item"] = session["search_results"][0]
    else:
        # UNIT 9: keyword search found nothing — try matching by meaning
        try:
            _t = time.perf_counter()
            try:
                session["semantic_results"] = semantic_search(
                    session["parsed"]["description"],
                    session["parsed"]["size"],
                    session["parsed"]["max_price"],
                )
            finally:
                session["timings_ms"]["semantic_search"] = round((time.perf_counter() - _t) * 1000, 1)
        except ModelUnavailable:
            # Don't disguise an API failure as "no match" — say what happened
            session["error"] = (
                "No keyword matches, and semantic search couldn't reach the "
                "embedding model. Check your API key or connection."
            )
            return session
        trace.step(
            "semantic_search",
            inputs=session["parsed"],
            returned=session["semantic_results"],
        )

        # Required branch: stop if both searches returned nothing
        if not session["semantic_results"]:
            session["error"] = (
                "No matching listings were found. Try changing the description, "
                "size, or increasing the maximum price."
            )
            return session

        session["search_method"] = "semantic"
        session["selected_item"] = session["semantic_results"][0]

    # Next iteration
    iteration_count+=1
    #print(f"Checking iteration: {iteration_count}")
    trace.check_iterations(iteration_count)

    try:
        _t = time.perf_counter()
        try:
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"],
                session["wardrobe"],
            )
        finally:
            session["timings_ms"]["suggest_outfit"] = round((time.perf_counter() - _t) * 1000, 1)
        trace.step(
            "suggest_outfit",
            inputs={
                "new_item": session["selected_item"],
                "wardrobe": session["wardrobe"],
            },
            returned=session["outfit_suggestion"],
        )

        iteration_count += 1
        trace.check_iterations(iteration_count)

        _t = time.perf_counter()
        try:
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"],
                session["selected_item"],
            )
        finally:
            session["timings_ms"]["create_fit_card"] = round((time.perf_counter() - _t) * 1000, 1)
        trace.step(
            "create_fit_card",
            inputs={
                "outfit": session["outfit_suggestion"],
                "new_item": session["selected_item"],
            },
            returned=session["fit_card"],
        )

    except ModelUnavailable:
        session["error"] = (
            "The model couldn't be reached. Check your API key or internet "
            "connection, then try again."
        )

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
