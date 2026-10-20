#!/usr/bin/env bash
# Finds the JUnit result files and whether one holds a failed test. Runs on bash 3.2, the
# system bash of macOS, so it matches the globs with find instead of globstar.
set -euo pipefail

: "${UPLOAD:?UPLOAD is required}"
: "${RESULTS:?RESULTS is required}"

case "$UPLOAD" in on-failure|always) ;; *) echo "upload must be on-failure or always" >&2; exit 1 ;; esac

# Turns a glob into an extended regex: ** spans directories, * and ? stay within one.
glob_regex() {
	local glob="$1" regex="" char i=0
	while ((i < ${#glob})); do
		char="${glob:i:1}"
		case "$char" in
			'*')
				if [ "${glob:i:3}" = '**/' ]; then
					regex+='(.*/)?'
					i=$((i + 2))
				elif [ "${glob:i:2}" = '**' ]; then
					regex+='.*'
					i=$((i + 1))
				else
					regex+='[^/]*'
				fi
				;;
			'?') regex+='[^/]' ;;
			'[')
				if [ "${glob:i+1:1}" = '!' ]; then
					regex+='[^'
					i=$((i + 1))
				else
					regex+='['
				fi
				;;
			'.' | '+' | '^' | '$' | '(' | ')' | '{' | '}' | '|' | '\') regex+="\\$char" ;;
			*) regex+="$char" ;;
		esac
		i=$((i + 1))
	done
	printf '%s' "$regex"
}

# Prints the files a glob matches, skipping hidden entries below its literal leading directories.
glob_files() {
	local glob="$1" root="" rest="$1" part dir regex path relative
	while [[ "$rest" == */* ]]; do
		part="${rest%%/*}"
		case "$part" in *[*?[]*) break ;; esac
		root+="$part/"
		rest="${rest#*/}"
	done
	case "$rest" in
		*[*?[]*) ;;
		*)
			if [ -f "$glob" ]; then printf '%s\n' "$glob"; fi
			return 0
			;;
	esac
	dir="${root%/}"
	if [ -z "$root" ]; then dir=.; elif [ -z "$dir" ]; then dir=/; fi
	[ -d "$dir" ] || return 0
	regex="^$(glob_regex "$rest")\$"
	while IFS= read -r path; do
		relative="${path#"$dir"}"
		relative="${relative#/}"
		if [[ "$relative" =~ $regex ]]; then printf '%s%s\n' "$root" "$relative"; fi
	done < <(find "$dir" -mindepth 1 \( -name '.*' -prune \) -o -type f -print)
}

files=()
set -f
globs=($RESULTS)
set +f
for glob in ${globs[@]+"${globs[@]}"}; do
	while IFS= read -r file; do files+=("$file"); done < <(glob_files "$glob")
done

failed=false
if ((${#files[@]} > 0)) && grep -qlE '<(failure|error)[ />]' "${files[@]}"; then failed=true; fi
echo "found=$((${#files[@]} > 0))" >> "$GITHUB_OUTPUT"
echo "failed=$failed" >> "$GITHUB_OUTPUT"
