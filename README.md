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
  
<strong>This utility is currently in pre-beta form.  Most core functionality exists and works but needs a bit of polishing.</strong>

</div>

# Overview

This command line utility exists to interface with [pwpush.com](https://pwpush.com) or any privately hosted instance of [Password Pusher](https://github.com/pglombardo/PasswordPusher).

It uses the JSON API of Password Pusher to create, view, retrieve and manage pushes.  It can do this anonymously or via the authenticated API.

# Installation

`pip install pwpush`

* Required Python version >3.5

# Screenshots

## Help

![](https://disznc.s3.amazonaws.com/pwpush-cli-help.png)

## List

![](https://disznc.s3.amazonaws.com/pwpush-cli-list.png)

## Audit

![](https://disznc.s3.amazonaws.com/pwpush-cli-audit.png)

## Config

![](https://disznc.s3.amazonaws.com/pwpush-cli-config.png)
