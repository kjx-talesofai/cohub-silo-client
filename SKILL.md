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
# 1. Install as a skill (makes it available to Claude Code agents)
npx skills add github.com/kjx-talesofai/cohub-silo-client -g -y

# 2. Run the CLI directly
python3 ~/.claude/skills/silo-client/cli.py config --space <space-uuid> --alias <name>
# e.g. python3 ~/.claude/skills/silo-client/cli.py config --space <uuid> --alias kjx

# Add more silos with different aliases
python3 ~/.claude/skills/silo-client/cli.py config --space <another-uuid> --alias colleague

# Set default
python3 ~/.claude/skills/silo-client/cli.py config --default kjx

# Or use env var (accepts alias or raw UUID)
export SILO_SPACE=kjx
```

> **Note:** `npx skills add` registers the skill for Claude Code agents. It does **not** install a global `silo-client` shell command. Use `python3 ~/.claude/skills/silo-client/cli.py` to run the CLI directly, or create a symlink manually (see Troubleshooting).

**Supports multiple spaces.** Add as many silos as you want with different aliases, and switch between them with `--space <alias>`.

The silo URL is always: `https://s-{space-uuid}-5173.cohub.run`

## CLI reference

```bash
# Config (multi-space)
python3 ~/.claude/skills/silo-client/cli.py config                         # Show all configured spaces
python3 ~/.claude/skills/silo-client/cli.py spaces                         # Same as config
python3 ~/.claude/skills/silo-client/cli.py config --space <uuid> --alias <name>   # Add a space
python3 ~/.claude/skills/silo-client/cli.py config --default <alias>               # Set default
python3 ~/.claude/skills/silo-client/cli.py config --remove <alias>                # Remove a space

# Discovery (--space <alias|uuid> overrides default)
python3 ~/.claude/skills/silo-client/cli.py collections                    # Use default space
python3 ~/.claude/skills/silo-client/cli.py collections --space kjx        # Explicit space by alias
python3 ~/.claude/skills/silo-client/cli.py topics                         # List all topics with item counts
python3 ~/.claude/skills/silo-client/cli.py stats                          # Daily indexing stats

# Search & retrieval
python3 ~/.claude/skills/silo-client/cli.py search --q "keyword"           # Full-text search (supports CJK)
python3 ~/.claude/skills/silo-client/cli.py search --q "keyword" --topic tech --collection my-docs --limit 10
python3 ~/.claude/skills/silo-client/cli.py search --q "keyword" --sort random  # Sort: latest | random | relevant

# Random sampling
python3 ~/.claude/skills/silo-client/cli.py sample                         # 5 random items
python3 ~/.claude/skills/silo-client/cli.py sample --topic warhammer40k --limit 3
python3 ~/.claude/skills/silo-client/cli.py sample --collection my-docs --limit 10

# Single item
python3 ~/.claude/skills/silo-client/cli.py get 42                         # Item metadata
python3 ~/.claude/skills/silo-client/cli.py get 42 --content               # Include full content (for reading)
```

## Agent usage guidelines

When a user asks you to use silo-client:

1. **First, ensure config is set:**
   ```bash
   python3 ~/.claude/skills/silo-client/cli.py config
   ```
   If no spaces are configured, ask the user for the space UUID.
   Users may have multiple silos configured — respect the alias they want to use.

2. **Discover what's available:**
   ```bash
   python3 ~/.claude/skills/silo-client/cli.py collections
   python3 ~/.claude/skills/silo-client/cli.py topics
   ```
   This helps you understand the knowledge domains before searching.

3. **Search intelligently:**
   - Use `--q` for full-text search. CJK (Chinese/Japanese/Korean) works natively.
   - Narrow with `--topic` and `--collection` when you know the domain.
   - Use `--sort random` for discovery/serendipity browsing.

4. **Retrieve content when needed:**
   - `python3 ~/.claude/skills/silo-client/cli.py get <id> --content` returns the full text content.
   - For large content, pipe through `head` or `less` if needed.

5. **Sample for exploration:**
   - `python3 ~/.claude/skills/silo-client/cli.py sample --topic <t>` gives a quick taste of a topic without search.

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

- **`command not found: silo-client`**: The `npx skills add` command registers the skill for Claude Code but does not create a global shell command. Run the CLI directly with:
  ```bash
  python3 ~/.claude/skills/silo-client/cli.py <command>
  ```
  Or create a symlink for convenience:
  ```bash
  chmod +x ~/.claude/skills/silo-client/cli.py
  mkdir -p ~/.local/bin
  ln -s ~/.claude/skills/silo-client/cli.py ~/.local/bin/silo-client
  export PATH="$HOME/.local/bin:$PATH"
  ```
- **`✗ connection error`**: Verify space UUID is correct and the silo server is running.
- **`✗ HTTP 404`**: The endpoint doesn't exist — check the space UUID.
- **`✗ HTTP 429`**: Rate limited. Wait 60 seconds before retrying.
- **`✗ no silo space configured`**: Run `python3 ~/.claude/skills/silo-client/cli.py config --space <uuid>` first.
