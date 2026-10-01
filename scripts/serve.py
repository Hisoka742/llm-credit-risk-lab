"""Serve the live demo API.

    python -m scripts.build_live                 # once, after E2 has been run
    python -m scripts.serve                      # http://127.0.0.1:8000/api/health

Reads `configs/live.yaml`. With `live.provider: gigachat`, put GIGACHAT_AUTH_KEY in .env
(see src/live/gigachat.py for the TLS certificate note). The site's dev server proxies /api
to this port, so `npm run dev` in site/ shows the "Try it" section while this is running.
"""

from __future__ import annotations

import argparse
import os

from src.config import load_config, load_dotenv
from src.features.llm_extract import FatalLLMError
from src.live.api import build_scorer, create_app


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="configs/live.yaml")
    ap.add_argument("--provider", default=None, help="override live.provider")
    ap.add_argument("--model", default=None, help="override live.model")
    ap.add_argument("--base-url", default=None, help="override llm.base_url (openai_compatible)")
    args = ap.parse_args()

    import uvicorn

    load_dotenv()
    cfg = load_config(args.config)
    if args.provider:
        cfg["live"]["provider"] = args.provider
    if args.model:
        cfg["live"]["model"] = args.model
    if args.base_url:
        cfg["llm"]["base_url"] = args.base_url
    if os.environ.get("LIVE_TRUST_PROXY", "").lower() in ("1", "true", "yes"):
        cfg["live"]["trust_proxy"] = True
    try:
        scorer, reset_auth = build_scorer(cfg)
    except FileNotFoundError as e:
        raise SystemExit(f"[serve] live bundle missing ({e}). Run: python -m scripts.build_live") \
            from None  # fmt: skip
    except FatalLLMError as e:
        raise SystemExit(f"[serve] {e}") from None
    live = cfg["live"]
    print(f"[serve] {len(scorer.b.profiles)} profiles | reader {live['model']} "
          f"({live['provider']}) | model trained on {scorer.b.trained_on}")  # fmt: skip
    # Hosting platforms pass the address through the environment (HOST, PORT).
    host = os.environ.get("HOST", live["host"])
    port = int(os.environ.get("PORT", live["port"]))
    uvicorn.run(create_app(cfg, scorer, reset_auth), host=host, port=port)


if __name__ == "__main__":
    main()
