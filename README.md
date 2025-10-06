# pwpush CLI

<div align="center">

[![Build status](https://github.com/pglombardo/pwpush-cli/workflows/build/badge.svg?branch=master&event=push)](https://github.com/pglombardo/pwpush-cli/actions?query=workflow%3Abuild)
[![Python Version](https://img.shields.io/pypi/pyversions/pwpush.svg)](https://pypi.org/project/pwpush/)
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/pglombardo/pwpush-cli/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pglombardo/pwpush-cli/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/pglombardo/pwpush-cli/releases)
[![License](https://img.shields.io/github/license/pglombardo/pwpush-cli)](https://github.com/pglombardo/pwpush/blob/master/LICENSE)

**Command Line Interface for Password Pusher**
Secure information distribution with automatic expiration controls.

</div>

## Overview

The `pwpush` CLI is a powerful command-line tool that interfaces with [Password Pusher](https://pwpush.com) instances for secure information distribution. It supports both the hosted services (eu.pwpush.com, us.pwpush.com) and self-hosted instances.

### Why Secure Information Distribution?

Traditional communication tools create permanent digital footprints that can be exploited years later. Password Pusher sidesteps this by creating:

- **Self-destructing shareable links** that auto-expire after a preset number of views
- **Time-based expiration** that automatically deletes content after a set duration  
- **Zero permanent storage** - once expired, the information is completely removed
- **Full audit trails** so you know exactly who accessed what and when

### Key Features

- 🔐 **Secure Information Distribution**: Self-destructing links for passwords, secrets, and files with automatic expiration and complete audit trails.
- 🌐 **Multi-Instance Support**: Works with eu.pwpush.com, us.pwpush.com, or your own instance
- 🔑 **Authentication**: Full API integration with user accounts
- 📊 **Audit Logs**: Track access and usage of distributed content
- 🎯 **Flexible Expiration**: Set expiration by views, days, or both
- 📁 **File Support**: Distribute files securely with the same expiration controls and audit logs
- 🎨 **Rich Output**: Beautiful terminal output with tables and formatting

## Installation

```bash
pip install pwpush
```

**Requirements**: Python 3.9.2 or higher

## Quick Start

### 1. Basic Usage (Anonymous)

```bash
# Push a password (interactive mode)
pwpush push

# Push a password directly
pwpush push --secret "mypassword123"

# Auto-generate a secure password
pwpush push --auto

# Push with custom expiration (7 days, 5 views)
pwpush push --secret "mypassword" --days 7 --views 5
```

### 2. Configure Your Instance

The CLI works with multiple Password Pusher instances:

```bash
# Use the EU instance
pwpush config set --key url --value https://eu.pwpush.com

# Use the US instance  
pwpush config set --key url --value https://us.pwpush.com

# Use your own self-hosted instance
pwpush config set --key url --value https://pwpush.yourdomain.com
```

### 3. Authentication (Optional)

For advanced features like listing pushes and audit logs, authenticate with your account:

```bash
# Login with your credentials
pwpush login

# Or set credentials manually
pwpush config set --key email --value your@email.com
pwpush config set --key token --value your_api_token
```

Get your API token from: https://pwpush.com/en/users/token

## Common Commands

### Pushing Content

```bash
# Push a password with custom settings
pwpush push --secret "password123" --days 3 --views 10 --deletable

# Push as URL (for sharing links)
pwpush push --secret "https://example.com" --kind url

# Push as QR code
pwpush push --secret "QR data content" --kind qr

# Push a file
pwpush push-file document.pdf --days 7 --views 5

# Push with a reference note (requires authentication)
pwpush push --secret "password" --note "Employee onboarding - John Doe"

# Require click-through for retrieval (prevents URL scanners)
pwpush push --secret "password" --retrieval-step
```

### Managing Pushes

```bash
# List your active pushes (requires authentication)
pwpush list

# List expired pushes
pwpush list --expired

# View audit log for a specific push
pwpush audit <url_token>

# Expire a push immediately
pwpush expire <url_token>
```

### Configuration

```bash
# View current configuration
pwpush config show

# Set default expiration settings
pwpush config set --key expire_after_days --value 7
pwpush config set --key expire_after_views --value 10

# Enable JSON output by default
pwpush config set --key json --value true

# Logout and clear credentials
pwpush logout
```

## Advanced Usage

### Push Types

The `--kind` parameter allows you to specify the type of content being pushed:

```bash
# Text/Password (default)
pwpush push --secret "mypassword" --kind text

# URL - for sharing links that will be displayed as clickable URLs
pwpush push --secret "https://example.com" --kind url

# QR Code - for content that will be displayed as a QR code
pwpush push --secret "QR data content" --kind qr

# File - automatically set when using push-file command
pwpush push-file document.pdf  # kind is automatically set to "file"
```

### JSON Output

```bash
# Get JSON output for scripting
pwpush --json push --secret "password"
pwpush --json list
```

### Verbose and Debug Modes

```bash
# Enable verbose output
pwpush --verbose push --secret "password"

# Enable debug mode for troubleshooting
pwpush --debug push --secret "password"
```

### Batch Operations

```bash
# Generate and distribute multiple passwords
for i in {1..5}; do
  pwpush --json push --auto --note "Batch password $i"
done
```

## Configuration Reference

### Instance Settings

| Key | Description | Example |
|-----|-------------|---------|
| `url` | Password Pusher instance URL | `https://eu.pwpush.com` |
| `email` | Your account email | `user@example.com` |
| `token` | Your API token | `abc123...` |

### Expiration Settings

| Key | Description | Valid Values |
|-----|-------------|--------------|
| `expire_after_days` | Default days until expiration | 1-90 |
| `expire_after_views` | Default views until expiration | 1-100 |
| `retrieval_step` | Require click-through for retrieval | true/false |
| `deletable_by_viewer` | Allow viewers to delete content | true/false |

### CLI Settings

| Key | Description | Valid Values |
|-----|-------------|--------------|
| `json` | Output in JSON format | true/false |
| `verbose` | Enable verbose output | true/false |

## Examples

### Developer Workflow

```bash
# Push database credentials with team
pwpush push --secret "db_password_123" --days 1 --views 3 --note "Staging DB - expires in 24h"

# Push API keys securely
pwpush push --secret "sk_live_..." --days 7 --views 1 --note "Production API Key"

# Share deployment URLs as clickable links
pwpush push --secret "https://staging.example.com/deploy" --kind url --days 1 --views 5
```

### System Administration

```bash
# Push temporary access credentials
pwpush push --auto --days 1 --views 1 --note "Emergency access - $(date)"

# Push configuration files
pwpush push-file /etc/nginx/nginx.conf --days 3 --views 5
```

### Team Collaboration

```bash
# Push deployment secrets
pwpush push --secret "deploy_token" --days 1 --views 10 --note "Release v2.1.0"

# Push sensitive documents
pwpush push-file sensitive_document.pdf --days 7 --views 3 --retrieval-step
```

## Troubleshooting

### Common Issues

**Connection Errors**
```bash
# Check your instance URL
pwpush config show

# Test connectivity
pwpush --debug push --secret "test"
```

**Authentication Issues**
```bash
# Verify your credentials
pwpush config show

# Re-login
pwpush logout
pwpush login
```

**Permission Errors**
```bash
# Check file permissions when uploading files
ls -la your_file.txt
pwpush push-file your_file.txt
```

### Getting Help

```bash
# View all available commands
pwpush --help

# Get help for specific commands
pwpush push --help
pwpush config --help
```

## Security Notes

- Passwords and secrets are encrypted before transmission
- All communication uses HTTPS
- Content is automatically deleted after expiration
- API tokens should be kept secure and not shared
- Use `--retrieval-step` to prevent URL scanners from consuming views

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- **Password Pusher**: https://pwpush.com
- **Documentation**: https://docs.pwpush.com
- **GitHub Repository**: https://github.com/pglombardo/pwpush-cli
- **Open Source Project**: https://github.com/pglombardo/PasswordPusher

## About Apnotic

This CLI tool is built by **Apnotic**.

- **Company Homepage**: https://apnotic.com
- **Password Pusher Pro**: https://pwpush.com
