"""Sentence embeddings of `desc` with a disk cache, plus a train-only PCA reduction.

Cache design: vectors are keyed by sha1(model + settings + text), not by loan id. Identical
descriptions ("Debt consolidation" appears ~1k times) are embedded once, and any rerun or
new sample only embeds texts it has not seen. The cache is written as numbered parquet
shards after every `shard_size` texts, so an interrupted Kaggle session loses at most one
shard of work.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


@dataclass(frozen=True)
class EmbedSettings:
    model_name: str
    max_seq_length: int = 512
    prefix: str = ""  # e.g. "passage: " for e5 models; bge needs none for documents
    normalize: bool = True
    batch_size: int = 64

    @property
    def slug(self) -> str:
        return self.model_name.split("/")[-1]


def pick_device(requested: str | None = None) -> str:
    if requested:
        return requested
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def cache_key(s: EmbedSettings, precision: str, text: str) -> str:
    # Precision is part of the key: fp16 (GPU) and fp32 (CPU) vectors differ slightly, and
    # mixing them in one matrix would make results depend on where each shard was computed.
    raw = f"{s.model_name}|{s.max_seq_length}|{s.prefix}|{s.normalize}|{precision}|{text}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _emb_cols(dim: int) -> list[str]:
    return [f"emb_{i:03d}" for i in range(dim)]


def load_cache(cache_dir: Path) -> pd.DataFrame:
    parts = sorted(cache_dir.glob("part-*.parquet"))
    if not parts:
        return pd.DataFrame()
    cache = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    return cache.drop_duplicates("key").set_index("key")


@dataclass
class EmbedStats:
    device: str
    precision: str
    n_texts: int
    n_unique: int
    n_computed: int
    seconds: float
    mean_tokens: float
    share_truncated: float

    @property
    def texts_per_second(self) -> float:
        return self.n_computed / self.seconds if self.seconds else float("nan")


def embed_texts(
    texts: pd.Series,
    s: EmbedSettings,
    cache_dir: Path,
    device: str | None = None,
    fp16: bool = True,
    shard_size: int = 10_000,
) -> tuple[np.ndarray, EmbedStats]:
    """Return an (n, dim) float32 matrix aligned with `texts`, and cost stats."""
    from sentence_transformers import SentenceTransformer

    device = pick_device(device)
    precision = "fp16" if (fp16 and device == "cuda") else "fp32"
    model = SentenceTransformer(s.model_name, device=device)
    model.max_seq_length = s.max_seq_length
    if precision == "fp16":
        model.half()

    inputs = (s.prefix + texts.astype(str)).tolist()
    keys = pd.Series([cache_key(s, precision, t) for t in inputs], index=texts.index)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = load_cache(cache_dir)
    todo = (
        pd.DataFrame({"key": keys.to_numpy(), "text": inputs})
        .drop_duplicates("key")
        .loc[lambda d: ~d["key"].isin(cache.index)]
    )
    print(f"[embed] {len(texts):,} texts, {keys.nunique():,} unique, {len(todo):,} to compute "
          f"on {device} ({precision})")  # fmt: skip

    t0 = time.perf_counter()
    next_part = len(list(cache_dir.glob("part-*.parquet")))
    new_parts = []
    for start in range(0, len(todo), shard_size):
        chunk = todo.iloc[start : start + shard_size]
        vecs = model.encode(
            chunk["text"].tolist(),
            batch_size=s.batch_size,
            normalize_embeddings=s.normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)
        part = pd.DataFrame(vecs, columns=_emb_cols(vecs.shape[1]))
        part.insert(0, "key", chunk["key"].to_numpy())
        part.to_parquet(cache_dir / f"part-{next_part:05d}.parquet", index=False)
        next_part += 1
        new_parts.append(part.set_index("key"))
        done = start + len(chunk)
        rate = done / (time.perf_counter() - t0)
        print(f"[embed] {done:,}/{len(todo):,}  {rate:.0f} texts/s  "
              f"eta {(len(todo) - done) / rate / 60:.1f} min", flush=True)  # fmt: skip
    seconds = time.perf_counter() - t0

    if new_parts:
        cache = pd.concat([cache, *new_parts]) if len(cache) else pd.concat(new_parts)
    matrix = cache.loc[keys.to_numpy()].to_numpy(dtype=np.float32)

    n_tok = np.array([len(t) for t in model.tokenizer(inputs)["input_ids"]])
    stats = EmbedStats(
        device=device,
        precision=precision,
        n_texts=len(texts),
        n_unique=int(keys.nunique()),
        n_computed=len(todo),
        seconds=round(seconds, 1),
        mean_tokens=float(np.minimum(n_tok, s.max_seq_length).mean()),
        share_truncated=float((n_tok > s.max_seq_length).mean()),
    )
    return matrix, stats


def embeddings_path(processed_dir: Path, s: EmbedSettings) -> Path:
    return processed_dir / "embeddings" / f"{s.slug}.parquet"


def save_embeddings(path: Path, ids: pd.Series, matrix: np.ndarray) -> None:
    out = pd.DataFrame(matrix, columns=_emb_cols(matrix.shape[1]))
    out.insert(0, "id", ids.to_numpy())
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)


def load_embeddings(path: Path, ids: pd.Series) -> np.ndarray:
    """Load the per-loan matrix aligned to `ids`. Fails loudly on any missing id."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Run: python -m scripts.embed --config ...")
    emb = pd.read_parquet(path).set_index("id")
    missing = ~ids.isin(emb.index)
    if missing.any():
        raise ValueError(f"{int(missing.sum())} loans have no embedding; rerun scripts.embed")
    return emb.loc[ids.to_numpy()].to_numpy(dtype=np.float32)


def fit_reducer(train_matrix: np.ndarray, n_components: int, seed: int) -> PCA:
    """PCA = SVD of the train-centered matrix, fit on train rows only.

    Centering matters: sentence embeddings are anisotropic (they share a large common
    direction). Uncentered TruncatedSVD would spend its first component on that near-constant
    mean vector. Fitting on train only keeps val/test out of the basis.
    """
    return PCA(n_components=n_components, svd_solver="full", random_state=seed).fit(train_matrix)


def reduce(pca: PCA, matrix: np.ndarray, prefix: str = "emb_pc") -> pd.DataFrame:
    z = pca.transform(matrix).astype(np.float32)
    return pd.DataFrame(z, columns=[f"{prefix}_{i:02d}" for i in range(z.shape[1])])
