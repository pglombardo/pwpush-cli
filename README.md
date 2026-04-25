# pwpush CLI

<div align="center">

[![Build status](https://github.com/pglombardo/pwpush-cli/workflows/build/badge.svg?branch=master&event=push)](https://github.com/pglombardo/pwpush-cli/actions?query=workflow%3Abuild)
[![Python Version](https://img.shields.io/pypi/pyversions/pwpush.svg)](https://pypi.org/project/pwpush/)
[![PyPI](https://img.shields.io/pypi/v/pwpush)](https://pypi.org/project/pwpush/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/github/license/pglombardo/pwpush-cli)](https://github.com/pglombardo/pwpush/blob/master/LICENSE)

**The elegant way to share secrets from the command line.**
<br>
Self-destructing links for passwords, files, and sensitive data.

[Installation](#installation) • [Quick Start](#quick-start) • [Features](#features) • [Documentation](https://docs.pwpush.com)

</div>

---

## What is pwpush?

`pwpush` is a beautiful, intuitive CLI for [Password Pusher](https://pwpush.com) — the secure way to share passwords, secrets, and files. Instead of sending sensitive data over email or Slack, create self-destructing links that automatically expire after a set number of views or days.

```bash
# Share a password securely
$ pwpush push --secret "my-sensitive-payload"
The secret has been pushed to:
https://us.pwpush.com/p/abc123xyz

# Or pipe in content from a file or command
$ cat secret.txt | pwpush push
The secret has been pushed to:
https://us.pwpush.com/p/xyz789abc
```

---

## Installation

```bash
pip install pwpush
```

Requires Python 3.10 or higher.

---

## Quick Start

### 1. Run the Config Wizard 🧙

The easiest way to get started. The wizard guides you through selecting your instance, setting up authentication, and configuring defaults:

```bash
$ pwpush config wizard

Password Pusher CLI Setup
This wizard will create your local pwpush configuration.

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Option ┃ Instance              ┃ Description             ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1      │ https://eu.pwpush.com │ EU hosted: Pro features │
│ 2      │ https://us.pwpush.com │ US hosted: Pro features │
│ 3      │ https://oss.pwpush.com│ OSS: EU Data Residency  │
│ 4      │ Custom                │ Self-hosted instance    │
└────────┴───────────────────────┴─────────────────────────┘
```

### 2. Push Your First Secret

```bash
# Interactive mode — just type and go
$ pwpush push
Enter secret: ********
The secret has been pushed to:
https://pwpush.com/p/xyz789abc

# Or pass it directly
$ pwpush push --secret "my-password" --days 3 --views 5

# Auto-generate a secure password
$ pwpush push --auto
Passphrase is: battery horse staple correct
https://pwpush.com/p/auto123gen
```

### 3. Share Files

```bash
$ pwpush push-file secret-document.pdf --days 7
https://pwpush.com/f/file456token
```

---

## Why pwpush?

### 🔐 Security First
- Zero permanent storage — data is encrypted and auto-deleted
- Full audit trails — see exactly who accessed what and when
- Prevent URL scanners with `--retrieval-step`

### ✨ Developer Experience
- **Auto-negotiating API** — seamlessly works with v2 and legacy instances
- **Beautiful output** — rich tables, colors, and formatting
- **JSON mode** — perfect for scripts and CI/CD pipelines

### 🌍 Multi-Instance Support
Works with hosted services or your own instance:
- `eu.pwpush.com` — EU-hosted Pro
- `us.pwpush.com` — US-hosted Pro  
- `oss.pwpush.com` — Free OSS tier
- Self-hosted — Your own domain

---

## Everyday Commands

```bash
# Quick password share
pwpush push --secret "db-password" --days 1 --views 3

# Share a link as a clickable URL
pwpush push --secret "https://staging.example.com" --kind url

# Push with a reference note (for your records)
pwpush push --secret "password" --note "AWS Root - Production"

# List your active pushes
pwpush list

# View audit trail
pwpush audit <url_token>

# Expire a push immediately
pwpush expire <url_token>
```

---

## Pro Features

For [Password Pusher Pro](https://pwpush.com) users with authenticated access:

```bash
# Email notifications when push is accessed
pwpush push --secret "password" --notify "admin@company.com"

# Multi-language notifications
pwpush push --secret "password" --notify "admin@company.com" --notify-locale "es"

# Multiple accounts per API token (automatically detected)
```

---

## Configuration

The CLI stores settings in `~/.config/pwpush/config.ini` with restricted permissions (0o600):

```bash
# Guided setup (recommended)
pwpush config wizard

# View current settings
pwpush config

# Quick updates
pwpush config set expire_after_days 7
pwpush config set expire_after_views 10

# Reset everything
pwpush config delete
```

---

## Advanced Usage

### JSON Output for Scripting

```bash
# Perfect for automation
$ pwpush --json push --secret "password"
{"url":"https://pwpush.com/p/abc123","url_token":"abc123","expire_after_days":7}

# Chain with other tools
$ pwpush --json push --auto | jq -r '.url' | pbcopy
```

### Pipe Input

```bash
# Pipe passwords directly
cat secret.txt | pwpush push

# From environment variables
pwpush push --secret "$DATABASE_PASSWORD"
```

### Debug Mode

```bash
# Troubleshoot connectivity
pwpush --debug push --secret "test"
```

---

## API Compatibility

The CLI automatically detects your instance's API version:

1. Probes `GET /api/v2/version` on first run
2. Uses **API v2** if available (modern, feature-rich)
3. Falls back to **legacy** endpoints for older instances
4. Caches the result for 1 hour to avoid repeated probes

Works with:
- ✅ Password Pusher Pro (any version)
- ✅ Open Source v2.4.2+ with API v2
- ✅ Older instances via legacy fallback

---

## Security Notes

- All data is encrypted in transit (HTTPS) and at rest
- Content is permanently deleted after expiration
- API tokens are stored with 0o600 permissions
- Use `--retrieval-step` to prevent bot consumption
- Passphrase protection available with `--passphrase`

---

## Links & Resources

| Resource | Link |
|----------|------|
| 📖 Full Documentation | [docs.pwpush.com](https://docs.pwpush.com) |
| 🌐 Password Pusher | [pwpush.com](https://pwpush.com) |
| 💻 Open Source Project | [github.com/pglombardo/PasswordPusher](https://github.com/pglombardo/PasswordPusher) |
| 🐛 Issue Tracker | [github.com/pglombardo/pwpush-cli/issues](https://github.com/pglombardo/pwpush-cli/issues) |

---

## About

Built by [Apnotic](https://apnotic.com) — empowering secure information distribution.

- Homepage: [apnotic.com](https://apnotic.com)
- SaaS: [pwpush.com](https://pwpush.com)
- License: MIT
