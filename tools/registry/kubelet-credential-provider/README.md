# Artifact Keeper kubelet credential provider

This helper exchanges the pod-bound Kubernetes ServiceAccount token supplied by
the kubelet for a short-lived Artifact Keeper CI-OIDC token. It does not store
registry credentials on nodes or in Kubernetes `imagePullSecrets`.

The kubelet must be configured with `tokenAttributes` and the
`KubeletServiceAccountTokenForCredentialProviders` feature gate. The helper
expects a root-owned JSON file at:

```text
/etc/kubernetes/artifact-keeper-credential-provider.json
```

Example:

```json
{
  "registries": {
    "registry.arcadeya.com": {
      "url": "https://registry.arcadeya.com",
      "provider_id": "<Arcadeya Kubernetes CI-OIDC provider UUID>"
    },
    "registry.whereareiam.me": {
      "url": "https://registry.whereareiam.me",
      "provider_id": "<whereareiam Kubernetes CI-OIDC provider UUID>"
    }
  }
}
```

The Artifact Keeper mappings must restrict the Kubernetes ServiceAccount claim
to the intended namespace, for example:

```text
system:serviceaccount:arcadeya:artifact-puller
system:serviceaccount:whereareiam:artifact-puller
```
