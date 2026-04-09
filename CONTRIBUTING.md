# Contributing

## Branch rules

- Never develop directly on `main`.
- Never develop directly on `develop`.
- Always create a feature branch from `develop`.
- Keep branch names readable and subsystem-specific.

Examples:

- `feature/collaborative-response-map-panel`
- `feature/constructive-simulation-scene-fix`
- `feature/realtime-detection-camera-page`
- `feature/sensor-management-device-table`

## Commit scope

Only commit files related to your task.
Do not include generated caches such as `node_modules`, `dist`, or `__pycache__`.

If you changed a subsystem and the main shell depends on its static copy:

1. Rebuild that subsystem if needed.
2. Run `.\scripts\sync-subsystems.ps1`.
3. Include both the subsystem source change and the refreshed public copy in the same branch.

## Pull Request checklist

- The branch was created from `develop`.
- The change stays within the responsible subsystem unless shared files were intentionally changed.
- Local verification was completed in the contributor's own environment.
- If integration assets changed, `.\scripts\sync-subsystems.ps1` was run.
- No unrelated files were added to the commit.

## Shared files that need extra care

- `vue-project_all/src/router/`
- `vue-project_all/src/views/`
- `vue-project_all/src/components/`
- `vue-project_all/public/`
- `.gitignore`
- `README.md`
- `CONTRIBUTING.md`
- `scripts/`

Coordinate before changing those files in parallel.
