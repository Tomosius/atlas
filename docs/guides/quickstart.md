# Quick Start

## 1. Initialise your project

Navigate to your project root and run:

```bash
atlas init
```

Atlas will detect your stack (languages, tools, frameworks) and suggest modules to install.

## 2. Ask the agent for context

In your editor, the agent can now call:

```
atlas retrieve python
atlas retrieve ruff
atlas retrieve pytest
```

Each call returns a Markdown document with your actual config values injected.

## 3. Run tasks with error augmentation

```
atlas just test
atlas just lint
```

Atlas runs the command and appends relevant rule hints next to any errors.

## 4. Add more modules

```
atlas add django
atlas add postgresql
```

## 5. Keep in sync

When you change config files, run:

```bash
atlas sync
```

Atlas re-scans your config files and updates stored values.
