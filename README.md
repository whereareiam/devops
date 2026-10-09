# devops

Reusable GitHub Actions and infrastructure tools. A `primitive/<domain>/<thing>/<verb>` action does
one thing; a `composite/...` action combines primitives into a flow. Reference an action by its
major tag, for example `whereareiam/devops/primitive/setup/gradle@v3`.

| Task | Start here |
| --- | --- |
| Install JDKs and Gradle in a job | [Setting up Gradle](#setting-up-gradle) |
| Publish Maven artifacts to the registry | [Publishing Maven artifacts](#publishing-maven-artifacts) |
| Build and push a Docker image | [Publishing images](#publishing-images) |
| Show test results on a run | [Reporting test results](#reporting-test-results) |
| Check a pull request's title and labels | [Validating pull requests](#validating-pull-requests) |
| Move a workflow from `v2` | [Moving from v2](#moving-from-v2) |

## All actions

| Action | Purpose |
| --- | --- |
| `composite/package/docker/docs-site` | Builds a Docusaurus site, packages it as an image and pushes it. |
| `composite/package/docker/publish` | Signs in, builds an image and pushes it with explicit public or private visibility. |
| `composite/package/maven/publish` | Signs in and runs a Gradle or Maven command that publishes to a Maven repository. |
| `primitive/auth/artifact-keeper/request-token` | Exchanges the job's OIDC token for a short-lived Artifact Keeper token. |
| `primitive/metadata/image/resolve-repository` | Resolves the repository an image of the current GitHub repository lives in. |
| `primitive/pull-request/validate-metadata` | Checks that a pull request's title and labels fit a changelog built from pull requests. |
| `primitive/report/junit/publish` | Uploads JUnit results and reports as an artifact and summarizes the failed tests. |
| `primitive/setup/gradle` | Installs the JDK that runs Gradle, further toolchain JDKs, and Gradle with one cache policy. |

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
```

The job needs `checks: write` for the summary. On a pull request from a fork the results are still
uploaded, but the summary is skipped because the fork's token cannot write it.

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

## Moving from v2

`v3` only moves the existing actions; their inputs and outputs are unchanged.

| v2 | v3 |
| --- | --- |
| `actions/registry/oidc-login` | `primitive/auth/artifact-keeper/request-token` |
| `actions/registry/resolve` | `primitive/metadata/image/resolve-repository` |
| `actions/registry/docker-publish` | `composite/package/docker/publish` |
| `actions/registry/maven-publish` | `composite/package/maven/publish` |
| `actions/publish-docs-site` | `composite/package/docker/docs-site` |

## Tools

`tools/registry/kubelet-credential-provider` holds the kubelet credential provider for Artifact
Keeper; see its own README.
