# CLAUDE.md

## Release Process

When making changes that warrant a release, follow the checklist in [CONTRIBUTING.md](CONTRIBUTING.md):

1. Bump plugin version in both `marketplace.json` and `plugin.json` (must stay in sync)
2. Bump viewer `package.json` version only if the viewer itself changed
3. Add a changelog entry in `CHANGELOG.md`
4. Commit version bumps and changelog together
