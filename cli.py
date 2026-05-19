#!/usr/bin/env python3
"""silo-client — CLI for querying a remote cohub-silo instance.

Uses the public REST API at https://s-{space}-5173.cohub.run.
No authentication required — silo is public by design.

Usage:
  silo-client config --space <uuid>          # Set target silo space UUID
  silo-client collections                     # List all collections
  silo-client search --q "keyword" [...]      # Full-text search
  silo-client sample [...]                    # Random sample
  silo-client get <id> [--content]            # Get single item
  silo-client topics                          # List topics with counts
  silo-client stats                           # Daily stats summary

Config:
  Space UUID is resolved in order:
    1. --space CLI flag
    2. SILO_SPACE environment variable
    3. Saved config in ~/.silo-client.json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path.home() / ".silo-client.json"
BASE_PORT = 5173


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def resolve_space(args):
    """Resolve space UUID from args / env / config."""
    if getattr(args, "space", None):
        return args.space
    env = os.environ.get("SILO_SPACE", "").strip()
    if env:
        return env
    cfg = load_config()
    return cfg.get("space", None)


def api_url(space, path):
    return f"https://s-{space}-{BASE_PORT}.cohub.run{path}"


def fetch_json(url):
    """GET JSON from silo API."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err = json.loads(body)
            msg = err.get("error", body[:200])
        except Exception:
            msg = body[:200]
        print(f"✗ HTTP {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"✗ connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def require_space(args):
    space = resolve_space(args)
    if not space:
        print("✗ no silo space configured.", file=sys.stderr)
        print("  set with: silo-client config --space <uuid>", file=sys.stderr)
        print("  or:       export SILO_SPACE=<uuid>", file=sys.stderr)
        sys.exit(1)
    return space


# ─── Commands ────────────────────────────────────────────────


def cmd_config(args):
    """Save or show config."""
    if args.space:
        cfg = load_config()
        cfg["space"] = args.space
        save_config(cfg)
        print(f"✓ silo space set to {args.space}")
    else:
        cfg = load_config()
        env = os.environ.get("SILO_SPACE", "")
        print(f"config file:  {CONFIG_PATH}")
        print(f"space:        {cfg.get('space', '(not set)')}")
        print(f"SILO_SPACE:   {env or '(not set)'}")


def cmd_collections(args):
    """List collections."""
    space = require_space(args)
    data = fetch_json(api_url(space, "/api/collections"))
    if not data:
        print("(no collections)")
        return
    print(f"{'ID':28s} {'NAME':20s} {'TOPIC':16s} ITEMS")
    print("-" * 80)
    for c in data:
        print(f"{c['id']:28s} {c['name'][:20]:20s} {c['topic'][:16]:16s} {c['item_count']}")


def cmd_topics(args):
    """List topics with counts."""
    space = require_space(args)
    data = fetch_json(api_url(space, "/api/items/topics"))
    if not data:
        print("(no topics)")
        return
    for t in data:
        print(f"  {t['topic']:20s} {t['count']} items")


def cmd_stats(args):
    """Show daily stats."""
    space = require_space(args)
    data = fetch_json(api_url(space, "/api/stats/daily"))
    print(f"total items: {data['total']}")
    print()
    print(f"{'DATE':12s} {'ITEMS':>6s}  COLLECTIONS")
    print("-" * 60)
    for d in data.get("days", []):
        colls = ", ".join(f"{k}({v})" for k, v in d.get("collections", {}).items())
        print(f"{d['date']:12s} {d['total']:>6d}  {colls}")


def cmd_search(args):
    """Full-text search."""
    space = require_space(args)
    params = []
    if args.q:
        params.append(("q", args.q))
    if args.collection:
        params.append(("collection", args.collection))
    if args.topic:
        params.append(("topic", args.topic))
    if args.sort:
        params.append(("sort", args.sort))
    limit = args.limit or 20
    params.append(("limit", str(limit)))

    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params)
    data = fetch_json(api_url(space, f"/api/items?{qs}"))

    items = data.get("items", [])
    if not items:
        print("(no results)")
        return

    print(f"{data.get('total', len(items))} results (showing {len(items)}):\n")
    for it in items:
        tags = ", ".join(it.get("tags", [])[:3])
        print(f"  [{it['id']:4d}] {it['title'][:70]:70s}")
        print(f"         {it['collection_id']:20s}  topic={it['topic']:14s}  {tags}")
        if it.get("excerpt"):
            print(f"         {it['excerpt'][:120]}")
        print()

    if data.get("has_more"):
        print(f"  ⋯ more results available (next cursor: {data['next_cursor']})")


def cmd_sample(args):
    """Random sample from silo."""
    space = require_space(args)
    params = []
    if args.topic:
        params.append(("topic", args.topic))
    if args.collection:
        params.append(("collection", args.collection))
    params.append(("limit", str(args.limit or 5)))

    qs = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params)
    data = fetch_json(api_url(space, f"/api/items/sample?{qs}"))

    if not data:
        print("(no items to sample)")
        return

    for it in data:
        tags = ", ".join(it.get("tags", [])[:5])
        print(f"\n── [{it['id']}] {it['title']} ──")
        print(f"  collection: {it['collection_id']}  topic: {it['topic']}  tags: {tags}")
        print(f"  file: {it['filename']}  size: {it['size']}  mtime: {it['mtime']}")
        if it.get("excerpt"):
            print(f"\n  {it['excerpt'][:300]}")
        if it.get("source_url"):
            print(f"  source: {it['source_url']}")


def cmd_get(args):
    """Get single item by ID."""
    space = require_space(args)
    suffix = "?content=1" if args.content else ""
    data = fetch_json(api_url(space, f"/api/items/{args.id}{suffix}"))

    print(f"ID:         {data['id']}")
    print(f"Title:      {data['title']}")
    print(f"Collection: {data['collection_id']}")
    print(f"Topic:      {data['topic']}")
    print(f"Tags:       {', '.join(data.get('tags', []))}")
    print(f"File:       {data['filename']}  ({data['size']} bytes)")
    print(f"MIME:       {data['mimetype']}")
    print(f"Modified:   {data['mtime']}")
    print(f"Indexed:    {data['fetched_at']}")
    if data.get("source_url"):
        print(f"Source:     {data['source_url']}")
    if data.get("media_url"):
        print(f"Media:      {data['media_url']} ({data['media_type']})")

    content = data.get("content", "")
    if content:
        print(f"\n{'─' * 60}")
        print(content)


# ─── Main ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="silo-client",
        description="Query a remote cohub-silo data server",
    )
    parser.add_argument("--space", help="Silo space UUID (overrides env/config)")

    sub = parser.add_subparsers(dest="command")

    # config
    p_cfg = sub.add_parser("config", help="Set or show silo space config")
    p_cfg.add_argument("--space", help="Space UUID to save")

    # collections
    sub.add_parser("collections", help="List collections")

    # topics
    sub.add_parser("topics", help="List topics with counts")

    # stats
    sub.add_parser("stats", help="Daily stats summary")

    # search
    p_sr = sub.add_parser("search", help="Full-text search")
    p_sr.add_argument("--q", help="Search query (FTS5 full-text)")
    p_sr.add_argument("--collection", help="Filter by collection ID")
    p_sr.add_argument("--topic", help="Filter by topic")
    p_sr.add_argument("--sort", choices=["latest", "random", "relevant"], default="latest")
    p_sr.add_argument("--limit", type=int, default=20)

    # sample
    p_sm = sub.add_parser("sample", help="Random sample of items")
    p_sm.add_argument("--topic", help="Filter by topic")
    p_sm.add_argument("--collection", help="Filter by collection ID")
    p_sm.add_argument("--limit", type=int, default=5)

    # get
    p_gt = sub.add_parser("get", help="Get single item by ID")
    p_gt.add_argument("id", type=int)
    p_gt.add_argument("--content", action="store_true", help="Include full content")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmds = {
        "config": cmd_config,
        "collections": cmd_collections,
        "topics": cmd_topics,
        "stats": cmd_stats,
        "search": cmd_search,
        "sample": cmd_sample,
        "get": cmd_get,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
