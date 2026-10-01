"""Record real live-demo runs, so the static site can show them without a server.

    python -m scripts.record_live          # needs the live reader (GIGACHAT_AUTH_KEY in .env)

Each prepared text is read once by the configured LLM and scored for every demo profile.
Each profile's original description is read too, which shows where the live reader disagrees
with the model that produced the training labels. Output: reports/live/recorded.json, which
`scripts.export_site_data` copies into the site data. Nothing here is typed by hand.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from src.config import load_config, load_dotenv
from src.features.llm_extract import FatalLLMError
from src.live.api import build_scorer

# Prepared rewrites. One is in Russian: the prompt is English, the reader is multilingual.
TEXTS = [
    {"id": "hardship", "lang": "en",
     "text": "I lost my job two months ago and I am behind on my credit card bills. My wife had "
             "surgery and we need help to catch up."},
    {"id": "stable_plan", "lang": "en",
     "text": "I have worked as a nurse at the same hospital for eleven years. I want to pay off "
             "two credit cards at a lower rate. My budget leaves $600 a month for this payment "
             "and I plan to finish in three years."},
    {"id": "two_words", "lang": "en", "text": "need money"},
    {"id": "business", "lang": "en",
     "text": "I am opening a second location for my bakery and need funds for equipment and the "
             "first months of rent."},
    {"id": "stable_plan_ru", "lang": "ru",
     "text": "Работаю инженером на одном заводе девять лет. Хочу закрыть две кредитные карты "
             "одним платежом по более низкой ставке. Из зарплаты могу отдавать 40 тысяч в месяц "
             "и планирую расплатиться за три года."},
]  # fmt: skip

KEEP = ("reading", "error", "latency_s", "prompt_tokens", "completion_tokens", "pd_your_text",
        "contributions")  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/live.yaml")
    args = ap.parse_args()

    load_dotenv()
    cfg = load_config(args.config)
    try:
        scorer, _ = build_scorer(cfg)
    except FatalLLMError as e:
        raise SystemExit(f"[record] {e}") from None

    runs = []
    for p in scorer.b.profiles:
        items = [*TEXTS, {"id": "original", "lang": "en", "text": p["desc"]}]
        for t in items:
            out = scorer.analyze(p["id"], t["text"])
            if (out["error"] or "").startswith("api"):
                raise SystemExit(f"[record] reader failed on {t['id']}: {out['error']}")
            runs.append({"profile_id": p["id"], "text_id": t["id"], **{k: out[k] for k in KEEP}})
        print(f"[record] profile {p['id']} (grade {p['grade']}) done", flush=True)

    out_path = Path(cfg["paths"]["reports_dir"]) / "live" / "recorded.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "reader": scorer.s.model,
                "provider": cfg["live"]["provider"],
                "trained_on": scorer.b.trained_on,
                "recorded_on": dt.date.today().isoformat(),
                "max_text_chars": cfg["live"]["max_text_chars"],
                "texts": TEXTS,
                "profiles": scorer.b.profiles,
                "runs": runs,
            },
            indent=1, ensure_ascii=False,
        ),
        encoding="utf-8",
    )  # fmt: skip
    print(f"wrote {out_path}: {len(scorer.b.profiles)} profiles x {len(TEXTS) + 1} texts")


if __name__ == "__main__":
    main()
