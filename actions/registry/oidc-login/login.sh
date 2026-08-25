#!/usr/bin/env bash
set -euo pipefail

if [ -z "${AK_PROVIDER_ID:-}" ] && [ "${GITHUB_SERVER_URL:-}" = "https://github.com" ] && [ "${GITHUB_REPOSITORY:-}" = "whereareiam/toolkit" ]; then
  AK_URL="${AK_URL:-https://maven.whereareiam.me}"
  AK_PROVIDER_ID="bb42817c-b0e2-4bea-ab22-d7b3db257f82"
  AK_AUDIENCE="${AK_AUDIENCE:-artifact-keeper-whereareiam-github}"
fi

: "${AK_URL:?AK_URL is required when no built-in OIDC profile matches}"
: "${AK_PROVIDER_ID:?AK_PROVIDER_ID is required when no built-in OIDC profile matches}"
: "${AK_AUDIENCE:?AK_AUDIENCE is required when no built-in OIDC profile matches}"
: "${ACTIONS_ID_TOKEN_REQUEST_URL:?ACTIONS_ID_TOKEN_REQUEST_URL is required}"
: "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:?ACTIONS_ID_TOKEN_REQUEST_TOKEN is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"

separator='?'
case "$ACTIONS_ID_TOKEN_REQUEST_URL" in
  *\?*) separator='&' ;;
esac

oidc_token="$(curl --fail-with-body --silent --show-error \
  --header "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
  "${ACTIONS_ID_TOKEN_REQUEST_URL}${separator}audience=${AK_AUDIENCE}" | jq -er '.value')"

response="$(curl --fail-with-body --silent --show-error \
  --request POST \
  --header "Authorization: Bearer $oidc_token" \
  --header 'Content-Type: application/json' \
  --data "{\"provider_id\":\"$AK_PROVIDER_ID\"}" \
  "${AK_URL%/}/api/v1/auth/ci/token")"

username="$(printf '%s' "$response" | jq -er '.username')"
token="$(printf '%s' "$response" | jq -er '.access_token')"

printf '::add-mask::%s\n' "$oidc_token"
printf '::add-mask::%s\n' "$token"
export ARTIFACT_KEEPER_USER="$username"
export ARTIFACT_KEEPER_TOKEN="$token"
printf 'ARTIFACT_KEEPER_USER=%s\n' "$username" >> "$GITHUB_ENV"
printf 'ARTIFACT_KEEPER_TOKEN=%s\n' "$token" >> "$GITHUB_ENV"
printf 'username=%s\n' "$username" >> "$GITHUB_OUTPUT"
printf 'token=%s\n' "$token" >> "$GITHUB_OUTPUT"
