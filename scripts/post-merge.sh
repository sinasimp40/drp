#!/bin/bash
set -e

# Install Python dependencies if requirements.txt exists
if [ -f license_server/requirements.txt ]; then
  pip install -q -r license_server/requirements.txt
fi

# Install mockup sandbox dependencies
if [ -f artifacts/mockup-sandbox/package.json ]; then
  (cd artifacts/mockup-sandbox && npm install --silent --no-audit --no-fund)
fi
