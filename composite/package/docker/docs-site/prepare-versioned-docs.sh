#!/usr/bin/env bash
set -euo pipefail

repo_dir="${DOCS_REPOSITORY_DIRECTORY:-$PWD}"
site_dir="${DOCS_SITE_DIRECTORY:-docs}"
content_dir="${DOCS_CONTENT_DIRECTORY:-content}"
sidebars_path="${DOCS_SIDEBARS_PATH:-sidebars.js}"
max_releases="${DOCS_MAX_RELEASES:-10}"
current_ref="${DOCS_CURRENT_REF:-origin/dev}"
branch_refs="${DOCS_BRANCH_REFS:-origin/release}"
tag_pattern="${DOCS_TAG_PATTERN:-v*}"

site_path="$repo_dir/$site_dir"
content_path="$site_path/$content_dir"

cd "$repo_dir"

if git remote get-url origin >/dev/null 2>&1; then
  git fetch --force --tags origin "+refs/heads/*:refs/remotes/origin/*"
fi

rm -rf "$site_path/versioned_docs" "$site_path/versioned_sidebars" "$site_path/versions.json"
mkdir -p "$site_path/versioned_docs" "$site_path/versioned_sidebars"

tmp_root="$(mktemp -d)"
restore_content="$tmp_root/original-content"
cp -a "$content_path" "$restore_content"

restore() {
  rm -rf "$content_path"
  cp -a "$restore_content" "$content_path"
  rm -rf "$tmp_root"
}
trap restore EXIT

copy_ref_content() {
  local ref="$1"
  local destination="$2"

  local tmp="$tmp_root/ref"
  rm -rf "$tmp"
  mkdir -p "$tmp"

  if ! git archive "$ref" "$site_dir/$content_dir" | tar -x -C "$tmp" 2>/dev/null; then
    return 1
  fi

  rm -rf "$destination"
  mkdir -p "$destination"
  cp -a "$tmp/$site_dir/$content_dir/." "$destination/"
}

write_sidebar_snapshot() {
  local destination="$1"

  SIDEBAR_PATH="$site_path/$sidebars_path" node <<'EOF' > "$destination"
const sidebars = require(process.env.SIDEBAR_PATH);
process.stdout.write(`${JSON.stringify(sidebars, null, 2)}\n`);
EOF
}

if ! copy_ref_content "$current_ref" "$content_path"; then
  echo "Could not load current docs from $current_ref; using checked-out docs content." >&2
fi

versions=()

for branch_ref in $branch_refs; do
  if git rev-parse --verify --quiet "$branch_ref" >/dev/null; then
    branch_name="${branch_ref##*/}"
    version_name="branch-${branch_name}"
    if copy_ref_content "$branch_ref" "$site_path/versioned_docs/version-$version_name"; then
      write_sidebar_snapshot "$site_path/versioned_sidebars/version-$version_name-sidebars.json"
      versions+=("$version_name")
    fi
  fi
done

mapfile -t release_tags < <(
  git tag --list "$tag_pattern" --sort=-v:refname | head -n "$max_releases"
)

for tag in "${release_tags[@]}"; do
  if copy_ref_content "$tag" "$site_path/versioned_docs/version-$tag"; then
    write_sidebar_snapshot "$site_path/versioned_sidebars/version-$tag-sidebars.json"
    versions+=("$tag")
  fi
done

{
  printf '[\n'
  for index in "${!versions[@]}"; do
    suffix=","
    if [ "$index" -eq "$((${#versions[@]} - 1))" ]; then
      suffix=""
    fi
    printf '  "%s"%s\n' "${versions[$index]}" "$suffix"
  done
  printf ']\n'
} > "$site_path/versions.json"
