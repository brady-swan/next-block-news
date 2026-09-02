#!/usr/bin/env python3
"""Dry-run-first bounded recovery of fresh exhausted source-timeout jobs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbn import store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    con = store.connect()
    try:
        result = store.recover_exhausted_timeouts(
            con, limit=args.limit, apply=args.apply
        )
    finally:
        con.close()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
