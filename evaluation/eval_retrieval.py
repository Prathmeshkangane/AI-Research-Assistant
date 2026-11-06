"""
eval_retrieval.py - measure how good your ArXiv retrieval really is.

  python eval_retrieval.py gen  --n 40      # add test questions (resumable: run again tomorrow if quota ends)
  python eval_retrieval.py eval --k 10 --tag baseline   # semantic vs BM25 vs hybrid (RRF); saves results_baseline.json

Lives in evaluation/. Run from the PROJECT ROOT:  python evaluation/eval_retrieval.py eval --k 10 --tag mytag
Results are written to evaluation/results/.
"""
import argparse, json, os, random, re, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, "..")))     # project root (so `from app import app` works)
RESULTS_DIR = os.path.join(HERE, "results")                    # evaluation/results/

from app import app
from models.paper import Paper
from services import semantic_search as ss          # your module: model, index, paper_ids, semantic_search()

EVAL_MODEL = os.getenv("GEMINI_EVAL_MODEL", "gemini-3.5-flash-lite")   # name suggested by the API itself; change with: set GEMINI_EVAL_MODEL=<name>
BATCH = 5                                                               # papers per Gemini call

# ───────────────────────── hooks into your project ─────────────────────────
def load_papers():
    with app.app_context():
        return [{"id": p.id, "title": p.title, "abstract": p.abstract} for p in Paper.query.all()]

def semantic_search(query: str, k: int):
    """Your REAL end-to-end search (query encoding + FAISS + MySQL fetch)."""
    with app.app_context():
        return [p.id for p in ss.semantic_search(query, top_k=k)]

def latency_breakdown(query: str, k: int = 10):
    t0 = time.perf_counter(); q = ss.encode_query(query)
    t1 = time.perf_counter(); _, idx = ss.index.search(q, k)
    t2 = time.perf_counter()
    with app.app_context():
        ids = [ss.paper_ids[i] for i in idx[0]]
        Paper.query.filter(Paper.id.in_(ids)).all()
    t3 = time.perf_counter()
    return (t1 - t0) * 1000, (t2 - t1) * 1000, (t3 - t2) * 1000

def ask_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel(EVAL_MODEL).generate_content(prompt).text
# ───────────────────────────────────────────────────────────────────────────

PROMPT = """For each research paper below write TWO search queries a researcher might type to find it
WITHOUT having read it. Return ONLY a JSON list, one object per paper:
[{{"id": "<paper id>", "keyword": "...", "paraphrase": "..."}}, ...]

- "keyword": 2-5 words, like a search-engine query (may use the field's normal terms).
- "paraphrase": one natural question, max 20 words, that describes the paper's idea in DIFFERENT words:
  do NOT reuse distinctive words or phrases from the abstract and do not mention the title.

Papers:
{papers}"""

def parse_json_list(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)

def is_quota_error(e):
    s = str(e).lower()
    return "429" in s or "quota" in s or "resourceexhausted" in s or "rate limit" in s

def gen(n, out, seed=42):
    rows = json.load(open(out)) if os.path.exists(out) else []
    for r in rows: r.setdefault("style", "legacy")
    used = {r["paper_id"] for r in rows}
    papers = [p for p in load_papers() if len(p["abstract"]) > 200 and p["id"] not in used]
    random.Random(seed).shuffle(papers)
    papers = papers[:n]
    by_id = {p["id"]: p for p in papers}
    added = 0
    for i in range(0, len(papers), BATCH):
        chunk = papers[i:i + BATCH]
        block = "\n\n".join(f"id: {p['id']}\nabstract: {p['abstract'][:1200]}" for p in chunk)
        try:
            items = parse_json_list(ask_gemini(PROMPT.format(papers=block)))
        except Exception as e:
            if is_quota_error(e):
                print("Gemini quota reached - progress is saved. Run the same command again later "
                      "(free quotas reset daily), or set GEMINI_EVAL_MODEL to another model.")
                break
            if "404" in str(e) or "no longer available" in str(e).lower() or "not found" in str(e).lower():
                print(f"Model '{EVAL_MODEL}' is not available for your key: {str(e)[:200]}\n"
                      "Set another one, e.g.  set GEMINI_EVAL_MODEL=gemini-2.5-flash  (Windows cmd)  and run again.")
                break
            print("skipping a batch:", str(e)[:200]); continue
        for it in items:
            p = by_id.get(str(it.get("id")))
            if not p: continue
            for style in ("keyword", "paraphrase"):
                q = str(it.get(style, "")).strip().strip('"')
                if q:
                    rows.append({"query": q, "paper_id": p["id"], "title": p["title"], "style": style}); added += 1
        json.dump(rows, open(out, "w"), indent=2, ensure_ascii=False)
        time.sleep(2)
    json.dump(rows, open(out, "w"), indent=2, ensure_ascii=False)
    print(f"added {added} queries, {len(rows)} total in {out}. READ THEM and delete bad/ambiguous ones.")

def tok(s): return re.findall(r"[a-z0-9]+", s.lower())

def pct(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]

def score(rank_lists, gold, ks):
    res = {f"Recall@{k}": round(sum(g in r[:k] for r, g in zip(rank_lists, gold)) / len(gold), 3) for k in ks}
    rr = [1 / (r[:max(ks)].index(g) + 1) if g in r[:max(ks)] else 0 for r, g in zip(rank_lists, gold)]   # true MRR@10
    res["MRR@%d" % max(ks)] = round(sum(rr) / len(rr), 3)
    return res

def rrf(*rank_lists, k=60, depth=50, weights=None):
    """Reciprocal Rank Fusion: merges several ranked lists of ids into one (optionally weighted)."""
    weights = weights or [1.0] * len(rank_lists)
    score = {}
    for w, lst in zip(weights, rank_lists):
        for rank, pid in enumerate(lst, start=1):
            score[pid] = score.get(pid, 0) + w / (k + rank)
    return [pid for pid, _ in sorted(score.items(), key=lambda x: -x[1])][:depth]

def evaluate(eval_set, kmax, tag="", w_sem=1.0, w_bm=1.0):
    from rank_bm25 import BM25Okapi
    rows = json.load(open(eval_set))
    for r in rows: r.setdefault("style", "legacy")
    gold = [r["paper_id"] for r in rows]
    papers = load_papers(); ids = [p["id"] for p in papers]; title = {p["id"]: p["title"] for p in papers}
    bm25 = BM25Okapi([tok(p["title"] + " " + p["abstract"]) for p in papers])

    depth = max(kmax, 50)            # deeper lists so hybrid fusion has something to merge
    lat = []
    for r in rows:
        t = time.perf_counter(); semantic_search(r["query"], kmax); lat.append((time.perf_counter() - t) * 1000)
    sem = [list(semantic_search(r["query"], depth)) for r in rows]
    bm = []
    for r in rows:
        sc = bm25.get_scores(tok(r["query"])); top = sorted(range(len(sc)), key=lambda i: -sc[i])[:depth]
        bm.append([ids[i] for i in top])
    hyb = [rrf(sem[i], bm[i], depth=depth, weights=[w_sem, w_bm]) for i in range(len(rows))]

    parts = [latency_breakdown(r["query"], kmax) for r in rows]
    breakdown = {n: {"p50": round(statistics.median(c), 2), "p95": round(pct(list(c), 95), 2)}
                 for n, c in zip(["query_encode_ms", "faiss_search_ms", "db_fetch_ms"], zip(*parts))}
    ks = [k for k in (1, 3, 5, 10) if k <= kmax]

    def by_style(s_filter):
        idx = [i for i, r in enumerate(rows) if s_filter is None or r["style"] == s_filter]
        return {"n": len(idx), "semantic": score([sem[i] for i in idx], [gold[i] for i in idx], ks),
                "bm25_baseline": score([bm[i] for i in idx], [gold[i] for i in idx], ks),
                "hybrid_rrf": score([hyb[i] for i in idx], [gold[i] for i in idx], ks)}
    styles = sorted({r["style"] for r in rows})
    out = {"overall": by_style(None), "by_query_style": {s: by_style(s) for s in styles},
           "end_to_end_latency_ms": {"p50": round(statistics.median(lat), 1), "p95": round(pct(lat, 95), 1)},
           "latency_breakdown": breakdown, "hybrid_weights": {"semantic": w_sem, "bm25": w_bm},
           "note": f"{len(rows)} synthetic queries; model {ss.EMBED_MODEL}; device {ss.model.device} (set CUDA_VISIBLE_DEVICES=-1 for CPU latency)"}
    print(json.dumps(out, indent=2)); os.makedirs(RESULTS_DIR, exist_ok=True); json.dump(out, open(os.path.join(RESULTS_DIR, f"results{'_' + tag if tag else ''}.json"), "w"), indent=2)

    cases = []
    for i, r in enumerate(rows):
        rank = sem[i].index(gold[i]) + 1 if gold[i] in sem[i] else None
        if rank != 1:
            cases.append({"query": r["query"], "style": r["style"], "gold_title": r["title"], "semantic_rank": rank,
                          "bm25_rank": bm[i].index(gold[i]) + 1 if gold[i] in bm[i] else None,
                          "hybrid_rank": hyb[i].index(gold[i]) + 1 if gold[i] in hyb[i] else None,
                          "semantic_top3_titles": [title.get(x, x) for x in sem[i][:3]]})
    json.dump(cases, open(os.path.join(RESULTS_DIR, f"failures{'_' + tag if tag else ''}.json"), "w"), indent=2, ensure_ascii=False)
    print(f"{len(cases)} queries where the right paper was NOT ranked #1 -> evaluation/results/failures{'_' + tag if tag else ''}.json (read these: your error analysis)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["gen", "eval"])
    ap.add_argument("--n", type=int, default=40, help="number of NEW papers to write queries for")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--w_sem", type=float, default=1.0, help="hybrid weight for semantic results")
    ap.add_argument("--w_bm", type=float, default=1.0, help="hybrid weight for BM25 results")
    ap.add_argument("--tag", default="", help="saves results_<tag>.json so you can compare before/after")
    ap.add_argument("--out", default=os.path.join(HERE, "eval_set.json")); ap.add_argument("--eval_set", default=os.path.join(HERE, "eval_set.json"))
    a = ap.parse_args()
    gen(a.n, a.out) if a.cmd == "gen" else evaluate(a.eval_set, a.k, a.tag, a.w_sem, a.w_bm)