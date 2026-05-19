#!/usr/bin/env python3
"""silo-client — CLI for querying remote cohub-silo instances.

Uses the public REST API at https://s-{space}-5173.cohub.run.
No authentication required — silo is public by design.
Supports multiple spaces via aliases.

Usage:
  silo-client config --space <uuid> [--alias <name>]  # Add or update a space
  silo-client config --default <alias>                # Set default space
  silo-client config --remove <alias>                 # Remove a space
  silo-client config                                  # Show all configured spaces
  silo-client spaces                                  # Alias: list configured spaces
  silo-client collections [--space <alias|uuid>]      # List collections
  silo-client search --q "..." [--space ...] [...]    # Full-text search
  silo-client sample [--space ...] [...]              # Random sample
  silo-client get <id> [--space ...] [--content]      # Get single item
  silo-client topics [--space ...]                    # List topics with counts
  silo-client stats [--space ...]                     # Daily stats

Space resolution (--space flag):
  Accepts either an alias (e.g. "kjx") or a raw UUID.
  If not given, resolves from SILO_SPACE env → config default.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path.home() / ".silo-client.json"
BASE_PORT = 5173
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


# ─── Config helpers ──────────────────────────────────────────


def load_config():
    """Load config, auto-migrating old single-space format."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        # Migrate old format: {"space": "uuid"} → {"spaces": {...}, "default": "..."}
        if "space" in cfg and "spaces" not in cfg:
            old = cfg.pop("space")
            cfg["spaces"] = {"default": old}
            cfg["default"] = "default"
            save_config(cfg)
        return cfg
    return {}


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get_spaces():
    """Return {alias: uuid} dict from config."""
    cfg = load_config()
    return cfg.get("spaces", {})


def get_default_alias():
    cfg = load_config()
    return cfg.get("default", None)


def resolve_space(space_arg):
    """Resolve a space argument (alias or raw UUID) to a UUID.

    Resolution order:
      1. If it's a raw UUID, return as-is
      2. If it matches a configured alias, return the saved UUID
      3. Otherwise, return None
    """
    if not space_arg:
        return None
    if UUID_RE.match(space_arg):
        return space_arg  # raw UUID
    spaces = get_spaces()
    return spaces.get(space_arg, None)


def require_space(args):
    """Resolve the space to use for this command.

    Order: --space flag → SILO_SPACE env → config default alias.
    """
    # 1. --space flag
    if getattr(args, "space", None):
        uuid = resolve_space(args.space)
        if not uuid:
            spaces = get_spaces()
            known = ", ".join(spaces.keys()) if spaces else "none"
            print(f"✗ unknown space: '{args.space}'", file=sys.stderr)
            print(f"  known aliases: {known}", file=sys.stderr)
            print(f"  raw UUIDs are also accepted", file=sys.stderr)
            sys.exit(1)
        return uuid

    # 2. SILO_SPACE env
    env = os.environ.get("SILO_SPACE", "").strip()
    if env:
        uuid = resolve_space(env)
        if not uuid:
            print(f"✗ SILO_SPACE='{env}' is neither a known alias nor a valid UUID", file=sys.stderr)
            sys.exit(1)
        return uuid

    # 3. config default
    default_alias = get_default_alias()
    if default_alias:
        spaces = get_spaces()
        uuid = spaces.get(default_alias)
        if uuid:
            return uuid

    # Nothing configured
    print("✗ no silo space configured.", file=sys.stderr)
    print("  set with: silo-client config --space <uuid> --alias <name>", file=sys.stderr)
    print("  or:       export SILO_SPACE=<alias|uuid>", file=sys.stderr)
    sys.exit(1)


def api_url(space_uuid, path):
    return f"https://s-{space_uuid}-{BASE_PORT}.cohub.run{path}"


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


# ─── Commands ────────────────────────────────────────────────


def cmd_config(args):
    """Manage spaces config."""
    cfg = load_config()
    spaces = cfg.get("spaces", {})

    if args.remove:
        alias = args.remove
        if alias not in spaces:
            print(f"✗ alias '{alias}' not found in config", file=sys.stderr)
            sys.exit(1)
        del spaces[alias]
        if cfg.get("default") == alias:
            cfg["default"] = next(iter(spaces), None)
        save_config(cfg)
        print(f"✓ removed '{alias}'")
        return

    if args.default:
        alias = args.default
        if alias not in spaces:
            print(f"✗ alias '{alias}' not found. Add it first:", file=sys.stderr)
            print(f"  silo-client config --space <uuid> --alias {alias}", file=sys.stderr)
            sys.exit(1)
        cfg["default"] = alias
        save_config(cfg)
        print(f"✓ default space set to '{alias}' ({spaces[alias]})")
        return

    if args.space:
        alias = args.alias or "default"
        if UUID_RE.match(args.space):
            uuid = args.space
        else:
            uuid = resolve_space(args.space)
            if not uuid:
                print(f"✗ '{args.space}' is not a valid UUID or known alias", file=sys.stderr)
                sys.exit(1)
        spaces[alias] = uuid
        if not cfg.get("default"):
            cfg["default"] = alias
        cfg["spaces"] = spaces
        save_config(cfg)
        print(f"✓ '{alias}' → {uuid}")
        if cfg["default"] == alias:
            print(f"  (default)")
        return

    # Show config
    print(f"config:  {CONFIG_PATH}")
    default = cfg.get("default")
    if not spaces:
        print("  (no spaces configured)")
        return
    for alias, uuid in sorted(spaces.items()):
        marker = " *" if alias == default else ""
        print(f"  {alias:20s} → {uuid}{marker}")
    print()
    print(f"env:     SILO_SPACE={os.environ.get('SILO_SPACE', '(not set)')}")


def cmd_spaces(args):
    """List configured spaces (display only)."""
    cfg = load_config()
    spaces = cfg.get("spaces", {})
    default = cfg.get("default")
    print(f"config:  {CONFIG_PATH}")
    if not spaces:
        print("  (no spaces configured)")
        return
    for alias, uuid in sorted(spaces.items()):
        marker = " *" if alias == default else ""
        print(f"  {alias:20s} → {uuid}{marker}")
    print()
    print(f"env:     SILO_SPACE={os.environ.get('SILO_SPACE', '(not set)')}")


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
        description="Query a remote cohub-silo data server (multi-space support)",
    )
    parser.add_argument("--space", help="Space alias or UUID (overrides default)")

    sub = parser.add_subparsers(dest="command")

    # config
    p_cfg = sub.add_parser("config", help="Manage silo spaces config")
    p_cfg.add_argument("--space", help="Space UUID or alias to add/update")
    p_cfg.add_argument("--alias", help="Alias name for this space (default: 'default')")
    p_cfg.add_argument("--default", help="Set default space alias")
    p_cfg.add_argument("--remove", help="Remove a space by alias")

    # spaces (alias for config display)
    sub.add_parser("spaces", help="List configured spaces (alias: config)")

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

    t0 = time.time()
    cmds = {
        "config": cmd_config,
        "spaces": cmd_spaces,
        "collections": cmd_collections,
        "topics": cmd_topics,
        "stats": cmd_stats,
        "search": cmd_search,
        "sample": cmd_sample,
        "get": cmd_get,
    }
    cmds[args.command](args)
    elapsed = int((time.time() - t0) * 1000)
    if args.command not in ("config", "spaces"):
        print(f"\n⏱  {elapsed}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
