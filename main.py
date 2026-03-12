from __future__ import annotations

import argparse
import json
import sys

from src.cobol_ast_trace import EntryNotFound, trace_file
from src.cobol_execution import Unknown


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cbl", help="Path to .cbl file")
    ap.add_argument("--entry", default=None, help="Entry paragraph")
    ap.add_argument("--vars", nargs="*", default=[], help='Initial vars like A=1 B="X" FLAG=true')
    ap.add_argument("--copy-dirs", nargs="*", default=[], help="Directories where copybooks are searched")
    ap.add_argument(
        "--copy-exts",
        nargs="*",
        default=["", ".cpy", ".CPY", ".copy", ".COPY"],
        help="Copybook extensions to try",
    )
    ap.add_argument("--max-steps", type=int, default=3000)
    ap.add_argument("--max-paths", type=int, default=80)
    ap.add_argument("--json", action="store_true", help="Output NDJSON (one path per line)")
    args = ap.parse_args()

    try:
        entry, paths = trace_file(
            args.cbl,
            entry=args.entry,
            vars=args.vars,
            copy_dirs=args.copy_dirs,
            copy_exts=args.copy_exts,
            max_steps=args.max_steps,
            max_paths=args.max_paths,
        )
    except EntryNotFound as exc:
        avail = ", ".join(exc.available[:50]) + ("..." if len(exc.available) > 50 else "")
        print(f"Entry paragraph '{exc.entry}' not found. Available: {avail}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"Cannot read file: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        for i, p in enumerate(paths, 1):
            rec = {
                "path_id": i,
                "entry": entry,
                "calls": p.calls,
                "decisions": p.decisions,
                "flags": p.flags,
                "known_env": {k: v for k, v in p.env.items() if v is not Unknown},
                "unknown_env_keys": sorted([k for k, v in p.env.items() if v is Unknown]),
                "steps": p.steps,
            }
            print(json.dumps(rec, ensure_ascii=False))
    else:
        for i, p in enumerate(paths, 1):
            print("=" * 90)
            print(f"PATH #{i} steps={p.steps} flags={p.flags}")
            print("Calls:")
            for c in p.calls:
                if c.get("type") == "ZCALLPGM":
                    print(f"  - ZCALLPGM program={c['program']} USING {c.get('using', [])}")
                else:
                    print(f"  - CALL {c['target']} USING {c.get('using', [])} indirect={c.get('indirect')}")
            print("Decisions:")
            for d in p.decisions:
                print(f"  - {d}")
            known = {k: v for k, v in p.env.items() if v is not Unknown}
            unk = [k for k, v in p.env.items() if v is Unknown]
            print(f"Known vars: {known}")
            print(f"Unknown vars: {unk}")


if __name__ == "__main__":
    main()
