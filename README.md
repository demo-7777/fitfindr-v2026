# FitFindr

FitFindr is a Python-based AI agent that helps users discover clothing items and generate personalized outfit recommendations based on their preferences and existing wardrobe.

The application uses a multi step workflow to search product listings, select a matching item, suggest an outfit, and generate a short description. Product search is integrated through Model Context Protocol (MCP).

### Key Features

- **Multi-step agent workflow:** Coordinates product search, outfit generation, and description creation.
- **MCP tool integration:** Executes product searches through an MCP server.
- **Conditional execution:** Stops early and returns a helpful message when no matching products are found.
- **Preference-based filtering:** Matches product descriptions, sizes, and price limits.
- **Evaluation framework:** Tests successful execution, unsuccessful searches, tool data flow, output consistency, and price constraints.

### Results

- Met all five evaluation criteria across five repeated runs before and after the search-filtering improvement.
- Reduced results for the vintage graphic tee under $30 query from 10 to 6 while preserving the correct top recommendation.
- Verified that unsuccessful searches stop without executing unnecessary downstream tools.

### My Contributions

This project was developed as part of the CodePath Applied AI program using a provided starter repository.

- Implemented the three core tools for product search, wardrobe-based outfit recommendations, and outfit description generation.
- Designed and implemented the agent's planning loop to coordinate tool execution, maintain session state, and handle unsuccessful searches through conditional termination.
- Integrated `search_listings` with the Model Context Protocol (MCP) server, replacing direct function calls with MCP-based execution.
- Defined five acceptance criteria and used the provided evaluation framework to test successful execution, early termination, tool data flow, output consistency, and price constraints.
- Refined keyword-based search filtering, reducing results from 10 to 6 in a documented test case while preserving the correct top recommendation.

### Getting Started

See [RUNNING.md](RUNNING.md) for installation, configuration, and execution instructions.

---

## Tool Inventory


### `search_listings`

- **What it does:** Searches the items in `listings.json` for listings matching the user's requested description, size, and maximum price.
- **Inputs:** `description` (string), `size` (string), `max_price` (float).
- **Returns:** A list of matching listing dictionaries containing fields such as `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.
- **When it has nothing:** Returns an empty list `[]` when no listings match the search.

### `suggest_outfit`

- **What it does:** Uses the new listing item and the user's wardrobe to suggest an outfit combination.
- **Inputs:** `new_item` (dict), `wardrobe` (dict containing a list of item dictionaries).
- **Returns:** A string containing the `new_item` and selected compatible items from the user's wardrobe.
- **When it has nothing:** If the wardrobe contains no items, returns a string containing general outfit advice for styling the new item.

### `create_fit_card`

- **What it does:** Writes a short caption describing the appeal of an outfit after the addition of the new item.
- **Inputs:** `outfit` (string), `new_item` (dict).
- **Returns:** A string containing a short caption describing the outfit and how the new item complements it.
- **When it has nothing:** Returns a string with a message explaining that no outfit was provided.

---

## Planning Loop


**Branch rule:** If `search_listings` returns an empty list, put a message in the session and stop. Otherwise, take the first result and continue to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Using regex, the size and max_price are extracted from the user's query, and the remaining text is cleaned into the description.

**What moves through the session:** The parsed query is stored in parsed and passed to search_listings. Its results are stored in search_results, the best result becomes selected_item, the generated outfit is stored in outfit_suggestion, and the final caption is stored in fit_card.

---

## Sample Run


**One full query**

```
$ python agent.py

=== A query the data can match ===
found: Y2K Baby Tee — Butterfly Print — $18.0 on depop

outfit:
Top: Y2K Baby Tee — Butterfly Print (New Item)
Bottoms: Baggy straight-leg jeans, dark wash
Shoes: Chunky white sneakers
Outerwear: Vintage black denim jacket
Accessories: Black crossbody bag

Why it works:
This outfit plays with a classic Y2K silhouette by pairing the fitted, graphic baby tee with baggy straight-leg jeans for a balanced proportion. The chunky white sneakers tie into the playful, nostalgic aesthetic, while the vintage black denim jacket and black crossbody bag add a cool, effortless finish without distracting from the tee's butterfly print.

fit card:
Channeling major 2000s energy with this fitted butterfly baby tee paired with dark baggy denim and chunky sneakers. Topped off with a vintage black jacket, this fit is serving ultimate effortless off-duty vibes. Snag the Y2K Butterfly Baby Tee over on my Depop for just $18.00 before it’s gone!

```

**The three tools, tested one at a time**

```text
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

```text
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"

**Outfit Suggestion:**

* **New Item:** Vintage Levi's 501 Jeans (Medium Wash)
* **Top:** White ribbed tank top
* **Outerwear:** Vintage black denim jacket
* **Shoes:** Chunky white sneakers
* **Accessories:** Black crossbody bag

**Why it works:**
The medium-wash vintage Levi's provide a classic, relaxed base that pairs effortlessly with the fitted white tank top for a timeless casual look. Layering the vintage black denim jacket adds a cool, cohesive texture that complements the retro vibe of the jeans, while the chunky white sneakers and black crossbody bag tie the streetwear elements of the outfit together.
```

```text
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"

Nothing beats the timeless combo of your favorite white sneakers and the ultimate off-duty uniform. These Vintage Levi's 501 Jeans in medium wash nail that effortless, perfectly broken-in 90s aesthetic. Grab them on depop for just $38.00 before I change my mind and keep them.
```

---

## How I Used AI


**Moment 1**

- *What I asked for:* I gave AI my rough algorithm for search_listings and asked it to help implement the function based on the requirements in tools.py.
- *What came back:* It produced code that loads the listings, filters by price and size, scores listings using keyword matches, sorts them by score, and returns the results.
- *What I changed:* I tested the function myself using both a matching query and a query designed to return nothing. I verified that matching searches returned listing dictionaries and that no matches returned [].

**Moment 2**

- *What I asked for:* I gave AI my planned flow for run_agent and asked for help implementing the planning loop and session state.
- *What came back:* It produced a loop that parses the query, calls search_listings, stores the selected item in the session, calls suggest_outfit, and then calls create_fit_card. It also included the branch that stops when the search returns an empty list.
- *What I changed:* I added and tested the iteration checks using trace.check_iterations(). I ran both example paths and verified that the successful path reached all three tools while the no-results path stopped after the search and left fit_card as None.

**Moment 3**

- *What I asked for:* I asked AI to help identify a measurable improvement after reviewing my before evaluation results.
- *What came back:* It identified that `search_listings` was accepting listings with only one matching keyword and suggested requiring at least two matches for multi-word searches.
- *What I changed:* I applied the change, ran the after evaluation myself, and verified that all five criteria still passed while the test search decreased from 10 results to 6 more relevant results.


---

## Run Log — Before


| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops early | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected listing passed to outfit tool | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card stays consistent with item | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Maximum price respected | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

**Criterion 1 — Matching query completes all three tools**  
Tested: `agent.py::run_agent`

```text
selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
search_results: 10

[1] search_listings (via MCP)
[2] suggest_outfit
[3] create_fit_card

Fit card:
Channeling major early 2000s energy with this effortless streetwear fit, pairing baggy dark wash denim with chunky kicks. The star of the look is this brand new Y2K butterfly baby tee, which is giving all the nostalgic vibes. Snag this cute new piece on Depop for just $18.00 before it’s gone!
```

**Criterion 2 — Impossible query stops early**  
Tested: `agent.py::run_agent`

```text
stopped early: yes — No matching listings were found. Try changing the description, size, or increasing the maximum price.
selected_item: (none)
search_results: 0

[1] search_listings (via MCP)
      out: [] (empty)
```

**Criterion 3 — Selected listing passed to outfit tool**  
Tested: `agent.py::run_agent`

```text
selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)

[1] search_listings (via MCP)
      out: 10 items: Y2K Baby Tee — Butterfly Print, ...

[2] suggest_outfit
      in: dict with keys: new_item, wardrobe

Outfit Suggestion:
Top: Y2K Baby Tee — Butterfly Print (New item)
```

**Criterion 4 — Fit card stays consistent with item**  
Tested: `tools.py::create_fit_card`

```text
selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)

Fit card:
Embracing full early-2000s streetwear energy with this baggy denim and cropped hoodie combo. The star of the fit is this new Y2K butterfly print baby tee, which brings total retro nostalgia. Grab it on my depop now for just $18.00 before it’s gone!
```

**Criterion 5 — Maximum price respected**  
Tested: `tools.py::search_listings`

```text
Query: vintage graphic tee under $20
selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
search_results: 8
```

---

## Verdicts and Diagnoses


| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes | 4/5 | MET (5/5) | All five tries completed all three tool calls and returned a fit card. |
| 2 | Impossible query stops early | 5/5 | MET (5/5) | All five tries stopped after the empty search and returned a useful message. |
| 3 | Selected listing passed to outfit tool | 5/5 | MET (5/5) | All five tries passed the selected listing into `suggest_outfit`. |
| 4 | Fit card stays consistent with item | 4/5 | MET (5/5) | All five fit cards stayed consistent with the selected item's fields. |
| 5 | Maximum price respected | 5/5 | MET (5/5) | All five tries selected an item at or below the requested maximum price. |

**Diagnoses**

All five criteria met their original targets, so there were no failed criteria requiring a failure diagnosis. The 5/5 targets were appropriate for deterministic behavior. The 4/5 targets were reasonable for criteria involving model-generated output because the wording can vary between runs.

One weakness shown by the tests is search relevance. The search can return listings that only loosely match the full description. I will use this as the basis for the one improvement in the next milestone.


---

## Loop Trace

```text
[1] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[2] suggest_outfit
      in:  dict with keys: new_item, wardrobe
      out: **Outfit Suggestion:**  * **Top:** Y2K Baby Tee — Butterfly Print (New Item) * **Bottoms:** Baggy straight-leg…
[3] create_fit_card
      in:  dict with keys: outfit, new_item
      out: Channeling major 2000s energy with this fitted butterfly baby tee paired with dark baggy denim and chunky snea…
```

**Happy path**

```
[1] search_listings (via MCP)
      in: dict with keys: description, size, max_price
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[2] suggest_outfit
      in: dict with keys: new_item, wardrobe
[3] create_fit_card
      in: dict with keys: outfit, new_item
```

**Empty search**

```
[1] search_listings (via MCP)
      in: dict with keys: description, size, max_price
      out: [] (empty)
```

**On the MCP move:** I moved `search_listings` from a direct function call to the MCP server. `agent.py` now calls it through `mcp_client.call_tool`. The agent's normal behavior stayed the same after the move, and the trace confirms that `search_listings` runs through MCP before the other two tools. <!-- what changed in your code, and whether anything behaved differently afterwards. If the rewire didn't work, say exactly where it broke — the error text and the last thing that worked. That earns the point in full. -->



---

## The Improvement


**What I changed:** I changed search_listings so multi-word searches require at least two keyword matches instead of accepting a listing when only one keyword matches.

**Which failure it was meant to fix:** All five criteria passed, but the before run showed weak search relevance. The query vintage graphic tee under $30 returned 10 results, including loosely related listings. The change was meant to reduce those weaker matches.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops early | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected listing passed to outfit tool | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card stays consistent with item | 4/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Maximum price respected | 5/5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help, and how do I know:** Yes. All five criteria continued to meet their targets, while the `vintage graphic tee under $30` search decreased from 10 results before the change to 6 results after the change. The same correct Y2K Baby Tee remained the top selected item, so the change reduced loosely related results without breaking the tested agent behavior.



---

## Limitations and Future Improvements

All five criteria still meet their targets after the improvement, so there are no remaining failed criteria to fix.

The search is more selective than before, but keyword matching is still simple and may return some loosely related listings. A future improvement could use better relevance scoring, but I stopped here because unit 4 requires only one measured improvement.

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**

---

## Capstone

**What This Extends**

This extends FitFindr, the Unit 4 agent that searches secondhand listings, suggests an outfit from the user's wardrobe, and writes a fit card. Two things are new. First, a fourth tool, `semantic_search`, that runs only when the keyword search in `search_listings` returns nothing: it embeds the query, compares it to embeddings of the listings, and returns the closest match by meaning. Second, the system now runs as a hosted web service (`serve.py` on Render) with structured logging of every request.

**The Shape**

Shape C — extend one capability — on run path A (hosted). FitFindr's search only matches exact keywords, so a query that uses different words than the listings returns nothing and the agent stops early. In a test of 14 queries against the 40 listings, 6 returned zero results; "retro t-shirt" found nothing because no listing contains "retro" or "t-shirt", while 29 of the 40 listings contain "vintage" and 5 contain "tee". `semantic_search` fills that gap: when keyword search comes back empty, it applies the same price and size filters, embeds the query, scores each remaining listing by cosine similarity against cached listing embeddings, and returns the top match if its score clears a similarity threshold. Below the threshold it still returns nothing, so impossible queries continue to stop early.

Out of scope:
- I'm not changing the keyword logic in `search_listings`; the fallback only runs when it returns nothing.
- I'm not reranking non empty keyword results; a reranker has little to choose between when most queries return 0–6 listings.
- I'm not expanding the listings dataset or building a frontend; `/ask` stays a JSON endpoint.

Stretch (declared before building):
- Both run paths — hosted on Render and documented as a local run, with a note on what differed.
- A latency breakdown — measured time per stage (keyword search, semantic search, outfit, fit card) for one run.

**Running It**

Path A (hosted): https://fitfindr-v2026.onrender.com on Render's free tier, started with `gunicorn serve:app` (worker timeout set to 120 s in `gunicorn.conf.py`). Path B (local) is also documented, for the "both run paths" stretch. The URL, routes, Render settings, Python version, dependencies and the local start command are all in [RUNNING.md](RUNNING.md). The local path was tested from a fresh clone of this repo and worked without changes.

**Instrumentation**

Every `POST /ask` writes one JSON record, including rejected (400) and crashed (500) requests. Records go to `logs/requests.jsonl` and to stdout, because Render's dashboard keeps stdout after the disk is wiped. `GET /logs?n=N` reads the file back. Code: `serve.py`, functions `_log_record()` and `_write_log()`.

| Field | What it holds |
|---|---|
| `ts` | UTC timestamp when the request finished |
| `request_id` | Short id, also returned in the response |
| `status` | HTTP status: 200, 400 or 500 |
| `query` | What came in, exactly as sent |
| `search_method` | `keyword`, `semantic` (the new fallback), or `null` if nothing matched |
| `keyword_results` / `semantic_results` | How many listings each search returned |
| `selected_id` / `selected_title` / `selected_price` | What came out: the listing the agent chose |
| `similarity` | Cosine score of the chosen listing (semantic route only) |
| `fit_card_chars` | Length of the fit card (0 = none was made) |
| `error` | The run's error message, or `null` |
| `duration_ms` | Time from request received to response built |
| `model_calls` / `cache_hits` | Gemini calls made by this run / answers served from cache (should be 0 with `AI201_CACHE=0`) |
| `prompt_tokens` / `output_tokens` | Tokens the service reported for this run (embedding calls report none) |

The 12 entries below came from the Render deployment on 2026-11-17, copied from `GET /logs?n=12` (saved in `results/capstone_cost_run_raw.json`). They are 10 measured runs (5 on the keyword route, 3 on the semantic route, 2 with no match) and 2 rejected requests (empty query; body not JSON):

```jsonl
{"ts": "2026-11-17T00:13:05.555+00:00", "request_id": "59db3f7d", "route": "/ask", "status": 200, "query": "vintage graphic tee under $30", "search_method": "keyword", "keyword_results": 6, "semantic_results": 0, "selected_id": "lst_002", "selected_title": "Y2K Baby Tee — Butterfly Print", "selected_price": 18.0, "similarity": null, "fit_card_chars": 253, "error": null, "duration_ms": 23851.8, "model_calls": 2, "cache_hits": 0, "prompt_tokens": 652, "output_tokens": 191}
{"ts": "2026-11-17T00:13:23.786+00:00", "request_id": "c71dc421", "route": "/ask", "status": 200, "query": "denim jacket under $50", "search_method": "keyword", "keyword_results": 1, "semantic_results": 0, "selected_id": "lst_007", "selected_title": "Denim Jacket — Light Wash, Cropped", "selected_price": 42.0, "similarity": null, "fit_card_chars": 271, "error": null, "duration_ms": 18089.3, "model_calls": 2, "cache_hits": 0, "prompt_tokens": 652, "output_tokens": 197}
{"ts": "2026-11-17T00:13:35.114+00:00", "request_id": "4a44a320", "route": "/ask", "status": 200, "query": "graphic tee", "search_method": "keyword", "keyword_results": 4, "semantic_results": 0, "selected_id": "lst_002", "selected_title": "Y2K Baby Tee — Butterfly Print", "selected_price": 18.0, "similarity": null, "fit_card_chars": 275, "error": null, "duration_ms": 11173.8, "model_calls": 2, "cache_hits": 0, "prompt_tokens": 663, "output_tokens": 213}
{"ts": "2026-11-17T00:13:45.359+00:00", "request_id": "fe206b64", "route": "/ask", "status": 200, "query": "vintage denim", "search_method": "keyword", "keyword_results": 5, "semantic_results": 0, "selected_id": "lst_001", "selected_title": "Vintage Levi's 501 Jeans — Medium Wash", "selected_price": 38.0, "similarity": null, "fit_card_chars": 273, "error": null, "duration_ms": 10079.3, "model_calls": 2, "cache_hits": 0, "prompt_tokens": 665, "output_tokens": 214}
{"ts": "2026-11-17T00:14:01.733+00:00", "request_id": "d1e2be8a", "route": "/ask", "status": 200, "query": "leather", "search_method": "keyword", "keyword_results": 4, "semantic_results": 0, "selected_id": "lst_009", "selected_title": "Platform Mary Janes — Black Patent", "selected_price": 55.0, "similarity": null, "fit_card_chars": 299, "error": null, "duration_ms": 16215.9, "model_calls": 2, "cache_hits": 0, "prompt_tokens": 628, "output_tokens": 181}
{"ts": "2026-11-17T00:14:21.896+00:00", "request_id": "62540404", "route": "/ask", "status": 200, "query": "retro t-shirt", "search_method": "semantic", "keyword_results": 0, "semantic_results": 2, "selected_id": "lst_006", "selected_title": "Graphic Tee — 2003 Tour Bootleg Style", "selected_price": 24.0, "similarity": 0.6175, "fit_card_chars": 312, "error": null, "duration_ms": 20035.5, "model_calls": 3, "cache_hits": 0, "prompt_tokens": 673, "output_tokens": 221}
{"ts": "2026-11-17T00:14:40.834+00:00", "request_id": "77b069de", "route": "/ask", "status": 200, "query": "oversized hoodie", "search_method": "semantic", "keyword_results": 0, "semantic_results": 3, "selected_id": "lst_027", "selected_title": "Oversized College Crewneck — Faded Red", "selected_price": 21.0, "similarity": 0.6546, "fit_card_chars": 294, "error": null, "duration_ms": 18707.0, "model_calls": 3, "cache_hits": 0, "prompt_tokens": 634, "output_tokens": 178}
{"ts": "2026-11-17T00:14:54.918+00:00", "request_id": "9e097a62", "route": "/ask", "status": 200, "query": "sweater", "search_method": "semantic", "keyword_results": 0, "semantic_results": 1, "selected_id": "lst_008", "selected_title": "Knit Cardigan — Chunky Brown", "selected_price": 35.0, "similarity": 0.6083, "fit_card_chars": 241, "error": null, "duration_ms": 13881.9, "model_calls": 3, "cache_hits": 0, "prompt_tokens": 646, "output_tokens": 189}
{"ts": "2026-11-17T00:14:59.398+00:00", "request_id": "35906186", "route": "/ask", "status": 200, "query": "car tires", "search_method": null, "keyword_results": 0, "semantic_results": 0, "selected_id": null, "selected_title": null, "selected_price": null, "similarity": null, "fit_card_chars": 0, "error": "No matching listings were found. Try changing the description, size, or increasing the maximum price.", "duration_ms": 4267.2, "model_calls": 1, "cache_hits": 0, "prompt_tokens": 0, "output_tokens": 0}
{"ts": "2026-11-17T00:15:03.717+00:00", "request_id": "e5275fb8", "route": "/ask", "status": 200, "query": "designer ballgown size XXS under $5", "search_method": null, "keyword_results": 0, "semantic_results": 0, "selected_id": null, "selected_title": null, "selected_price": null, "similarity": null, "fit_card_chars": 0, "error": "No matching listings were found. Try changing the description, size, or increasing the maximum price.", "duration_ms": 4175.0, "model_calls": 0, "cache_hits": 0, "prompt_tokens": 0, "output_tokens": 0}
{"ts": "2026-11-17T00:15:28.943+00:00", "request_id": "6163a19c", "route": "/ask", "status": 400, "query": "", "search_method": null, "keyword_results": 0, "semantic_results": 0, "selected_id": null, "selected_title": null, "selected_price": null, "similarity": null, "fit_card_chars": 0, "error": "Send JSON with a 'query' field, e.g. {\"query\": \"vintage graphic tee under $30\"}", "duration_ms": 0.1, "model_calls": 0, "cache_hits": 0, "prompt_tokens": 0, "output_tokens": 0}
{"ts": "2026-11-17T00:15:29.072+00:00", "request_id": "cd5c8354", "route": "/ask", "status": 400, "query": null, "search_method": null, "keyword_results": 0, "semantic_results": 0, "selected_id": null, "selected_title": null, "selected_price": null, "similarity": null, "fit_card_chars": 0, "error": "Send JSON with a 'query' field, e.g. {\"query\": \"vintage graphic tee under $30\"}", "duration_ms": 0.1, "model_calls": 0, "cache_hits": 0, "prompt_tokens": 0, "output_tokens": 0}
```

A failure the log could not record: before the timeout fix, the first `/ask` for "denim jacket under $50" (2026-11-17, about 00:04 UTC) returned HTTP 500 after 30.8 s, and no log entry exists for it. Gunicorn's default 30 s worker timeout killed the worker mid-request, before `_write_log()` ran. The fix was `gunicorn.conf.py` (`timeout = 120`); none of the runs since then have hit it.

**What It Costs**

Measured from the 10 runs above, on Render with the cache off. Each number comes from the run's own log record: `model_calls`, `prompt_tokens` and `output_tokens` are differences in `generate.py`'s counters taken before and after the run, and `duration_ms` is wall-clock time in `serve.py`.

| Route | Runs | Mean time | Model calls | Tokens (prompt + output) |
|---|---|---|---|---|
| All | 10 | 14.0 s | 2.0 | 680 (521 + 158) |
| Keyword | 5 | 15.9 s | 2 | 851 |
| Semantic | 3 | 17.5 s | 3 | 847, plus one embedding call that reports no tokens |
| No match | 2 | 4.2 s | 0–1 | 0 |

Per run: about 2 model calls, 680 tokens and 14 seconds of server time. Actual spend is $0 because the key is on Gemini's free tier.

A hundred runs a day, using the averages above:
- Model calls: 100 × 2.0 = 200 per day
- Tokens: 100 × 680 = 68,000 per day
- Server time: 100 × 14.0 s = 1,400 s per day, about 23 minutes. `serve.py` handles one request at a time, so that is 23 minutes of a single worker being busy.

Limit of this measurement: embedding calls report no token counts, so the semantic route costs slightly more than the table shows.
