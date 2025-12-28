# Configuration

This directory contains Barbossa's configuration files.

## Files

### `repositories.json` (Required)
Your main configuration file. Copy from `repositories.json.example` to get started:

```bash
cp config/repositories.json.example config/repositories.json
```

Then edit with your GitHub username and repository details.

**Note:** This file is gitignored for privacy.

### `repositories.json.example` (Template)
Template showing all configuration options with comments. Use this as reference.

### `repositories.schema.json` (Validation)
JSON schema for validating your configuration. Used internally for startup validation.

### `crontab` (Schedule)
Cron schedule for automated agent runs. Generated from configuration by `scripts/generate_crontab.py`.

### `env/` (Optional)
Repository-specific environment files. These are automatically loaded if they exist and are gitignored.

## Configuration Options

See `repositories.json.example` for detailed documentation on:
- Issue tracker setup (GitHub Issues vs Linear)
- Repository settings and `do_not_touch` patterns
- Agent enable/disable toggles
- Auto-merge and PR thresholds
- Backlog limits

## Environment Variables

Configuration supports environment variable interpolation. See `.env.example` in the root directory for required variables.
