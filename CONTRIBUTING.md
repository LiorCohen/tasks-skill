# Contributing

## Project Structure

```
.claude-plugin/marketplace.json   # Marketplace metadata (version here)
plugin/
  .claude-plugin/plugin.json      # Plugin manifest (version here)
  skills/tasks/
    SKILL.md                      # Skill prompt — command definitions
    workflows.md                  # Workflow details and transition protocol
    schemas.md                    # File templates and field documentation
    scripts/
      tasks_cli.py                # CLI entry point
      tasks_lib/                  # CLI modules (constants, parsing, commands, etc.)
    viewer/
      src/                        # VS Code extension source (TypeScript)
      package.json                # Extension manifest (version here)
      install.sh                  # Build and install script
```

## Release Checklist

When preparing a release:

1. **Bump versions** in all three locations:
   - `.claude-plugin/marketplace.json` — `plugins[0].version`
   - `plugin/.claude-plugin/plugin.json` — `version`
   - `plugin/skills/tasks/viewer/package.json` — `version`
2. **Add a changelog entry** in `CHANGELOG.md` under the new version heading.
3. **Commit** the version bumps and changelog together.

## Testing the CLI

The CLI requires a git repo with a `.tasks/` directory. Quick test:

```bash
dir=$(mktemp -d) && cd "$dir" && git init && mkdir .tasks
python3 /path/to/scripts/tasks_cli.py add "Test task"
python3 /path/to/scripts/tasks_cli.py list
python3 /path/to/scripts/tasks_cli.py audit
```

All output is structured JSON to stdout. Errors are JSON to stderr with exit code 1.

## Testing the Viewer

```bash
python3 /path/to/scripts/tasks_cli.py install-viewer
# Reload VS Code
```

TypeScript diagnostics (pre-existing `@types` warnings are expected — the extension compiles without `@types/vscode` installed globally):

```bash
cd plugin/skills/tasks/viewer && npx tsc --noEmit
```

## Code Style

- Python: no external dependencies (no PyYAML, etc.). The CLI uses a hand-rolled YAML parser.
- TypeScript: the viewer is a standalone VS Code extension with its own `package.json`.
- All markdown task files use YAML frontmatter (`---` delimiters).
- `task.yaml` is pure YAML (no `---` delimiters).
