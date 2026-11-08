# Color Vault website migration

## Source

- Separate local clone: `C:\Users\glwex\Documents\GitHub\Color-Vault-org`
- Remote: `Color-Vault/Color-Vault`
- Pinned commit: `01ce4130c20cd1a3c78f0ca75ac47ed329d13084` (“Updated Pixel Art Recolor tool”)
- Destination: `masterwebx/Color-Vault` branch `master`

## Mapping

| Former org-site path | New path in this repo |
| --- | --- |
| `index.html` (old home) | `legacy/site/index.html` |
| `downloads.html`, `coloranalyzer.html`, `colorcreator.html`, `colorcreator2.html` | `legacy/site/<same>` |
| `app.js`, `app2.js`, `defaultColors.js`, `data.json` | `legacy/site/<same>` |
| `style/`, `images/`, `sounds/`, `Programs/`, `costumes/` | `legacy/site/<same>/` |
| `image analyzer 1.4/` | `legacy/site/image analyzer 1.4/` |
| `dist/index.html` | `dist/index.html` (kept at root; main tool) |
| `assets/index-DUonJy8q.js`, `assets/index-ItG1fmLn.css` | kept at root |
| `assets/pixel-art-recolor-tool/` | kept at root (tool source) |
| New landing | `index.html` (root) |
| Org redirect stubs (not deployed from here) | `migration/org-redirects/` |

GitHub Pages workflow: `.github/workflows/static.yml` uploads `path: '.'`, triggers on `master` push and `workflow_dispatch`. `.nojekyll` is present. Former Jekyll workflow removed.

## Archive inventory (`legacy/site/`)

- HTML: `index.html`, `downloads.html`, `coloranalyzer.html`, `colorcreator.html`, `colorcreator2.html`
- Scripts/data: `app.js`, `app2.js`, `defaultColors.js`, `data.json`
- Assets: `style/`, `images/` (incl. `color sheets/`), `sounds/`
- Tools: `Programs/Image_2_RGB.exe`, `costumes/costumes.rar`
- Nested: `image analyzer 1.4/` (analyzer UI, sheets, embedded color creator)

## Legacy sheets vs `other/color sheets`

Compared top-level files in `legacy/site/images/color sheets/` (46) with `other/color sheets/` (50).

- Same name + same SHA-256: **5** — `Dio (Sandbox) Recolor Sheet .png`, `Jotaro (Sandbox) Recolor Sheet .png`, `Pac Man Recolor Sheet.png`, `X (Sandbox) Recolor Sheet .png`, `Zero (Sandbox) Recolor Sheet .png`
- Same name, **different hash**: **38** — `Bandana Dee Recolor Sheet.png`, `Black Mage Recolor Sheet.png`, `Bomberman Recolor Sheet.png`, `Bowser Recolor Sheet.png`, `Captain Falcon Recolor Sheet.png`, `Chibi Robo Recolor Sheet.png`, `Ganondorf Recolor Sheet.png`, `Ichigo Recolor Sheet.png`, `Isaac Recolor Sheet.png`, `Jigglypuff Recolor Sheet.png`, `Kirby Recolor Sheet.png`, `Krystal Recolor Sheet.png`, `Link Recolor Sheet.png`, `Lloyd Recolor Sheet.png`, `Lucario Recolor Sheet.png`, `Luffy Recolor Sheet.png`, `Luigi Recolor Sheet.png`, `Mario Recolor Sheet.png`, `Mega Man Recolor Sheet.png`, `Naruto Recolor Sheet.png`, `Ness Recolor Sheet.png`, `Peach Recolor Sheet.png`, `Pichu Recolor Sheet.png`, `Pikachu Recolor Sheet.png`, `Pit Recolor Sheet.png`, `Rayman Recolor Sheet.png`, `readme.txt`, `Ryu Recolor Sheet.png`, `Samus Recolor Sheet.png`, `Sandbag Recolor Sheet.png`, `Simon Recolor Sheet.png`, `Sonic Recolor Sheet.png`, `Sora Recolor Sheet.png`, `Tails Recolor Sheet.png`, `Waluigi Recolor Sheet.png`, `Wario Recolor Sheet.png`, `Yoshi Recolor Sheet.png`, `Zamus Recolor Sheet.png`
- Only in legacy: **3** — `BowserA Recolor Sheet.png`, `BowserB Recolor Sheet.png`, `Game n_ Watch Recolor Sheet.png`
- Only in `other/color sheets`: **7** — `Dedede Recolor Sheet.png`, `Falco Recolor Sheet.png`, `gameandwatch Recolor Sheet.png`, `goku recolor sheet.png`, `MetaKnight_Recolor_Sheet.png`, `Sheik_Recolor_Sheet.png`, `Zelda_Recolor_Sheet.png`

## Absolute `Color-Vault/Color-Vault` raw links (left unchanged)

Listed for follow-up; still point at the org repo:

- `https://github.com/Color-Vault/Color-Vault/raw/main/costumes/costumes.rar` — in `legacy/site/index.html`
- `https://github.com/Color-Vault/Color-Vault/raw/main/Programs/Image_2_RGB.exe` — in `legacy/site/index.html` (note: original markup also has a missing opening quote on this `href`)

After move, local copies live at `legacy/site/costumes/costumes.rar` and `legacy/site/Programs/Image_2_RGB.exe`.

## External consumers

- **Costume injector** (`other/source/gui.py`): “Create Recolor” opens `https://color-vault.github.io/Color-Vault/colorcreator2.html` (should later become `/legacy/site/colorcreator2.html` on masterwebx Pages, or use org redirects). Also loads `other/urls.json` and raw `*.as` from `masterwebx/Color-Vault`.
- **Wex-Projects**: historically links to the Pixel Art Recolor Tool `dist` URL on the Color Vault Pages host; update to `https://masterwebx.github.io/Color-Vault/dist/index.html` when cut over.
- **Old-home raw downloads**: org `raw/main` `.exe` / `.rar` links above (costumes pack + Image2RGB).

## Relative link fix applied

- `legacy/site/index.html`: `dist/index.html` → `../../dist/index.html` (tool stayed at repo root).

Other legacy relative assets (`style/`, `images/`, `app*.js`, etc.) remain valid under the preserved `legacy/site/` tree.

## Follow-ups

1. Point Pages (when ready) at this repo; do not deploy org redirects from here.
2. Copy `migration/org-redirects/` into the org repo so `color-vault.github.io` URLs forward.
3. Update injector `gui.py` Create Recolor URL.
4. Update Wex-Projects dist link.
5. Optionally retarget or replace the two org `raw/main` download links.
6. Rebuild/publish `dist/` from `assets/pixel-art-recolor-tool` when the tool changes (`base: /Color-Vault/`).

## Rollback

Working-tree only until a commit exists. To undo uncommitted migration work:

```text
git status
git restore --worktree --staged .
git clean -fd
```

After a future commit, use `git revert` / reset to that pre-migration commit on `master` (do not rewrite published history unless intentional).
