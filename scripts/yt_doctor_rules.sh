#!/usr/bin/env bash
set -euo pipefail

_yt_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

_yt_decode_accents() {
  local s="$1"
  if command -v iconv >/dev/null 2>&1; then
    s="$(printf '%s' "$s" | iconv -f utf-8 -t ascii//TRANSLIT 2>/dev/null || printf '%s' "$s")"
  fi
  printf '%s' "$s" \
    | sed -E 's/%c3%a1|%c3%a0|%c3%a2|%c3%a4/a/g; s/%c3%a9|%c3%a8|%c3%aa/e/g; s/%c3%ad|%c3%ac|%c3%af/i/g; s/%c3%b3|%c3%b2|%c3%b4/o/g; s/%c3%ba|%c3%b9|%c3%bc/u/g'
}

_yt_norm() {
  local s
  s="$(_yt_lower "$1")"
  _yt_decode_accents "$s"
}

_yt_has_placeholder_pattern() {
  local s="$(_yt_norm "$1")"
  printf '%s' "$s" | grep -q 'peg' || return 1
  printf '%s' "$s" | grep -q 'aca' || return 1
  printf '%s' "$s" | grep -q 'url' || return 1
  return 0
}

_yt_bad_url_reason() {
  local url_raw="$1"
  local title_raw="$2"
  local url_lc title_lc
  url_lc="$(_yt_norm "$url_raw")"
  title_lc="$(_yt_norm "$title_raw")"

  if [ -z "$url_lc" ]; then
    echo ""
    return 0
  fi

  if [[ "$url_lc" == chrome-error://* ]] || [[ "$url_lc" == *chromewebdata* ]]; then
    echo "chrome_error"
    return 0
  fi

  if _yt_has_placeholder_pattern "$url_lc"; then
    echo "placeholder_pattern"
    return 0
  fi

  if printf '%s' "$url_lc" | grep -qiE 'err_name_not_resolved|dns_probe_finished_nxdomain|nxdomain'; then
    echo "dns_error"
    return 0
  fi

  if printf '%s' "$title_lc" | grep -qiE 'err_name_not_resolved|dns_probe_finished_nxdomain|nxdomain'; then
    echo "dns_error_title"
    return 0
  fi

  echo ""
}
