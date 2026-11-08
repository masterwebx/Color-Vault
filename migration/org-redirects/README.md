# Org repo redirect stubs

These HTML stubs are meant to be copied into the **Color-Vault/Color-Vault** org repository later so old `color-vault.github.io/Color-Vault/...` URLs keep working after the live site moves to **masterwebx/Color-Vault**.

**Do not deploy them from this repo.** They are prepared here only for a future org-repo update.

Each stub uses:

- `<link rel="canonical">` to the new masterwebx Pages URL
- `<meta http-equiv="refresh">`
- A visible link
- `location.replace(...)` that preserves `location.search` and `location.hash`

| Stub path | Redirects to |
| --- | --- |
| `index.html` | `https://masterwebx.github.io/Color-Vault/` |
| `dist/index.html` | `https://masterwebx.github.io/Color-Vault/dist/index.html` |
| `colorcreator2.html` | `https://masterwebx.github.io/Color-Vault/legacy/site/colorcreator2.html` |
| `colorcreator.html` | `https://masterwebx.github.io/Color-Vault/legacy/site/colorcreator.html` |
| `coloranalyzer.html` | `https://masterwebx.github.io/Color-Vault/legacy/site/coloranalyzer.html` |
| `downloads.html` | `https://masterwebx.github.io/Color-Vault/legacy/site/downloads.html` |
| `image analyzer 1.4/index.html` | `https://masterwebx.github.io/Color-Vault/legacy/site/image%20analyzer%201.4/index.html` |
