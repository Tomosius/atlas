# Verbs & API

Atlas exposes one MCP tool — `atlas` — with a single string input. The input is parsed into a verb + query.

## Syntax

```
<verb> <query>
<verb> <filter1> <filter2>     # spaces = AND filter
<verb> <moduleA>,<moduleB>     # commas = combine multiple modules
<verb> <query> -- <passthrough> # -- separates atlas args from tool args
```

## The 10 verbs

### `init`

Detect the project stack and install suggested modules.

```
init
init --yes        # accept all suggestions without prompting
```

### `retrieve`

Return pre-built context for one or more modules.

```
retrieve python
retrieve ruff
retrieve python ruff pytest     # multiple filters (AND)
retrieve python,ruff,pytest     # combine into one response
retrieve ruff select            # filter to sections matching "select"
```

### `add`

Install a module from the warehouse.

```
add ruff
add django postgresql
```

### `remove`

Uninstall a module.

```
remove flake8
```

### `sync`

Re-scan config files and update stored values.

```
sync
```

### `update`

Pull latest module bundles from the warehouse.

```
update
update ruff        # update a specific module only
```

### `status`

Show project state: installed modules, active task, recent history, git status.

```
status
```

### `just`

Run a project task with error augmentation.

```
just test
just lint
just test -- -k scanner     # passthrough args to the tool
```

### `note`

Add or remove a tribal knowledge note on a module.

```
note ruff "always run ruff before committing"
note remove ruff 1
```

### `notes`

List all notes for a module.

```
notes ruff
notes pytest
```

## Special: prompt retrieval

If the verb is not one of the 10 above, Atlas treats the whole input as a prompt name:

```
design
review
debug
king-mode
design -- src/auth/login.py     # with file context
```
