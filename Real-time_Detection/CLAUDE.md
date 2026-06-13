# CLAUDE.md — Real-time Detection Module

## Project Context

This is a submodule (交通事故检测 / Traffic Accident Detection) of the larger **lkywSystem** monorepo. The system is collaboratively developed on GitHub.

- **Repo**: https://github.com/luckyLuWen/lkywSystemv0
- **Current branch**: `feature/realtime-detection`
- **Main branch**: `develop`
- **Module directory**: `Real-time_Detection/`

## Environment

- **Virtual environment**: `lkywSystem` (conda, located at `/home/zhangboyu/anaconda3/envs/lkywSystem`)
- Always activate before running: `conda activate lkywSystem`

## Boundaries

1. **Only modify files within `Real-time_Detection/`**. Do not touch other submodules (Collaborative_Response, Constructive simulation, Sensor_Management, Sensor_Management_sim, vue-project_all, etc.).
2. If a global configuration file (outside this module) needs changes, explicitly flag it to the user — do not modify it directly.
3. The `web_app/frontend/old_version/` directory is untracked legacy code — do not modify it.

## Module Structure

```
Real-time_Detection/
├── web_app/                  # Web application (backend + frontend)
│   ├── backend/              # Detection backend server
│   └── frontend/             # Vue-based frontend
├── train_yolov11.py          # YOLOv11 training script
├── augment_train_dataset.py  # Dataset augmentation
├── generate_training_plots.py
├── dataset_split.py
├── start_backend.sh          # Launch backend
├── start_vue.sh              # Launch frontend dev server
├── requirements.txt
└── LKYWDataset_weights/      # Trained model weights
```

## Git Workflow

- Branch: `feature/realtime-detection`
- Target for PRs: `develop`
- GitHub user: `yingrushi0801`
- Do not run `git push --force` or destructive git commands unless explicitly asked.
- Do not commit changes unless explicitly asked.

## Running the Module

```bash
conda activate lkywSystem
cd Real-time_Detection
bash start_backend.sh   # Start detection backend
bash start_vue.sh       # Start Vue dev server
```
