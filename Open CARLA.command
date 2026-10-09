#!/bin/zsh
set -eu
cd "${0:A:h}"
.runtime/policy-venv/bin/python adapters/simlingo/run_local.py
