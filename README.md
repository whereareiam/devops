# devops

Reusable GitHub Actions and infrastructure tools for builds, tests, pull requests and releases. A `primitive/<domain>/<thing>/<verb>` action does
one thing; a `composite/...` action combines primitives into a flow. Reference an action by its
major tag, for example `whereareiam/devops/primitive/setup/gradle@v3`.

| Task | Start here |
| --- | --- |
| Install JDKs and Gradle in a job | [Setting up Gradle](#setting-up-gradle) |
| Give a job's tests Docker images without pulling them every run | [Setting up Docker images](#setting-up-docker-images) |
| Publish Maven artifacts to the registry | [Publishing Maven artifacts](#publishing-maven-artifacts) |
| Build and push a Docker image | [Publishing images](#publishing-images) |
| Show test results on a run | [Reporting test results](#reporting-test-results) |
| Check a pull request's title and labels | [Validating pull requests](#validating-pull-requests) |
| Let a job's Git read private repositories, such as Swift packages | [Setting up Git access](#setting-up-git-access) |
| Pick the Xcode a macOS job builds with | [Setting up Xcode](#setting-up-xcode) |
| Test Swift packages and report the results | [Testing Swift packages](#testing-swift-packages) |
| Check that Swift sources follow the repository's formatting | [Checking Swift formatting](#checking-swift-formatting) |
| Archive an Apple app and send it to TestFlight | [Uploading to App Store Connect](#uploading-to-app-store-connect) |
| Hand an uploaded build to a TestFlight group | [Distributing to TestFlight](#distributing-to-testflight) |
| Sort a release draft by title prefix and move developer changes apart | [Regrouping a release draft](#regrouping-a-release-draft) |
| Turn release notes into another format, such as a BBCode post | [Formatting release notes](#formatting-release-notes) |
| Move release actions from blockops `v4` | [Moving from blockops](#moving-from-blockops) |
| Move a workflow from `v2` | [Moving from v2](#moving-from-v2) |

## All actions

| Action | Purpose |
| --- | --- |
| `composite/package/docker/publish` | Signs in, builds an image and pushes it with explicit public or private visibility. |
| `composite/package/maven/publish` | Signs in and runs a Gradle or Maven command that publishes to a Maven repository. |
| `primitive/auth/artifact-keeper/request-token` | Exchanges the job's OIDC token for a short-lived Artifact Keeper token. |
| `primitive/metadata/image/resolve-repository` | Resolves the repository an image of the current GitHub repository lives in. |
| `primitive/pull-request/validate-metadata` | Checks that a pull request's title and labels fit a changelog built from pull requests. |
| `primitive/release/app-store/distribute` | Waits until App Store Connect processed an uploaded build and adds it to a TestFlight group, submitting it for beta review when the group is external. |
| `primitive/release/app-store/upload` | Archives an Xcode scheme for one platform and uploads it to App Store Connect, signed through an API key. |
| `primitive/release/draft/regroup` | Regroups a draft release body by pull request title prefix, adds the release notes file, and updates the draft. |
| `primitive/release/notes/format` | Converts release notes into another format, such as BBCode. |
| `primitive/report/junit/publish` | Summarizes the failed tests and uploads JUnit results and reports when a test failed. |
| `primitive/setup/docker-images` | Loads Docker images from the Actions cache, and pulls and caches them only when the cache has none for these references. |
| `primitive/setup/gradle` | Installs the JDK that runs Gradle, further toolchain JDKs, and Gradle with one cache policy. |
| `primitive/setup/git-access` | Lets every later Git call of the job read the listed repositories with a token, without writing it to a Git configuration file. |
| `primitive/setup/xcode` | Selects the newest installed Xcode at or above a minimum version through `DEVELOPER_DIR`. |
| `primitive/test/swift/run` | Runs `swift test` for each Swift package and writes JUnit results. |
| `primitive/lint/swift/run` | Runs `swift format lint` and annotates every finding. |

Registry actions default to private whereareiam destinations; select `visibility: public`
explicitly. Maven uses the `packages` and `packages-private` repositories, images use `images` and
`images-private`. Toolkit GitHub workflows use their repository-bound OIDC profile automatically;
the three OIDC inputs remain for a deliberately configured custom profile. A job that lets an action
sign in through OIDC needs `id-token: write`. Static registry credentials remain supported for local
or legacy runners.

## Setting up Gradle

```yaml
- uses: whereareiam/devops/primitive/setup/gradle@v3
  with:
    java-version: "25"
    toolchain-versions: "21"
```

`java-version` runs Gradle; `toolchain-versions` lists further JDKs, one per line, for Gradle
toolchains. With the default `cache: auto`, pushes to the default branch, releases and manual runs
write the Gradle cache, and every other run, such as a pull request, only reads it. Set
`read-write` or `read-only` to decide yourself.

## Setting up Docker images

```yaml
- uses: whereareiam/devops/primitive/setup/docker-images@v3
  with:
    images: |
      eclipse-temurin:21-jdk
      postgres:17
```

Run it before the tests that need the images. It loads the images into the job's Docker engine from one
Actions cache entry, keyed by the sorted list of references, so a registry is asked only when the list
changes or the entry has expired. The cache policy matches [Setting up Gradle](#setting-up-gradle): with
the default `cache: auto`, pushes to the default branch, releases and manual runs pull a missing entry and
save it, and every other run, such as a pull request, only reads it and pulls without saving on a miss.
The `cache-hit` output tells whether the images came from the cache.

Name an image by a tag that does not move, or by its digest, when a test must not pick up a newer
image: the entry for a reference is kept until it expires, even if the registry's tag moved meanwhile.

## Publishing Maven artifacts

```yaml
permissions:
  contents: read
  id-token: write

steps:
  - uses: whereareiam/devops/composite/package/maven/publish@v3
    with:
      visibility: public
      command: ./gradlew --no-daemon publish
```

The command receives `PUBLISH_MAVEN_BASE_URL`, `PUBLISH_MAVEN_REPOSITORY`, `PUBLISH_VISIBILITY`,
`PUBLISH_USER` and `PUBLISH_TOKEN`.

## Publishing images

```yaml
permissions:
  contents: read
  id-token: write

steps:
  - uses: whereareiam/devops/composite/package/docker/publish@v3
    with:
      visibility: public
      tags: |
        ${{ github.sha }}
        latest
```

`primitive/metadata/image/resolve-repository` returns the same repository path without building,
for jobs that only need the reference.

## Reporting test results

```yaml
- uses: whereareiam/devops/primitive/report/junit/publish@v3
  if: always()
  with:
    name: Unit test results
    artifact-name: test-results
```

The summary on the run lists the failed tests under `name`. The result files and HTML reports are
uploaded as `artifact-name` only when a test failed or errored; `upload: always` uploads them on
every run. The job needs `checks: write` for the summary. On a pull request from a fork the
summary is skipped, because the fork's token cannot write it.

## Validating pull requests

```yaml
on:
  pull_request_target:
    types: [opened, reopened, edited, synchronize, labeled, unlabeled]

permissions:
  pull-requests: read

jobs:
  metadata:
    runs-on: ubuntu-latest
    steps:
      - uses: whereareiam/devops/primitive/pull-request/validate-metadata@v3
```

The title must read `Area: Description`, and the pull request must carry exactly one of
`feature`, `change`, `bug` and `dependencies`, or `skip-changelog`. `title-pattern`,
`category-labels` and `skip-label` change those rules. The action reads the pull request through
the API and never checks out its code, so it is safe under `pull_request_target`.

## Setting up Git access

```yaml
- uses: whereareiam/devops/primitive/setup/git-access@v3
  with:
    token: ${{ secrets.FABRICA_TOKEN }}
    repositories: |
      whereareiam/fabrica
```

Run it before the first step that fetches the repositories, such as `xcodebuild` or `swift test`
resolving a private package. The token goes into `GIT_CONFIG_COUNT` and its key-value pairs as an
authorization header for exactly the listed repositories (with and without `.git`), so every Git
process of the later steps sends it, and nothing outlives the job. A self-hosted runner's
`~/.gitconfig` stays untouched, and the header is masked in logs. A fine-grained token with
read-only contents access to the listed repositories is enough. `server` changes the GitHub address.

## Setting up Xcode

```yaml
- uses: whereareiam/devops/primitive/setup/xcode@v3
  with:
    minimum-version: "27"
```

The action picks the newest Xcode in `/Applications` at or above `minimum-version` and exports
`DEVELOPER_DIR`, so every later step of the job builds with it. It never runs `xcode-select`, which
needs `sudo`, so it works the same on hosted and self-hosted Macs. `search-path` changes where it looks;
the `path` and `version` outputs name the selected Xcode.

## Testing Swift packages

```yaml
- uses: whereareiam/devops/primitive/test/swift/run@v3
  with:
    packages: |
      App
      Modules/*

- uses: whereareiam/devops/primitive/report/junit/publish@v3
  if: always()
  with:
    name: Test results
    artifact-name: test-results
    results: test-results/*.xml
    reports: test-results/**
```

`packages` lists package paths or globs, one per line; every directory with a `Package.swift` is
tested. Each package writes its XCTest and Swift Testing results to `results-directory`, and the
action fails when any package fails, after testing all of them. `arguments` passes further options
to `swift test`.

## Checking Swift formatting

```yaml
- uses: whereareiam/devops/primitive/setup/xcode@v3
  with:
    minimum-version: "16"

- uses: whereareiam/devops/primitive/lint/swift/run@v3
  with:
    paths: |
      App
      Module
```

`paths` lists files, directories or globs, one per line; directories are checked recursively. The
style comes from the `.swift-format` file nearest to each source, so the repository decides it, and
`swift format --in-place --recursive .` applies it locally. The action fails on any finding, after
annotating each one on its line. `swift format` ships with Xcode 16 and later.

## Uploading to App Store Connect

```yaml
- uses: whereareiam/devops/primitive/setup/xcode@v3
  with:
    minimum-version: "27"

- uses: whereareiam/devops/primitive/release/app-store/upload@v3
  with:
    project: App.xcodeproj
    scheme: App
    platform: iOS
    version: 1.2.0
    build-number: ${{ github.run_number }}
    api-key-id: ${{ vars.APP_STORE_CONNECT_KEY_ID }}
    api-issuer-id: ${{ vars.APP_STORE_CONNECT_ISSUER_ID }}
    api-key: ${{ secrets.APP_STORE_CONNECT_KEY }}
```

The action archives `scheme` in Release for `platform` (`iOS`, `macOS`, `tvOS`, `visionOS`, `watchOS`),
with `version` and `build-number` replacing the project's own, and uploads the archive to App Store
Connect, where it appears in TestFlight once processed. Run it once per platform, for example in a
matrix; iPadOS builds come with `iOS`. The build number must grow with every upload of a version,
for each platform on its own.

Signing goes through an App Store Connect API key with the Admin role (Users and Access ›
Integrations): with it, Xcode creates the provisioning profiles and signs with a cloud-managed
distribution certificate, so the runner needs no distribution certificate. Keep the key ID and issuer
ID as variables and the `.p8` contents as a secret; the key file exists only while the step runs.
The archive itself is signed for development first, so a self-hosted runner needs the team's
development certificate in the keychain of the user the runner runs as. `team-id` overrides the
project's team.

## Distributing to TestFlight

```yaml
- uses: whereareiam/devops/primitive/release/app-store/distribute@v3
  with:
    bundle-id: com.example.app
    platform: iOS
    version: 1.2.0
    build-number: ${{ steps.build.outputs.number }}
    group: Friends
    notes: Try the new library.
    api-key-id: ${{ vars.APP_STORE_CONNECT_KEY_ID }}
    api-issuer-id: ${{ vars.APP_STORE_CONNECT_ISSUER_ID }}
    api-key: ${{ secrets.APP_STORE_CONNECT_KEY }}
```

Run it after the upload, with the same platform, version and build number. It waits up to
`timeout-seconds` (45 minutes by default) for App Store Connect to process the build, sets `notes` as
What to Test, and adds the build to the TestFlight group named `group`; a missing group fails with the
names the app has. An internal group's testers can install the build at once. An external group's
build is also submitted for beta review, which Apple must pass before those testers see it; a build
submitted before is left as it is. It uses the same API key as the upload, and needs only Python's
standard library and `openssl`, which every macOS runner has.

## Regrouping a release draft

```yaml
- id: drafter
  uses: release-drafter/release-drafter@v7
- uses: whereareiam/devops/primitive/release/draft/regroup@v3
  with:
    release-id: ${{ steps.drafter.outputs.id }}
    release-body: ${{ steps.drafter.outputs.body }}
```

The job needs `contents: write`. The action uses the job's token unless `token` is set.

The default `title-prefix` grouping sorts the changes of each category by the `Area:` prefix of
their pull request title, so changes of one area stand together and keep their prefix.
`developer-prefixes` names the areas that only concern developers, for example `API`. Their changes
leave the categories and close the changelog in a `## For developers` section; `developer-title`
renames that section.

```yaml
- uses: whereareiam/devops/primitive/release/draft/regroup@v3
  with:
    release-id: ${{ steps.drafter.outputs.id }}
    release-body: ${{ steps.drafter.outputs.body }}
    developer-prefixes: API
```

### Keeping hand-written notes

release-drafter rebuilds the draft body on every run, so text typed into the draft is lost. Keep the
hand-written part of a release, such as its subtitle, summary, and upgrade notes, in a file of the
repository instead, and mark where it goes in the release-drafter `template`:

```yaml
template: |
  <!-- release-notes:start -->
  # Update $RESOLVED_VERSION - [Short subtitle]

  [1-2 sentence summary of the release.]
  <!-- release-notes:end -->

  $CHANGES
```

The file starts with front matter that names the release it belongs to; its content replaces the
text between the markers:

```markdown
---
version: 3.0.0
---

# Update 3.0.0 - Shared Proxies

Proxies now share their sessions.
```

Check out the repository and pass the file and the resolved version:

```yaml
- uses: actions/checkout@v7
- id: drafter
  uses: release-drafter/release-drafter@v7
- uses: whereareiam/devops/primitive/release/draft/regroup@v3
  with:
    release-id: ${{ steps.drafter.outputs.id }}
    release-body: ${{ steps.drafter.outputs.body }}
    notes-file: .github/release-notes.md
    version: ${{ steps.drafter.outputs.resolved_version }}
```

When the file names another version, for example a release that was already published, or does not
exist, the draft keeps the text of the template. Bullets of the notes are never sorted as changes.

## Formatting release notes

```yaml
- uses: whereareiam/devops/primitive/release/notes/format@v3
  with:
    format: bbcode
    release-body: ${{ github.event.release.body }}
    output-file: output/release-notes-bbcode.txt
```

## Moving from blockops

The release actions of `whereareiam/blockops@v4` moved here unchanged; blockops `v5` no longer has them.

| blockops v4 | devops v3 |
| --- | --- |
| `primitive/release/draft/regroup` | `primitive/release/draft/regroup` |
| `primitive/release/notes/format` | `primitive/release/notes/format` |

## Moving from v2

`v3` moves the existing actions; their inputs and outputs are unchanged. The docs site action is removed.

| v2 | v3 |
| --- | --- |
| `actions/registry/oidc-login` | `primitive/auth/artifact-keeper/request-token` |
| `actions/registry/resolve` | `primitive/metadata/image/resolve-repository` |
| `actions/registry/docker-publish` | `composite/package/docker/publish` |
| `actions/registry/maven-publish` | `composite/package/maven/publish` |
| `actions/publish-docs-site` | Removed |

## Development

```shell
uv run --extra test pytest
```

## Tools

`tools/registry/kubelet-credential-provider` holds the kubelet credential provider for Artifact
Keeper; see its own README.
