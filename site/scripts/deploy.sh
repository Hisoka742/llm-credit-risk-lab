#!/usr/bin/env bash
# Build the static site and publish site/dist to the gh-pages branch (GitHub Pages).
#
#   bash site/scripts/deploy.sh
#
# The branch holds only the built files, as one commit that is replaced on each deploy.
# The live demo section is hidden in this build unless VITE_API_URL is set when building.
set -euo pipefail

cd "$(dirname "$0")/.."
remote="$(git -C .. remote get-url origin)"
source_commit="$(git -C .. rev-parse --short HEAD)"

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
