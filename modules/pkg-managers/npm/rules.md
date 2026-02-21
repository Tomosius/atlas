# npm

## Project

- Node version: {{npm.node_version}}
- Lock file: `package-lock.json` (commit this file)

## Core Commands

```bash
npm install              # install all dependencies from package-lock.json
npm install <package>    # add runtime dependency
npm install -D <package> # add development dependency
npm uninstall <package>  # remove dependency
npm run <script>         # run a package.json script
npm update               # update all dependencies within semver range
```

## Running Scripts

```bash
npm run build            # run "build" script from package.json
npm run test             # run "test" script
npm exec <binary>        # run a local binary directly (npm v7+)
npx <package>            # run a package without installing
```

## Lock File

- `package-lock.json` is the source of truth for reproducible installs — always commit it
- Never manually edit `package-lock.json`
- CI should run `npm ci` to do a clean install from the lock file
- Run `npm install` after editing `package.json` to regenerate the lock file

## Workspaces (Monorepo)

```json
// package.json
{
  "workspaces": ["packages/*", "apps/*"]
}
```

```bash
npm run build --workspace=packages/foo   # run in specific workspace
npm run build --workspaces               # run in all workspaces
npm install <dep> --workspace=packages/foo
```

## `.npmrc` Settings

Common settings:

```ini
save-exact=true          # pin exact versions (no ^ or ~)
engine-strict=true       # fail if Node version doesn't match engines field
fund=false               # suppress funding messages
```

## Key Differences from pnpm

| Task | npm | pnpm |
|------|-----|------|
| Install | `npm install` | `pnpm install` |
| Add dep | `npm install <pkg>` | `pnpm add <pkg>` |
| Add dev dep | `npm install -D <pkg>` | `pnpm add -D <pkg>` |
| CI install | `npm ci` | `pnpm install --frozen-lockfile` |
| Disk usage | full copies | symlinked content-addressable store |

## Commands

- Install: `{{commands.install}}`
- Add: `{{commands.add}} <package>`
- Remove: `{{commands.remove}} <package>`
- Run: `{{commands.run}} <script>`
- Update: `{{commands.update}}`
