# 客运车仿真多视角演示数据

- 来源模型：`汽车_13.FBX`（FBX）。
- 仿真 UAV 视角：24 张；仿真 UGV 视角：8 张。
- 图像由 Blender 相机渲染生成，用于模拟视角，不是真实 UAV/UGV 采集影像。
- `models/vehicle-surface.ply` 是源网格转为 PLY 并由材质漫反射色生成顶点颜色，不是 Poisson 重建结果。
- 源 FBX 未提供可用外部纹理图，因此没有生成 `texture.jpg`；场景尺度未标定，单位保持为模型单位。
