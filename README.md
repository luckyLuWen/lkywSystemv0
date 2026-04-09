# lkywSystem

## Project layout

- `vue-project_all`: main shell application and unified entry.
- `Collaborative_Response`: subsystem owned by colleague A.
- `Constructive simulation`: subsystem owned by colleague B.
- `Real-time_Detection`: subsystem owned by colleague C.
- `Sensor_Management`: subsystem owned by colleague D.
- `scripts/sync-subsystems.ps1`: sync built subsystem assets into `vue-project_all/public`.

## Source of truth

The four subsystem folders are the source of truth.
`vue-project_all/public` only stores the static copies used by the main shell.
Do not edit those copied public assets by hand.

## Branch model

- `main`: stable release branch.
- `develop`: daily integration branch.
- `feature/<subsystem>-<topic>`: personal development branches created from `develop`.
- `hotfix/<topic>`: urgent fixes created from `main`.

Recommended subsystem branch prefixes:

- A: `feature/collaborative-response-...`
- B: `feature/constructive-simulation-...`
- C: `feature/realtime-detection-...`
- D: `feature/sensor-management-...`

## Team workflow

1. Clone the repository.
2. Switch to `develop`.
3. Pull the latest `develop`.
4. Create a personal feature branch from `develop`.
5. Only modify files related to your subsystem or approved shared integration files.
6. Test in your own local operating system environment.
7. If your subsystem change affects the main shell integration, rebuild your subsystem and run `.\scripts\sync-subsystems.ps1`.
8. Commit and push your branch.
9. Open a Pull Request targeting `develop`.
10. After integration testing passes, merge `develop` into `main` when releasing.

## Ownership boundaries

- Colleague A mainly edits `Collaborative_Response/`.
- Colleague B mainly edits `Constructive simulation/`.
- Colleague C mainly edits `Real-time_Detection/`.
- Colleague D mainly edits `Sensor_Management/`.
- The lead mainly edits `vue-project_all/` and cross-subsystem integration files.

Any change to shared routes, iframe paths, public integration folders, or common release rules should be coordinated before merge.

## Sync command

After a subsystem changes, rebuild that subsystem if needed, then run:

```powershell
.\scripts\sync-subsystems.ps1
```

This refreshes the public folders used by `vue-project_all`:

- `collaborative-response`
- `constructive-simulation`
- `realtime-detection`
- `sensor-management`

## Initial repository setup

After cloning on a new machine, install dependencies only in the subsystem you need to work on and in `vue-project_all` if you need the integrated shell.

Typical example:

```powershell
cd vue-project_all
npm install
```

Repeat the same idea inside the subsystem you are responsible for.
