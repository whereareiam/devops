#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${PULL_REQUEST:?PULL_REQUEST is required}"
: "${TITLE_PATTERN:?TITLE_PATTERN is required}"
: "${CATEGORY_LABELS:?CATEGORY_LABELS is required}"

if [[ ! "$PULL_REQUEST" =~ ^[1-9][0-9]*$ ]]; then
	echo "pull-request must be a positive integer" >&2
	exit 1
fi

pull_request="$(gh api --header 'Accept: application/vnd.github+json' \
	"repos/${GITHUB_REPOSITORY}/pulls/${PULL_REQUEST}")"
title="$(jq -r '.title // empty' <<<"$pull_request")"
labels="$(jq -r '[.labels[]?.name] | join(", ")' <<<"$pull_request")"
category_count="$(jq --arg categories "$CATEGORY_LABELS" \
	'($categories | split(",") | map(gsub("^\\s+|\\s+$"; ""))) as $allowed
	| [.labels[]?.name | select(. as $label | $allowed | index($label))] | length' <<<"$pull_request")"
skipped="$(jq -r --arg skip "${SKIP_LABEL:-}" '[.labels[]?.name] | index($skip) != null' <<<"$pull_request")"
categories="${CATEGORY_LABELS//,/, }"
failures=()

if [[ ! "$title" =~ $TITLE_PATTERN ]]; then
	failures+=("Title must use the '${TITLE_FORMAT:-$TITLE_PATTERN}' format")
fi
if [[ "$category_count" -gt 1 ]]; then
	failures+=("Use only one category label: ${categories}")
elif [[ "$category_count" -eq 0 && "$skipped" != "true" ]]; then
	failures+=("Add one category label (${categories})${SKIP_LABEL:+ or ${SKIP_LABEL}}")
fi

{
	echo "### Pull request metadata"
	echo
	echo "- Title: ${title}"
	echo "- Labels: ${labels:-none}"
	if ((${#failures[@]} == 0)); then
		echo "- Result: valid"
	else
		echo "- Result: invalid"
		echo
		for failure in "${failures[@]}"; do
			echo "- ${failure}"
		done
	fi
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"

if ((${#failures[@]} > 0)); then
	printf 'Pull request metadata validation failed:\n' >&2
	printf -- '- %s\n' "${failures[@]}" >&2
	exit 1
fi
