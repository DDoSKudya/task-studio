# Versioning

Task Studio uses [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) for the **public version string** and a derived **integer build** for installers, menus, and manifests.

## Public version (SemVer)

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD_META]
```

| Piece | Meaning |
| --- | --- |
| `MAJOR` | Breaking product/API surface |
| `MINOR` | Backward-compatible features |
| `PATCH` | Backward-compatible fixes |
| `PRERELEASE` | Stability channel (see below) |
| `BUILD_META` | Optional SemVer build metadata (ignored for precedence) |

### Channels (`PRERELEASE`)

| Label | SemVer examples | When |
| --- | --- | --- |
| `alpha` | `1.0.0-alpha.1` | First public cut; expected rough edges |
| `beta` | `1.1.0-beta.1` | Feature-complete for the minor; polish / bugfix |
| `rc` | `1.1.0-rc.1` | Release candidate; ship blockers only |
| _(none)_ | `1.1.0` | General availability (GA) |

The trailing `.n` is the **iteration** within that channel for the same `MAJOR.MINOR.PATCH` (starts at `1`).

Develop / nightlies stay on the consumer manifest as `0.0.0-develop` (see `studio-version.json`) and are not changelog releases.

## Integer build number

Installers and update checks need a single monotonically useful integer. Compute it as:

```
build = MAJOR * 100_000_000
      + MINOR *   1_000_000
      + PATCH *      10_000
      + C     *       1_000
      + n
```

| Symbol | Source |
| --- | --- |
| `MAJOR`, `MINOR`, `PATCH` | SemVer core |
| `C` | Channel code: `alpha=1`, `beta=2`, `rc=3`, `ga=9` |
| `n` | Iteration `1…999` for that `X.Y.Z` + channel |

### Examples

| Version | C | n | Build |
| --- | --- | --- | --- |
| `1.0.0-alpha.1` | 1 | 1 | `100001001` |
| `1.0.0-alpha.2` | 1 | 2 | `100001002` |
| `1.1.0-beta.1` | 2 | 1 | `101002001` |
| `1.1.1-beta.1` | 2 | 1 | `101012001` |
| `1.1.0-rc.1` | 3 | 1 | `101003001` |
| `1.1.0` (GA) | 9 | 1 | `101009001` |
| `1.1.1` (GA) | 9 | 1 | `101019001` |

Within one product line this ordering grows with major → minor → patch → channel → iteration, so `1.0.0-alpha.2` < `1.1.0-beta.1` < `1.1.0` as integers as well as SemVer.

### Web UI source

The sidebar reads [`apps/web/app-version.json`](../apps/web/app-version.json) (overridable with `NUXT_PUBLIC_APP_VERSION` / `NUXT_PUBLIC_APP_BUILD` / `NUXT_PUBLIC_APP_CHANNEL`). Keep that file in sync when cutting a changelog release.

### Launcher source

The terminal launcher (bash / PowerShell) reads [`scripts/launcher-version.json`](../scripts/launcher-version.json). Chrome title shows SemVer (`Task Studio Launcher · 1.0.0-beta.1`); the footer appends `build …`. Launcher versioning is independent of the web app and of the consumer tip in `studio-version.json`.

| Artifact | Role | Example |
| --- | --- | --- |
| `apps/web/app-version.json` | Web UI sidebar | `1.1.1-beta.1` / `101012001` |
| `scripts/launcher-version.json` | Installer / TUI chrome | `1.0.0-beta.1` / `100002001` |
| `studio-version.json` | Consumer update channel | `0.0.0-develop` on develop tip |

### Compute helper

```bash
python3 scripts/maintenance/compute-build-number.py 1.1.0-beta.1
# → version=1.1.0-beta.1 build=101002001 channel=beta n=1
```

## Release checklist

1. Bump SemVer + iteration in `CHANGELOG.md` (Keep a Changelog section).
2. Run `scripts/maintenance/compute-build-number.py` and paste **Build** into the changelog entry.
3. Sync `apps/web/app-version.json` (and, when releasing the launcher chrome, `scripts/launcher-version.json`) with the same SemVer / build / channel.
4. For a consumer release channel, update `studio-version.json` `version` / `channel` / `ref` / archive URLs (leave `0.0.0-develop` on the develop tip).
5. Tag git as `v{version}` (example: `v1.1.0-beta.1`).
6. Optionally set SemVer build metadata to the same integer: `1.1.0-beta.1+101002001`.
