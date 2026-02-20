# pnpm

## Project

- pnpm version: {{pnpm.version}}
- Node version: {{pnpm.node_version}}
- Lock file: `pnpm-lock.yaml` (commit this file)

## Core Commands

```bash
pnpm install             # install all dependencies from pnpm-lock.yaml
pnpm add <package>       # add runtime dependency
pnpm add -D <package>    # add development dependency
pnpm remove <package>    # remove dependency
pnpm run <script>        # run a package.json script
pnpm update              # update all dependencies within semver range
pnpm update --latest     # upgrade all to latest versions
```

## Running Scripts

```bash
pnpm run build           # explicit: run "build" script
pnpm build               # shorthand for built-in scripts
pnpm exec tsc            # run a local binary directly
pnpm dlx <package>       # run a package without installing (like npx)
```

## Lock File

- `pnpm-lock.yaml` is the source of truth for reproducible installs — always commit it
- Never manually edit `pnpm-lock.yaml`
- CI should run `pnpm install --frozen-lockfile` to verify lock file is up to date
- Run `pnpm install` after editing `package.json` to regenerate the lock file

## Workspaces (Monorepo)

```yaml
# pnpm-workspace.yaml
packages:
  - "packages/*"
  - "apps/*"
```

```bash
pnpm --filter <package> run build    # run in specific package
pnpm -r run build                    # run in all packages
pnpm --filter "./packages/**" add <dep>
```

## `.npmrc` Settings

Common pnpm-specific settings:

```ini
shamefully-hoist=false    # keep strict node_modules (pnpm default)
strict-peer-dependencies=true
auto-install-peers=true
```

## Key Differences from npm

| Task | npm | pnpm |
|------|-----|------|
| Install | `npm install` | `pnpm install` |
| Add dep | `npm install <pkg>` | `pnpm add <pkg>` |
| Add dev dep | `npm install -D <pkg>` | `pnpm add -D <pkg>` |
| Run script | `npm run <script>` | `pnpm run <script>` |
| Disk usage | full copies | symlinked content-addressable store |

## Commands

- Install: `{{commands.install}}`
- Add: `{{commands.add}} <package>`
- Remove: `{{commands.remove}} <package>`
- Run: `{{commands.run}} <script>`
- Update: `{{commands.update}}`
