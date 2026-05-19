# cohub-silo-client

> CLI + agent skill for querying a remote [cohub-silo](https://github.com/kjx-talesofai/cohub-silo) data server from any Cohub Space or local machine.

## Quickstart

```bash
# Install as a skill (in Cohub)
npx skills add github.com/kjx-talesofai/cohub-silo-client -g -y

# Or clone standalone
git clone https://github.com/kjx-talesofai/cohub-silo-client.git
cd cohub-silo-client

# Configure target silo
silo-client config --space 98d87d78-047f-4298-9b7e-ea12ef39f0ae

# Explore
silo-client collections
silo-client topics
silo-client stats

# Search
silo-client search --q "审判庭"
silo-client search --q "Tyrant Star" --topic warhammer40k

# Sample
silo-client sample --topic ai-art --limit 3

# Read
silo-client get 78 --content
```

## How it works

```
You (or your agent)                        Silo owner's Space
┌──────────────────────┐     HTTPS        ┌────────────────────┐
│ silo-client config   │ ───────────────→ │ cohub-silo server  │
│ silo-client search   │                  │ (Flask, port 5173) │
│ silo-client sample   │                  │                    │
│ silo-client get      │ ←─────────────── │ SQLite + FTS5      │
│ silo-client topics   │     JSON         │ 513+ items         │
└──────────────────────┘                  └────────────────────┘
```

The silo is **public by design** — no API keys, no auth. Anyone who knows the space UUID can query it.

## Requirements

- Python 3.7+ (stdlib only — no pip install needed)
- Network access to `*.cohub.run`

## Commands

| Command | Description |
|---|---|
| `config` | Show/set target silo space UUID |
| `collections` | List collections with item counts |
| `topics` | List topics with item counts |
| `stats` | Daily indexing statistics |
| `search --q "..."` | Full-text search with filters |
| `sample` | Random sample of items |
| `get <id>` | Single item metadata (+ `--content` for full text) |

## Config

Space UUID is resolved in order:

1. `--space` CLI flag
2. `SILO_SPACE` environment variable
3. `~/.silo-client.json` config file

```bash
# Persistent config
silo-client config --space <uuid>

# One-shot
silo-client --space <uuid> search --q "keyword"

# Env var
export SILO_SPACE=<uuid>
silo-client collections
```

## For silo owners

To make your silo queryable by others, share:

1. This repo link: `github.com/kjx-talesofai/cohub-silo-client`
2. Your space UUID

That's it. Your colleagues install the skill and point it at your space.

## License

UNLICENSED
