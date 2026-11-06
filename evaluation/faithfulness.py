"""
faithfulness.py - measure whether the assistant's answers are supported by the papers it cites.

Lives in evaluation/. Run from the PROJECT ROOT, one step at a time:

  python evaluation/faithfulness.py sims     # 1) no Gemini calls: how similar are on-topic vs off-topic questions? (tunes the threshold)
  python evaluation/faithfulness.py run      # 2) asks the real RAG pipeline every question (resumable if Gemini quota ends)
  python evaluation/faithfulness.py sheet    # 3) writes evaluation/results/faith_review.html -> you label each answer in the browser
  python evaluation/faithfulness.py score    # 4) turns your labels into numbers

Questions: 30 on-topic questions are taken from your eval_set.json (paraphrase style) + 10 off-topic ones below.
Edit evaluation/faith_questions.json after step 1 if you want to remove or add questions.
"""
import argparse, json, math, os, random, statistics, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, "..")))
RESULTS = os.path.join(HERE, "results")
Q_FILE = os.path.join(HERE, "faith_questions.json")
ANS_FILE = os.path.join(RESULTS, "faith_answers.json")
LABEL_FILE = os.path.join(RESULTS, "faith_labels.json")
SIMS_FILE = os.path.join(RESULTS, "faith_sims.json")
SHEET_FILE = os.path.join(RESULTS, "faith_review.html")

OFF_TOPIC = [
    "What is a good recipe for butter chicken?", "Who won the FIFA World Cup in 2022?",
    "How do I fix a leaking kitchen tap?", "What will the weather be like in Mumbai tomorrow?",
    "Which smartphone should I buy under 20,000 rupees?", "Write me a poem about the monsoon.",
    "How do I invest in mutual funds as a beginner?", "What is the best way to learn the guitar?",
    "Can you recommend a good movie for the weekend?", "How do I prepare for a driving licence test?",
]
LABELS = {
    "on_topic": [("supported", "Supported: every claim is backed by the sources and the [n] citations are right"),
                 ("partial", "Partly supported: some claim is not in the sources, or a citation is wrong"),
                 ("unsupported", "Unsupported: mostly not backed by the sources / made up"),
                 ("false_refusal", "False refusal: says there is not enough information although the sources do answer it")],
    "off_topic": [("correct_refusal", "Correct: it declines / says the papers do not cover this"),
                  ("answered_anyway", "Wrong: it answers the question anyway")],
}


def load_app():
    from app import app
    from services import semantic_search as ss
    return app, ss


def build_questions():
    if os.path.exists(Q_FILE):
        return json.load(open(Q_FILE, encoding="utf-8"))
    rows = [r for r in json.load(open(os.path.join(HERE, "eval_set.json"), encoding="utf-8")) if r.get("style") == "paraphrase"]
    random.Random(7).shuffle(rows)
    qs = [{"id": f"on{i+1:02d}", "group": "on_topic", "question": r["query"]} for i, r in enumerate(rows[:30])]
    qs += [{"id": f"off{i+1:02d}", "group": "off_topic", "question": q} for i, q in enumerate(OFF_TOPIC)]
    json.dump(qs, open(Q_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"wrote {len(qs)} questions to {Q_FILE} (read the on-topic ones; delete any that are too broad)")
    return qs


def save(path, obj):
    os.makedirs(RESULTS, exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def max_similarity(app, ss, question):
    with app.app_context():
        hits = ss.semantic_search(question, top_k=5, return_scores=True)
    return (1 - min(d for _, d in hits) / 2) if hits else 0.0     # embeddings are normalised: cosine = 1 - L2/2


def cmd_sims():
    app, ss = load_app(); qs = build_questions(); out = []
    for q in qs:
        out.append({**q, "max_similarity": round(max_similarity(app, ss, q["question"]), 4)})
    save(SIMS_FILE, out)
    on = [o["max_similarity"] for o in out if o["group"] == "on_topic"]
    off = [o["max_similarity"] for o in out if o["group"] == "off_topic"]
    print(f"\non-topic  : min {min(on):.3f}  median {statistics.median(on):.3f}  max {max(on):.3f}   (n={len(on)})")
    print(f"off-topic : min {min(off):.3f}  median {statistics.median(off):.3f}  max {max(off):.3f}   (n={len(off)})")
    if max(off) < min(on):
        print(f"\nThe groups separate cleanly. Suggested RAG_MIN_SIMILARITY = {(max(off) + min(on)) / 2:.3f}")
    else:
        thr = sorted(on)[max(0, int(0.1 * len(on)) - 1)]          # 10th percentile of on-topic similarities
        leak = sum(1 for x in off if x >= thr)
        print(f"\nThe groups overlap. A cautious choice is RAG_MIN_SIMILARITY = {thr:.3f}: it keeps ~90% of on-topic questions, "
              f"and {leak} of {len(off)} off-topic questions would still reach the model (the prompt must make it decline).")
    print("Put the number you choose in .env as RAG_MIN_SIMILARITY=..., then run the 'run' step.")


def cmd_run(args):
    app, ss = load_app()
    from services import rag_service as rag
    from services.llm import QUOTA_EXCEEDED, LLM_UNAVAILABLE
    qs = build_questions()
    done = {a["id"]: a for a in (json.load(open(ANS_FILE, encoding="utf-8")) if os.path.exists(ANS_FILE) else [])}
    print(f"threshold in use: RAG_MIN_SIMILARITY = {rag.MIN_SIMILARITY}   (model: {os.getenv('GEMINI_MODEL', 'default')})")
    for q in qs:
        if q["id"] in done and done[q["id"]]["answer"] not in (QUOTA_EXCEEDED, LLM_UNAVAILABLE):
            continue
        sim = max_similarity(app, ss, q["question"])
        with app.app_context():
            answer, papers = rag.answer_question(q["question"])
            sources = [{"id": p.id, "title": " ".join(p.title.split()), "abstract": " ".join(p.abstract.split())} for p in papers]
        if answer == QUOTA_EXCEEDED:
            print("Gemini quota reached - progress is saved. Run the same command again later, or set GEMINI_MODEL to another model.")
            break
        done[q["id"]] = {**q, "answer": answer, "sources": sources, "max_similarity": round(sim, 4),
                         "skipped_llm": answer == rag.NO_RELEVANT_PAPERS, "threshold": rag.MIN_SIMILARITY}
        save(ANS_FILE, list(done.values()))
        print(f"[{len(done):02d}/{len(qs)}] {q['id']}  sim={sim:.2f}  {answer[:70]!r}")
        time.sleep(1.5)
    print(f"\n{len(done)}/{len(qs)} answered. Next: python evaluation/faithfulness.py sheet")


SHEET = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Faithfulness review</title>
<style>
body{font:15px/1.55 system-ui,sans-serif;background:#0f1115;color:#e6e8ee;max-width:900px;margin:0 auto;padding:24px}
h1{font-size:22px} .bar{position:sticky;top:0;background:#0f1115;padding:12px 0;border-bottom:1px solid #2a2e38;display:flex;gap:14px;align-items:center;z-index:5}
.card{border:1px solid #2a2e38;border-radius:12px;padding:18px;margin:18px 0;background:#151821}
.card.done{border-color:#3f6f4f} .tag{font:12px monospace;color:#e8b563} .q{font-size:18px;margin:6px 0 12px}
.ans{white-space:pre-wrap;background:#0f1115;border:1px solid #2a2e38;border-radius:8px;padding:12px;margin:8px 0}
details{margin:6px 0} summary{cursor:pointer;color:#9aa3b5} .abs{color:#b6bac6;font-size:13.5px;margin:6px 0 10px 12px}
label{display:block;margin:5px 0;cursor:pointer} input[type=text]{width:100%;padding:7px;background:#0f1115;border:1px solid #2a2e38;color:#e6e8ee;border-radius:6px;margin-top:8px}
button{background:#e8b563;color:#1a1306;border:0;border-radius:8px;padding:9px 16px;font-weight:600;cursor:pointer}
.warn{color:#ef9a9f;font-size:13px}
</style></head><body>
<h1>Answer faithfulness review</h1>
<p>For each answer, open the sources and check the claims against the abstracts. Be strict: if you cannot find a claim in the sources, it is not supported. Your choices are saved in this browser automatically.</p>
<div class="bar"><span id="prog"></span><button id="dl">Download labels (faith_labels.json)</button></div>
<div id="items"></div>
<script>
const DATA=__DATA__, LABELS=__LABELS__, KEY="faith_labels_v1";
let saved=JSON.parse(localStorage.getItem(KEY)||"{}");
const root=document.getElementById("items");
function el(t,c,x){const e=document.createElement(t); if(c) e.className=c; if(x!==undefined) e.textContent=x; return e;}
DATA.forEach(d=>{
  const card=el("div","card"); card.id=d.id;
  card.appendChild(el("div","tag",d.id+" · "+d.group.replace("_","-")+" · max similarity "+d.max_similarity+(d.skipped_llm?" · LLM skipped (below threshold)":"")));
  card.appendChild(el("div","q",d.question));
  card.appendChild(el("div","ans",d.answer));
  if(d.sources.length){
    const det=el("details"); det.appendChild(el("summary","","Sources ("+d.sources.length+") - open to check the claims"));
    d.sources.forEach((s,i)=>{det.appendChild(el("div","",(i+1)+". "+s.title+"  [arXiv:"+s.id+"]")); det.appendChild(el("div","abs",s.abstract));});
    card.appendChild(det);
  }
  (LABELS[d.group]||[]).forEach(([val,text])=>{
    const l=el("label"); const r=document.createElement("input"); r.type="radio"; r.name=d.id; r.value=val;
    if((saved[d.id]||{}).label===val) r.checked=true;
    r.addEventListener("change",()=>{saved[d.id]={label:val,note:note.value}; persist();});
    l.appendChild(r); l.appendChild(document.createTextNode(" "+text)); card.appendChild(l);
  });
  const note=el("input"); note.type="text"; note.placeholder="optional note (what was wrong?)"; note.value=(saved[d.id]||{}).note||"";
  note.addEventListener("input",()=>{ if(saved[d.id]){saved[d.id].note=note.value; persist();}});
  card.appendChild(note); root.appendChild(card);
});
function persist(){localStorage.setItem(KEY,JSON.stringify(saved)); progress();}
function progress(){const n=DATA.filter(d=>saved[d.id]&&saved[d.id].label).length;
  document.getElementById("prog").textContent=n+" / "+DATA.length+" labelled";
  DATA.forEach(d=>document.getElementById(d.id).classList.toggle("done",!!(saved[d.id]&&saved[d.id].label)));}
function exportLabels(){const blob=new Blob([JSON.stringify(saved,null,2)],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download="faith_labels.json"; a.click();}
document.getElementById("dl").addEventListener("click",exportLabels); progress();
</script></body></html>"""


def cmd_sheet():
    answers = json.load(open(ANS_FILE, encoding="utf-8"))
    html = SHEET.replace("__DATA__", json.dumps(answers, ensure_ascii=False).replace("</", "<\\/")) \
                .replace("__LABELS__", json.dumps(LABELS))
    open(SHEET_FILE, "w", encoding="utf-8").write(html)
    print(f"Open this file in your browser and label every answer:\n  {SHEET_FILE}\n"
          f"When finished click 'Download labels' and move faith_labels.json into {RESULTS}\\\nThen run:  python evaluation/faithfulness.py score")


def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n
    c = p + z * z / (2 * n); m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def cmd_score():
    answers = {a["id"]: a for a in json.load(open(ANS_FILE, encoding="utf-8"))}
    labels = json.load(open(LABEL_FILE, encoding="utf-8"))
    cnt = {g: {} for g in LABELS}
    for i, a in answers.items():
        lab = (labels.get(i) or {}).get("label")
        if lab: cnt[a["group"]][lab] = cnt[a["group"]].get(lab, 0) + 1
    on, off = cnt["on_topic"], cnt["off_topic"]
    n_on, n_off = sum(on.values()), sum(off.values())
    unlabelled = len(answers) - n_on - n_off
    print(f"labelled: {n_on} on-topic, {n_off} off-topic" + (f"   ({unlabelled} still unlabelled)" if unlabelled else ""))
    answered = n_on - on.get("false_refusal", 0)
    print("\nON-TOPIC questions"); [print(f"  {k:14s} {on.get(k, 0)}") for k, _ in LABELS["on_topic"]]
    if answered:
        s = on.get("supported", 0); lo, hi = wilson(s, answered)
        print(f"  -> fully supported: {s}/{answered} answered = {100*s/answered:.0f}%  (95% interval {100*lo:.0f}-{100*hi:.0f}%)")
        sp = s + on.get("partial", 0); lo2, hi2 = wilson(sp, answered)
        print(f"  -> supported or partly supported: {sp}/{answered} = {100*sp/answered:.0f}%  (95% interval {100*lo2:.0f}-{100*hi2:.0f}%)")
    if n_on: print(f"  -> false refusals: {on.get('false_refusal', 0)}/{n_on}")
    print("\nOFF-TOPIC questions"); [print(f"  {k:16s} {off.get(k, 0)}") for k, _ in LABELS["off_topic"]]
    if n_off:
        c = off.get("correct_refusal", 0); lo, hi = wilson(c, n_off)
        print(f"  -> correctly declined: {c}/{n_off} = {100*c/n_off:.0f}%  (95% interval {100*lo:.0f}-{100*hi:.0f}%)")
    th = next(iter(answers.values())).get("threshold")
    print(f"\nthreshold used: {th}.  Report these numbers with the sample size; with ~40 questions the interval is wide.")
    save(os.path.join(RESULTS, "faith_results.json"), {"on_topic": on, "off_topic": off, "threshold": th, "n_on": n_on, "n_off": n_off})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["sims", "run", "sheet", "score"])
    a = ap.parse_args()
    {"sims": cmd_sims, "run": lambda: cmd_run(a), "sheet": cmd_sheet, "score": cmd_score}[a.cmd]()