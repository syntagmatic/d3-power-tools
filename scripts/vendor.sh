#!/usr/bin/env bash
# Fetch third-party assets into vendor/ so pages render with no external egress.
#
# vendor/ is gitignored. Run this on the host before working in a sandboxed
# container (which has no CDN access), and in CI before deploying Pages.
#
#   ./scripts/vendor.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."
V=vendor
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

fail=0
get() { # get <url> <dest>
  mkdir -p "$(dirname "$V/$2")"
  curl -sfL --retry 3 --retry-delay 2 "$1" -o "$V/$2" || { echo "FAIL  $1" >&2; fail=1; }
}

# Self-contained ESM bundles from esm.sh. The ?bundle URL returns a stub that
# re-exports the real bundle, so resolve one level and fetch that.
get_esm() { # get_esm <npm-spec> <dest>
  local stub path
  stub=$(curl -sfL --retry 3 "https://esm.sh/$1?bundle&target=es2022") || { echo "FAIL  esm $1" >&2; fail=1; return; }
  path=$(printf '%s' "$stub" | grep -oE '"/[^"]+\.mjs"' | head -1 | tr -d '"')
  mkdir -p "$(dirname "$V/$2")"
  if [ -n "$path" ]; then
    curl -sfL --retry 3 "https://esm.sh$path" -o "$V/$2" || { echo "FAIL  esm $1" >&2; fail=1; return; }
  else
    printf '%s' "$stub" > "$V/$2"
  fi
  if grep -oE '(from|import) *"[^"]*"' "$V/$2" | grep -qE '"(https?:|/)'; then
    echo "WARN  $2 still has external imports" >&2
  fi
}

rm -rf "$V"; mkdir -p "$V"

echo "==> ESM bundles"
get_esm d3@7                 esm/d3.mjs
get_esm topojson-client@3    esm/topojson-client.mjs
get_esm versor@0.2           esm/versor.mjs
get_esm d3-hexbin@0.2        esm/d3-hexbin.mjs
get_esm topojson-simplify@3  esm/topojson-simplify.mjs
get_esm polylabel@2          esm/polylabel.mjs
get_esm pmtiles@3            esm/pmtiles.mjs
get_esm maplibre-gl@4        esm/maplibre-gl.mjs

echo "==> UMD / classic scripts"
get https://d3js.org/d3.v7.min.js         js/d3.v7.min.js
get https://d3js.org/topojson.v3.min.js   js/topojson.v3.min.js
get https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js                           js/d3.min.js
get https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js js/topojson-client.min.js
get https://cdn.jsdelivr.net/npm/d3-sankey@0.12/dist/d3-sankey.min.js          js/d3-sankey.min.js
get https://cdn.jsdelivr.net/npm/d3-hexbin@0.2/build/d3-hexbin.min.js          js/d3-hexbin.min.js
get https://cdnjs.cloudflare.com/ajax/libs/flubber/0.4.2/flubber.min.js        js/flubber.min.js

echo "==> Topology data"
get https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json           data/us-atlas/states-10m.json
get https://cdn.jsdelivr.net/npm/us-atlas@3/states-albers-10m.json    data/us-atlas/states-albers-10m.json
get https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json         data/us-atlas/counties-10m.json
get https://cdn.jsdelivr.net/npm/us-atlas@3/counties-albers-10m.json  data/us-atlas/counties-albers-10m.json
get https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json    data/world-atlas/countries-110m.json
get https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json         data/world-atlas/land-110m.json

echo "==> Fonts"
# Google Fonts CSS is fetched with a browser UA so we get woff2, then rewritten
# to point at the local files it references.
fetch_font_css() { # fetch_font_css <name> <css-url>
  local name="$1" url="$2" css
  mkdir -p "$V/fonts/$name"
  css=$(curl -sfL --retry 3 -A "$UA" "$url") || { echo "FAIL  font $name" >&2; fail=1; return; }
  printf '%s' "$css" | grep -oE 'https://fonts\.gstatic\.com/[^)]*' | sort -u | while read -r f; do
    curl -sfL --retry 3 "$f" -o "$V/fonts/$name/$(basename "$f")"
  done
  printf '%s' "$css" | sed -E 's#https://fonts\.gstatic\.com/[^)]*/([^/)]+)#\1#g' > "$V/fonts/$name/fonts.css"
}
fetch_font_css ui 'https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap'

echo
find "$V" -type f | wc -l | xargs echo "vendored files:"
du -sh "$V" | cut -f1 | xargs echo "total size:"
[ "$fail" = 0 ] || { echo "one or more assets failed to download" >&2; exit 1; }
