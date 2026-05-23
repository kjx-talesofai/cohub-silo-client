<p align="center">
  <img src="https://camo.githubusercontent.com/3e816c82f93843017c24bcc6cc25a3e8f6becd41c6435e39de4dbc11b0ca1485/68747470733a2f2f6173736574732e687970657273616d706c696e672e636f6d2f68797065722d73616d706c696e672d322e6a7067" alt="hyper-sampling" height="50"/>
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/kjx-talesofai/claude-skill-hypersampling/master/neta_logo.png" alt="neta.art" height="50"/>
</p>

<p align="center">
  <strong><a href="https://hypersampling.com">Jiaxin Kou 寇佳新</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://www.neta.art">Neta Art 捏Ta</a></strong>
  &nbsp;·&nbsp;
  <a href="https://github.com/kjx-talesofai">GitHub @kjx-talesofai</a>
</p>

---

# cohub-silo-client

> CLI + agent skill for querying a remote [cohub-silo](https://github.com/kjx-talesofai/cohub-silo) data server from any Cohub Space or local machine.

## Quickstart

```bash
# Install as a skill (in Cohub)
npx skills add github.com/kjx-talesofai/cohub-silo-client -g -y

# Or clone standalone
git clone https://github.com/kjx-talesofai/cohub-silo-client.git
cd cohub-silo-client

# Run the CLI directly (npx skills add does not create a global command)
python3 cli.py config --space <your-space-uuid> --alias kjx
python3 cli.py config --space <another-uuid> --alias colleague

# Explore
python3 cli.py collections                   # uses default
python3 cli.py collections --space colleague # explicit space
python3 cli.py topics
python3 cli.py stats

# Search
python3 cli.py search --q "审判庭"
python3 cli.py search --q "Tyrant Star" --topic warhammer40k

# Sample
python3 cli.py sample --topic ai-art --limit 3

# Read
python3 cli.py get 78 --content
```

> **Note:** `npx skills add` registers the skill for Claude Code agents but does not install a global `silo-client` shell command. Use `python3 cli.py` (or `python3 ~/.claude/skills/silo-client/cli.py`) directly. To add it to your PATH, see [Troubleshooting](#troubleshooting).

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
| `config` | Show/add/remove/rename spaces (multi-space support) |
| `spaces` | Alias for `config` — list configured spaces |
| `collections` | List collections with item counts |
| `topics` | List topics with item counts |
| `stats` | Daily indexing statistics |
| `search --q "..."` | Full-text search with filters |
| `sample` | Random sample of items |
| `get <id>` | Single item metadata (+ `--content` for full text) |

## Multi-space config

Supports multiple silos with aliases. Config is stored in `~/.silo-client.json`:

```json
{
  "spaces": {
    "kjx": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "alice": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  },
  "default": "kjx"
}
```

Space resolution order:

1. `--space <alias|uuid>` CLI flag (per-command)
2. `SILO_SPACE` environment variable (alias or UUID)
3. `default` alias in `~/.silo-client.json`

```bash
# Add spaces
python3 cli.py config --space <uuid> --alias kjx
python3 cli.py config --space <uuid> --alias alice

# Set default
python3 cli.py config --default alice

# Remove
python3 cli.py config --remove alice

# One-shot override
python3 cli.py --space kjx search --q "keyword"

# Env var
export SILO_SPACE=kjx
python3 cli.py collections

# Raw UUID always works too
python3 cli.py --space xxxxxxxx-... collections
```

## Troubleshooting

**`command not found: silo-client`**

The `npx skills add` command registers the skill for Claude Code but does not create a global shell command. Use the direct path:

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

## For silo owners

To make your silo queryable by others, share:

1. This repo link: `github.com/kjx-talesofai/cohub-silo-client`
2. Your space UUID

That's it. Your colleagues install the skill and point it at your space.

## License

MIT © 2026 koujiaxin / Hyper Sampling
