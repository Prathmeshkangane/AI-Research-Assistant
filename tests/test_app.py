from models import db
from models.chat_history import ChatHistory
from models.saved_paper import SavedPaper
from models.user import User
from tests.conftest import FakeGemini, FakeIndex


# ---------------- search / retrieval ----------------
def test_search_returns_papers_in_faiss_order(app_ctx):
    from services.semantic_search import semantic_search
    FakeIndex.next = ([0.1, 0.2], [2, 0])
    assert [p.id for p in semantic_search("graph neural networks", top_k=2)] == ["p2", "p0"]


def test_search_ignores_missing_results_marked_minus_one(app_ctx):
    from services.semantic_search import semantic_search
    FakeIndex.next = ([0.1, 9.9], [1, -1])
    assert [p.id for p in semantic_search("anything", top_k=2)] == ["p1"]


def test_empty_query_returns_nothing(app_ctx):
    from services.semantic_search import semantic_search
    assert semantic_search("   ") == []


def test_search_route_with_empty_query_is_ok(client):
    assert client.get("/search").status_code == 200


def test_similar_papers_excludes_the_paper_itself(app_ctx):
    from models.paper import Paper
    from services.faiss_recommendation import get_similar_papers_faiss
    FakeIndex.next = ([0.0, 0.1, 0.2], [1, 2, 3])      # first hit is the paper itself
    similar = get_similar_papers_faiss(db.session.get(Paper, "p1"), top_k=2)
    assert [p.id for p in similar] == ["p2", "p3"]


# ---------------- RAG ----------------
def test_rag_skips_the_llm_when_nothing_is_relevant(app_ctx):
    from services.rag_service import answer_question, NO_RELEVANT_PAPERS
    FakeIndex.next = ([1.9, 1.95], [0, 1])             # cosine ~0.05: irrelevant
    answer, papers = answer_question("what is the weather?")
    assert answer == NO_RELEVANT_PAPERS and papers == []
    assert FakeGemini.prompts == []                    # no LLM call = no cost, no hallucination


def test_rag_prompt_has_numbered_sources_and_returns_them(app_ctx):
    from services.rag_service import answer_question
    FakeIndex.next = ([0.2, 0.4], [0, 1])              # cosine 0.9 / 0.8: relevant
    answer, papers = answer_question("explain p0")
    assert answer == "Answer [1]." and [p.id for p in papers] == ["p0", "p1"]
    assert "[1] Title: Title p0" in FakeGemini.prompts[0] and "[2] Title: Title p1" in FakeGemini.prompts[0]


def test_rag_survives_llm_outage(app_ctx):
    from services.rag_service import answer_question, LLM_UNAVAILABLE
    FakeIndex.next = ([0.2], [0])
    FakeGemini.fail = True
    answer, papers = answer_question("explain p0")
    assert answer == LLM_UNAVAILABLE and len(papers) == 1


def test_rag_reports_quota_exhaustion_clearly(app_ctx):
    from services.rag_service import answer_question, QUOTA_EXCEEDED
    FakeIndex.next = ([0.2], [0])
    FakeGemini.fail, FakeGemini.fail_with = True, "429 You exceeded your current quota"
    answer, _ = answer_question("explain p0")
    assert answer == QUOTA_EXCEEDED


def test_summary_failure_is_not_cached(app_ctx):
    from models.paper import Paper
    from models import db
    from services.summary_service import summarize_paper, _cache
    _cache.clear()
    paper = db.session.get(Paper, "p0")
    FakeGemini.fail = True
    summarize_paper(paper)
    assert "p0" not in _cache
    FakeGemini.fail = False
    FakeGemini.reply = "Real summary"
    assert summarize_paper(paper) == "Real summary"


# ---------------- auth ----------------
def test_register_login_logout_flow(client):
    r = client.post("/register", data={"username": "bob", "email": "Bob@Example.com", "password": "longenough1"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    r = client.post("/login", data={"email": "bob@example.com", "password": "longenough1"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/dashboard")
    with client.session_transaction() as s:
        assert s["username"] == "bob"
    client.get("/logout")
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_login_error_is_the_same_for_unknown_email_and_wrong_password(client):
    client.post("/register", data={"username": "bob", "email": "bob@example.com", "password": "longenough1"})
    for email, pw in [("nobody@example.com", "whatever12"), ("bob@example.com", "wrongpass12")]:
        client.post("/login", data={"email": email, "password": pw})
        with client.session_transaction() as s:
            assert s["_flashes"][-1][1] == "Invalid email or password"
            s.pop("_flashes")


def test_short_password_is_rejected(client):
    client.post("/register", data={"username": "bob", "email": "bob@example.com", "password": "short"})
    assert User.query.count() == 0


def test_duplicate_email_is_rejected(client):
    data = {"username": "bob", "email": "bob@example.com", "password": "longenough1"}
    client.post("/register", data=data)
    client.post("/register", data={**data, "username": "bob2"})
    assert User.query.count() == 1


def test_passwords_are_stored_hashed(client):
    client.post("/register", data={"username": "bob", "email": "bob@example.com", "password": "longenough1"})
    assert User.query.first().password_hash.startswith("$2")


# ---------------- ask (regression for the empty-question crash) ----------------
def test_ask_with_empty_question_does_not_crash_or_save(logged_in):
    r = logged_in.post("/ask", data={"question": "   "})
    assert r.status_code == 200
    assert ChatHistory.query.count() == 0


def test_ask_saves_history_for_logged_in_user(logged_in):
    FakeIndex.next = ([0.2], [0])
    r = logged_in.post("/ask", data={"question": "explain p0"})
    assert r.status_code == 200
    chat = ChatHistory.query.one()
    assert chat.question == "explain p0" and chat.answer == "Answer [1]."


def test_ask_does_not_save_failure_messages_in_history(logged_in):
    FakeIndex.next = ([0.2], [0])
    FakeGemini.fail = True
    logged_in.post("/ask", data={"question": "explain p0"})
    assert ChatHistory.query.count() == 0


# ---------------- saved papers ----------------
def test_save_and_unsave_paper(logged_in):
    assert logged_in.get("/save/p1").status_code == 302
    logged_in.get("/save/p1")                              # saving twice must not duplicate
    assert SavedPaper.query.count() == 1
    logged_in.get("/unsave/p1")
    assert SavedPaper.query.count() == 0


def test_saving_unknown_paper_gives_404_not_500(logged_in):
    assert logged_in.get("/save/does-not-exist").status_code == 404


def test_save_requires_login(client):
    r = client.get("/save/p1")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_healthz(client):
    assert client.get("/healthz").data == b"ok"


# ---------------- embedding settings / ONNX backend ----------------
def test_settings_prefer_env_then_meta_then_default():
    from services.semantic_search import resolve_settings, DEFAULT_MODEL
    meta = {"model": "BAAI/bge-small-en-v1.5", "query_prefix": "Represent:"}
    assert resolve_settings({}, meta) == ("BAAI/bge-small-en-v1.5", "Represent:", "torch")
    assert resolve_settings({"EMBED_MODEL": "x/y", "QUERY_PREFIX": "q:", "EMBED_BACKEND": "ONNX"}, meta) == ("x/y", "q:", "onnx")
    assert resolve_settings({}, {}) == (DEFAULT_MODEL, "", "torch")


def test_onnx_backend_adds_prefix_and_normalises(monkeypatch):
    import importlib
    import numpy as np
    from services import semantic_search as ss
    from tests.conftest import FakeTextEmbedding
    monkeypatch.setenv("EMBED_BACKEND", "onnx")
    monkeypatch.setenv("QUERY_PREFIX", "query:")
    try:
        importlib.reload(ss)
        FakeTextEmbedding.seen.clear()
        vec = ss.encode_query("graph networks")
        assert FakeTextEmbedding.seen == ["query: graph networks"]
        assert vec.shape == (1, 384) and abs(float(np.linalg.norm(vec)) - 1.0) < 1e-5
    finally:
        monkeypatch.undo()
        importlib.reload(ss)


# ---------------- every page renders with the new templates ----------------
def test_all_pages_render(logged_in):
    from models import db
    from models.chat_history import ChatHistory
    from tests.conftest import FakeIndex
    FakeIndex.next = ([0.2, 0.4], [0, 1])
    db.session.add(ChatHistory(user_id=1, question="What is x?", answer="**Bold** answer [1]."))
    db.session.commit()
    logged_in.get("/save/p0"); logged_in.get("/save/p1")
    pages = ["/dashboard", "/search", "/search?q=graph", "/paper/p0", "/saved-papers", "/ask",
             "/history", "/summarize/p0", "/compare?paper1=p0&paper2=p1"]
    for url in pages:
        r = logged_in.get(url)
        assert r.status_code == 200, url
        assert b"ResearchAI" in r.data, url
    r = logged_in.post("/ask", data={"question": "explain p0"})
    assert r.status_code == 200 and b'id="src-1"' in r.data


def test_auth_pages_render_without_login(client):
    for url in ["/login", "/register", "/"]:
        assert client.get(url).status_code == 200, url


def test_unknown_page_shows_friendly_404(client):
    r = client.get("/definitely-not-a-page")
    assert r.status_code == 404 and b"Page not found" in r.data


def test_paper_page_shows_saved_state(logged_in):
    assert b"Save to library" in logged_in.get("/paper/p0").data
    logged_in.get("/save/p0")
    assert b"Saved" in logged_in.get("/paper/p0").data


def test_static_assets_are_served(client):
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_login_failure_message_is_visible(client):
    client.post("/login", data={"email": "nobody@example.com", "password": "wrongwrong"})
    assert b"Invalid email or password" in client.get("/login").data
