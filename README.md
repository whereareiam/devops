# devops

Reusable CI/CD actions and infrastructure automation.

## Actions

- `actions/publish-docs-site` builds a Docusaurus site, packages it as a Docker image, and pushes it to a container registry.
- `actions/registry/resolve` constructs private-by-default Artifact Keeper image repositories.
- `actions/registry/docker-publish` builds and publishes Docker/OCI images with explicit public/private visibility.
- `actions/registry/maven-publish` standardizes Maven publishing for Toolkit, Gradle, and Maven projects.
- `actions/registry/oidc-login` exchanges a Forgejo/GitHub Actions OIDC token for a short-lived Artifact Keeper token.

Registry actions default to private whereareiam destinations. Public publishing
must be selected explicitly with `visibility: public`. Toolkit GitHub workflows
use their repository-bound OIDC profile automatically; the Artifact Keeper
provider ID is internal action configuration, not a workflow setting. The
three OIDC inputs remain available only for a deliberately configured custom
profile. Static registry credentials remain supported for local or legacy
runners. Maven uses `packages` and `packages-private`; Docker/OCI uses `images`
and `images-private`.
