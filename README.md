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

**Command Line Interface for Password Pusher** - Securely share passwords, secrets, and files with expiration controls.

</div>

## Overview

The `pwpush` CLI is a powerful command-line tool that interfaces with [Password Pusher](https://pwpush.com) instances to securely share sensitive information. It supports both the hosted service at pwpush.com and self-hosted instances.

### Key Features

- 🔐 **Secure Sharing**: Share passwords, secrets, and files with automatic expiration
- 🌐 **Multi-Instance Support**: Works with pwpush.com, eu.pwpush.com, us.pwpush.com, or your own instance
- 🔑 **Authentication**: Full API integration with user accounts
- 📊 **Audit Logs**: Track access and usage of shared content
- 🎯 **Flexible Expiration**: Set expiration by views, days, or both
- 📁 **File Support**: Share files securely with the same expiration controls
- 🎨 **Rich Output**: Beautiful terminal output with tables and formatting

## Installation

```bash
pip install pwpush
```

**Requirements**: Python 3.9.2 or higher

## Quick Start

### 1. Basic Usage (Anonymous)

```bash
# Share a password (interactive mode)
pwpush push

# Share a password directly
pwpush push --secret "mypassword123"

# Auto-generate a secure password
pwpush push --auto

# Share with custom expiration (7 days, 5 views)
pwpush push --secret "mypassword" --days 7 --views 5
```

### 2. Configure Your Instance

The CLI works with multiple Password Pusher instances:

```bash
# Use the main hosted service (default)
pwpush config set --key url --value https://pwpush.com

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

### Sharing Content

```bash
# Share a password with custom settings
pwpush push --secret "password123" --days 3 --views 10 --deletable

# Share a file
pwpush push-file document.pdf --days 7 --views 5

# Share with a reference note (requires authentication)
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
# Generate and share multiple passwords
for i in {1..5}; do
  pwpush --json push --auto --note "Batch password $i"
done
```

## Configuration Reference

### Instance Settings

| Key | Description | Example |
|-----|-------------|---------|
| `url` | Password Pusher instance URL | `https://pwpush.com` |
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
# Share database credentials with team
pwpush push --secret "db_password_123" --days 1 --views 3 --note "Staging DB - expires in 24h"

# Share API keys securely
pwpush push --secret "sk_live_..." --days 7 --views 1 --note "Production API Key"
```

### System Administration

```bash
# Share temporary access credentials
pwpush push --auto --days 1 --views 1 --note "Emergency access - $(date)"

# Share configuration files
pwpush push-file /etc/nginx/nginx.conf --days 3 --views 5
```

### Team Collaboration

```bash
# Share deployment secrets
pwpush push --secret "deploy_token" --days 1 --views 10 --note "Release v2.1.0"

# Share sensitive documents
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
