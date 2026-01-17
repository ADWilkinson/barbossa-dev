# Examples

## Manual review

```json
{
  "settings": {
    "tech_lead": { "auto_merge": false }
  }
}
```

## Work hours only

```json
{
  "settings": {
    "schedule": {
      "engineer": "0 9,12,15,18 * * 1-5",
      "tech_lead": "30 9,12,15,18 * * 1-5"
    }
  }
}
```

## Quality focus

```json
{
  "repositories": [{
    "name": "my-app",
    "url": "https://github.com/you/my-app.git",
    "focus": "Bug fixes only. No new features."
  }]
}
```

## Spec Mode

```json
{
  "products": [{
    "name": "platform",
    "repositories": ["backend", "frontend"],
    "primary_repo": "frontend"
  }],
  "settings": {
    "spec_mode": { "enabled": true }
  }
}
```
