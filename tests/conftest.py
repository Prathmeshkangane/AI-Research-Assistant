"""
Test setup. The heavy libraries (torch / sentence-transformers / FAISS / Gemini) are replaced with tiny
fakes BEFORE the app is imported, so the tests run in seconds on any machine and in GitHub Actions,
with no model download, no GPU, no API key and no MySQL (SQLite in memory is used).
"""
import os
import pickle
import sys
import tempfile
import types

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ---- environment (must be set before importing the app) ----
IDS = ["p0", "p1", "p2", "p3"]
EMB_TMP = tempfile.mkdtemp()
with open(os.path.join(EMB_TMP, "paper_ids.pkl"), "wb") as f:
    pickle.dump(IDS, f)
os.environ.update(
    EMBEDDINGS_DIR=EMB_TMP, DATABASE_URL="sqlite://", SECRET_KEY="test-secret", GEMINI_API_KEY="test-key"
)


# ---- fakes for heavy dependencies ----
class FakeIndex:
    """Returns whatever the test put in FakeIndex.next = ([distances], [indices])."""
    next = ([0.1, 0.2], [0, 1])

    def search(self, vectors, k):
        d, i = FakeIndex.next
        return np.array([d[:k]], dtype="float32"), np.array([i[:k]])

    def reconstruct(self, pos):
        return np.zeros(384, dtype="float32")


fake_faiss = types.ModuleType("faiss")
fake_faiss.read_index = lambda path: FakeIndex()
sys.modules["faiss"] = fake_faiss


class FakeSentenceTransformer:
    def __init__(self, *a, **k): pass
    def encode(self, texts, **k): return np.zeros((len(texts), 384), dtype="float32")


fake_st = types.ModuleType("sentence_transformers")
fake_st.SentenceTransformer = FakeSentenceTransformer
sys.modules["sentence_transformers"] = fake_st


class FakeGemini:
    prompts = []          # every prompt sent
    reply = "Answer [1]."  # what the "LLM" says
    fail = False          # set True to simulate an outage
    fail_with = "simulated Gemini outage"   # the error text raised when fail is True


class _FakeModel:
    def __init__(self, name): pass
    def generate_content(self, prompt, **kwargs):
        FakeGemini.prompts.append(prompt)
        if FakeGemini.fail:
            raise RuntimeError(FakeGemini.fail_with)
        return types.SimpleNamespace(text=FakeGemini.reply)


fake_genai = types.ModuleType("google.generativeai")
fake_genai.configure = lambda **k: None
fake_genai.GenerativeModel = _FakeModel
fake_google = types.ModuleType("google")
fake_google.generativeai = fake_genai
sys.modules["google"] = fake_google
sys.modules["google.generativeai"] = fake_genai


# ---- fixtures ----
@pytest.fixture()
def app_ctx():
    from app import app
    from models import db
    from models.paper import Paper
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add_all(
            [Paper(id=i, title=f"Title {i}", authors="A", abstract=f"Abstract {i}", categories="cs.AI") for i in IDS]
        )
        db.session.commit()
        FakeGemini.prompts.clear()
        FakeGemini.reply, FakeGemini.fail = "Answer [1].", False
        FakeGemini.fail_with = "simulated Gemini outage"
        FakeIndex.next = ([0.1, 0.2], [0, 1])
        yield app


@pytest.fixture()
def client(app_ctx):
    return app_ctx.test_client()


@pytest.fixture()
def logged_in(client):
    from models import db
    from models.user import User
    user = User(username="alice", email="alice@example.com", password_hash="x")
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as s:
        s["user_id"], s["username"] = user.id, "alice"
    return client