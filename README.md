# pwpush

<div align="center">

[![Build status](https://github.com/pglombardo/pwpush-cli/workflows/build/badge.svg?branch=master&event=push)](https://github.com/pglombardo/pwpush-cli/actions?query=workflow%3Abuild)
[![Python Version](https://img.shields.io/pypi/pyversions/pwpush.svg)](https://pypi.org/project/pwpush/)
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/pglombardo/pwpush-cli/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pglombardo/pwpush-cli/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/pglombardo/pwpush-cli/releases)
[![License](https://img.shields.io/github/license/pglombardo/pwpush-cli)](https://github.com/pglombardo/pwpush/blob/master/LICENSE)

Command Line Interface to Password Pusher.
  
<strong>This utility is currently in BETA.  Most core functionality exists and works but needs a bit of polishing.</strong>

</div>

# Overview

This command line utility exists to interface with [pwpush.com](https://pwpush.com) or any privately hosted instance of [Password Pusher](https://github.com/pglombardo/PasswordPusher).

It uses the JSON API of Password Pusher to create, view, retrieve and manage pushes.  It can do this anonymously or via the authenticated API.

# Installation

`pip install pwpush`

* Required Python version >3.8

# Quickstart

## pwpush.com

```sh
# Push a password to pwpush.com
> pwpush push mypassword
https://pwpush.com/en/p/uzij1ybk6rol

# Get JSON output instead
> pwpush --json=true push mypassword
{'url': 'https://pwpush.com/en/p/uzij1ybk6rol'}
```
## Private Self Hosted Instance

```sh
# Point this tool to your privately hosted instance
> pwpush config set --key url --value https://pwpush.mydomain.secure
# ...and push away...
> pwpush push mypassword
https://pwpush.mydomain.secure/en/p/uzij1ybk6rol
```

## Authentication with API Token

Get [the API token associated with your account](https://pwpush.com/en/users/token) and add it to the CLI configuration.

```sh
# Get your API token at [/en/users/token](https://pwpush.com/en/users/token)

# Configure the CLI with your email and API token
> pwpush config set --key email --value <pwpush login email>
> pwpush config set --key token --value <api token from /en/users/token>

# List active pushes in your dashboard
> pwpush list

=== Active Pushes:
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Secret URL Token   ┃ Note                   ┃ Views ┃ Days  ┃ Deletable by Viewer ┃ Retrieval Step ┃ Created                ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ uzij1ybk6rol       │ Push prior to Digital  │ 6/100 │ 28/87 │ True                │ False          │ 10/08/2022, 11:55:49   │
│                    │ Ocean migration 3      │       │       │                     │                │ UTC                    │
│ sfoej1fwlfljwlf    │ Push prior to Digital  │ 0/100 │ 28/90 │ True                │ True           │ 10/08/2022, 11:55:19   │
│                    │ Ocean migration 2      │       │       │                     │                │ UTC                    │
└────────────────────┴────────────────────────┴───────┴───────┴─────────────────────┴────────────────┴────────────────────────┘

# Get the audit log for a push
> pwpush audit <secret url token>
```

## Show Configuration

```
> pwpush config show

=== Instance Settings:
Specify your credentials and even your private Password Pusher instance here.

┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key   ┃ Value              ┃ Description                                                            ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ URL   │ https://pwpush.com │ The Password Pusher instance to work with.                             │
│ email │ Not Set            │ E-mail address of your account on Password Pusher.                     │
│ token │ Not Set            │ API token from your account.  e.g. 'https://pwpush.com/en/users/token' │
└───────┴────────────────────┴────────────────────────────────────────────────────────────────────────┘

=== Expiration Settings:
Pushes created with this tool will have these expiration settings.

If not specified, the application defaults will be used.
Command line options override these settings.  See 'pwpush push --help'

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key                 ┃ Value   ┃ Valid Values ┃ Description                                                      ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ expire_after_days   │ Not Set │ 1-90         │ Number of days each push will be valid for.                      │
│ expire_after_views  │ Not Set │ 1-100        │ Number of views each push will be valid for.                     │
│ retrieval_step      │ Not Set │ true/false   │ Require users to perform a click through to retrieve a push.     │
│ deletable_by_viewer │ Not Set │ true/false   │ Enables/disables a user from deleting a push payload themselves. │
└─────────────────────┴─────────┴──────────────┴──────────────────────────────────────────────────────────────────┘

=== CLI Settings:
Behavior settings for this CLI.

Command line options override these settings.  See 'pwpush --help'

┏━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key     ┃ Value ┃ Valid Values ┃ Description                      ┃
┡━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ json    │ False │ true/false   │ CLI outputs results in JSON.     │
│ verbose │ False │ true/false   │ More verbosity when appropriate. │
└─────────┴───────┴──────────────┴──────────────────────────────────┘

To change the above the values see: 'pwpush config set --help'

User config is saved in '/Users/pglombardo/Library/Application Support/pwpush/config.ini'
```

# Screenshots

## Help

![](https://pwpush.fra1.cdn.digitaloceanspaces.com/cli/pwpush-cli-help.png)

## List

![](https://pwpush.fra1.cdn.digitaloceanspaces.com/cli/pwpush-cli-list.png)

## Audit

![](https://pwpush.fra1.cdn.digitaloceanspaces.com/cli/pwpush-cli-audit.png)

## Config

![](https://pwpush.fra1.cdn.digitaloceanspaces.com/cli/pwpush-cli-config.png)
