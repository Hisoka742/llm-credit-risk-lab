from __future__ import annotations

import sys
import types

import numpy as np
import pandas as pd
import pytest

from src.eval.compare import compare_to_baseline
from src.features.embeddings import (
    EmbedSettings,
    fit_reducer,
    load_embeddings,
    save_embeddings,
)


class FakeST:
    """Stands in for SentenceTransformer: deterministic vectors, counts encoded texts."""

    encoded: list[str] = []

    def __init__(self, name: str, device: str = "cpu") -> None:
        self.max_seq_length = 512
        self.tokenizer = lambda texts: {"input_ids": [t.split() for t in texts]}

    def half(self) -> None:
        pass

    def encode(self, texts, **_) -> np.ndarray:
        FakeST.encoded.extend(texts)
        return np.array([[len(t), t.count("a"), 1.0] for t in texts], dtype=np.float32)


@pytest.fixture
def fake_st(monkeypatch):
    FakeST.encoded = []
    monkeypatch.setitem(sys.modules, "sentence_transformers",
                        types.SimpleNamespace(SentenceTransformer=FakeST))  # fmt: skip
    return FakeST


def test_embed_cache_dedups_and_reuses(tmp_path, fake_st) -> None:
    from src.features.embeddings import embed_texts

    s = EmbedSettings("fake/model")
    texts = pd.Series(["debt consolidation", "car", "debt consolidation", "a banana"])
    m1, st1 = embed_texts(texts, s, tmp_path, device="cpu", shard_size=2)
    assert st1.n_computed == 3 and len(fake_st.encoded) == 3  # duplicate embedded once
    assert np.array_equal(m1[0], m1[2])
    m2, st2 = embed_texts(texts[::-1].reset_index(drop=True), s, tmp_path, device="cpu")
    assert st2.n_computed == 0 and len(fake_st.encoded) == 3  # all from cache
    assert np.array_equal(m2, m1[::-1])  # rows follow the input order


def test_load_embeddings_aligns_and_fails_on_missing(tmp_path) -> None:
    path = tmp_path / "e.parquet"
    save_embeddings(path, pd.Series(["a", "b"]), np.array([[1, 2], [3, 4]], dtype=np.float32))
    got = load_embeddings(path, pd.Series(["b", "a"]))
    assert got.tolist() == [[3, 4], [1, 2]]
    with pytest.raises(ValueError, match="no embedding"):
        load_embeddings(path, pd.Series(["a", "zzz"]))


def test_reducer_is_fit_on_train_only() -> None:
    rng = np.random.default_rng(0)
    train = rng.normal(size=(500, 10))
    shifted = train + 100  # a test set far away must not move the basis or the mean
    pca = fit_reducer(train, 3, seed=0)
    assert np.allclose(pca.mean_, train.mean(axis=0))
    assert not np.allclose(pca.mean_, np.vstack([train, shifted]).mean(axis=0))


def _preds(scores: np.ndarray, y: np.ndarray, ids: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"id": ids, "issue_d": pd.Timestamp("2014-01-01"), "split": "test",
                         "target": y, "score": scores})  # fmt: skip


def test_compare_detects_improvement_and_misalignment() -> None:
    rng = np.random.default_rng(0)
    n = 3000
    y = rng.integers(0, 2, n)
    good = y + rng.normal(0, 0.8, n)
    bad = y + rng.normal(0, 2.0, n)
    ids = [str(i) for i in range(n)]
    c = compare_to_baseline(_preds(good, y, ids), _preds(bad, y, ids), 200, 0, 0.95)
    assert c["gini_diff"]["ci_low"] > 0
    assert len(c["gini_diff_by_quarter"]) == 1
    with pytest.raises(ValueError, match="different test loans"):
        compare_to_baseline(_preds(good, y, ids), _preds(bad, 1 - y, ids), 50, 0, 0.95)
