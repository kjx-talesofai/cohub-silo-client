---
name: silo-client
description: Query a remote cohub-silo data server. Search, sample, and retrieve items from a public silo by space UUID. No authentication needed.
---

# silo-client

A CLI + agent skill for querying a remote [cohub-silo](https://github.com/kjx-talesofai/cohub-silo) data server.

## What it does

cohub-silo is a data server running inside a Cohub Space. It indexes documents, images, audio, video, and URLs into a SQLite + FTS5 database with CJK-capable full-text search, and exposes a public REST API.

**silo-client** is the agent-friendly CLI to query those silos. No auth — silos are public by design.

## Setup

```bash
# 1. Install
npx skills add github.com/kjx-talesofai/cohub-silo-client -g -y

# 2. Configure the target silo's space UUID (ask the silo owner)
silo-client config --space <space-uuid>
# OR set env:
export SILO_SPACE=<space-uuid>
```

The silo URL is always: `https://s-{space-uuid}-5173.cohub.run`

## CLI reference

```bash
# Config
silo-client config                         # Show current config
silo-client config --space <uuid>          # Set target space

# Discovery
silo-client collections                    # List all collections (names, IDs, topics, item counts)
silo-client topics                         # List all topics with item counts
silo-client stats                          # Daily indexing stats

# Search & retrieval
silo-client search --q "keyword"           # Full-text search (supports CJK)
silo-client search --q "keyword" --topic tech --collection my-docs --limit 10
silo-client search --q "keyword" --sort random  # Sort: latest | random | relevant

# Random sampling
silo-client sample                         # 5 random items
silo-client sample --topic warhammer40k --limit 3
silo-client sample --collection my-docs --limit 10

# Single item
silo-client get 42                         # Item metadata
silo-client get 42 --content               # Include full content (for reading)
```

## Agent usage guidelines

When a user asks you to use silo-client:

1. **First, ensure config is set:**
   ```bash
   silo-client config
   ```
   If space is not configured, ask the user for the space UUID.

2. **Discover what's available:**
   ```bash
   silo-client collections
   silo-client topics
   ```
   This helps you understand the knowledge domains before searching.

3. **Search intelligently:**
   - Use `--q` for full-text search. CJK (Chinese/Japanese/Korean) works natively.
   - Narrow with `--topic` and `--collection` when you know the domain.
   - Use `--sort random` for discovery/serendipity browsing.

4. **Retrieve content when needed:**
   - `silo-client get <id> --content` returns the full text content.
   - For large content, pipe through `head` or `less` if needed.

5. **Sample for exploration:**
   - `silo-client sample --topic <t>` gives a quick taste of a topic without search.

## Rate limits

The silo enforces **60 requests per minute** per IP. Be mindful of rate limits — batch your queries, don't loop aggressively.

## Architecture

```
┌──────────────────┐     HTTPS      ┌─────────────────────┐
│  silo-client CLI │ ────────────→  │  cohub-silo server  │
│  (your space)    │                │  (owner's space)    │
└──────────────────┘                │  port 5173          │
                                    │  SQLite + FTS5      │
                                    └─────────────────────┘
```

## Troubleshooting

- **`✗ connection error`**: Verify space UUID is correct and the silo server is running.
- **`✗ HTTP 404`**: The endpoint doesn't exist — check the space UUID.
- **`✗ HTTP 429`**: Rate limited. Wait 60 seconds before retrying.
- **`✗ no silo space configured`**: Run `silo-client config --space <uuid>` first.
