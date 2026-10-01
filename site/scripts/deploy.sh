#!/usr/bin/env bash
# Build the static site and publish site/dist to the gh-pages branch (GitHub Pages).
#
#   bash site/scripts/deploy.sh
#
# The branch holds only the built files, as one commit that is replaced on each deploy.
# VITE_API_URL is the hosted live demo API (render.yaml). Override it in the environment, or
# set it to an empty string to publish a site that shows the recorded runs only.
set -euo pipefail

cd "$(dirname "$0")/.."
remote="$(git -C .. remote get-url origin)"
source_commit="$(git -C .. rev-parse --short HEAD)"

export VITE_API_URL="${VITE_API_URL-https://llm-credit-risk-lab-api.onrender.com}"
npm run build
touch dist/.nojekyll   # serve files as they are, without Jekyll processing

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -r dist/. "$tmp"
cd "$tmp"
git init -q -b gh-pages
git add -A
git -c user.name="$(git config --global user.name)" -c user.email="$(git config --global user.email)" \
  commit -q -m "Deploy site from $source_commit"
git push -q --force "$remote" gh-pages
echo "deployed $source_commit to gh-pages"
