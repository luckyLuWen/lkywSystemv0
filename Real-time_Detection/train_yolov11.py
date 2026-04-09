#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv11 训练脚本 - 两客一危火灾检测
重点优化mAP指标
"""

import os
import gc

# 设置环境变量以减少内存使用和避免碎片化
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128,expandable_segments:True'
# 限制OpenMP线程数，防止CPU过载导致死机
os.environ['OMP_NUM_THREADS'] = '4'
os.environ['MKL_NUM_THREADS'] = '4'

from ultralytics import YOLO
import torch
import yaml
from pathlib import Path

# 清理内存
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()


class YOLOv11Trainer:
    def __init__(self, data_yaml, model_name='yolo11n.pt'):
        """
        初始化训练器
        
        Args:
            data_yaml: 数据集配置文件路径
            model_name: 预训练模型名称 (yolo11n/s/m/l/x.pt)
        """
        self.data_yaml = data_yaml
        self.model_name = model_name
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print("="*60)
        print("🚀 YOLOv11 训练器初始化")
        print("="*60)
        print(f"📊 数据集配置: {data_yaml}")
        print(f"🤖 预训练模型: {model_name}")
        print(f"💻 训练设备: {self.device}")
        
        # 检查数据集配置
        self._check_dataset()
        
    def _check_dataset(self):
        """检查数据集配置"""
        if not Path(self.data_yaml).exists():
            raise FileNotFoundError(f"数据集配置文件不存在: {self.data_yaml}")
        
        with open(self.data_yaml, 'r', encoding='utf-8') as f:
            data_config = yaml.safe_load(f)
        
        print(f"✅ 数据集类别数: {data_config['nc']}")
        print(f"✅ 类别名称: {data_config['names']}")
        
    def train(self, 
              epochs=300,
              imgsz=640,
              batch=16,
              patience=50,
              save_period=10,
              project='runs/detect',
              name='lkyw_fire_detection'):
        """
        开始训练
        
        Args:
            epochs: 训练轮数
            imgsz: 图片尺寸
            batch: 批次大小
            patience: 早停耐心值
            save_period: 保存周期
            project: 项目保存路径
            name: 实验名称
        """
        print("\n" + "="*60)
        print("🎯 开始训练 - 重点优化mAP")
        print("="*60)
        
        # 加载模型
        model = YOLO(self.model_name)
        
        # 训练参数配置（针对mAP优化，防止系统死机）
        results = model.train(
            # 数据配置
            data=self.data_yaml,
            
            # 训练基础参数
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=self.device,
            workers=4,          # 限制数据加载线程数，防止CPU过载
            cache=False,        # 关闭缓存，减少内存占用
            
            # 优化器配置（提升mAP）
            optimizer='AdamW',  # AdamW通常比SGD收敛更快，且内存效率更高
            lr0=0.0008,         # 初始学习率（略微降低以获得更稳定的训练）
            lrf=0.01,           # 最终学习率（epoch结束时）
            momentum=0.937,     # SGD momentum/Adam beta1
            weight_decay=0.0005,  # 权重衰减（防止过拟合）
            warmup_epochs=5.0,  # 增加预热轮数，让训练更平稳
            warmup_momentum=0.8,
            warmup_bias_lr=0.1,
            
            # 数据增强配置（平衡增强强度以提升泛化，减少计算负载）
            hsv_h=0.015,        # 色调增强
            hsv_s=0.6,          # 饱和度增强（略微降低）
            hsv_v=0.3,          # 明度增强（略微降低）
            degrees=0.0,        # 旋转角度（已在离线增强）
            translate=0.08,     # 平移（略微降低）
            scale=0.4,          # 缩放（略微降低）
            shear=0.0,          # 剪切
            perspective=0.0,    # 透视变换
            flipud=0.0,         # 上下翻转
            fliplr=0.5,         # 左右翻转
            mosaic=0.6,         # Mosaic增强（进一步降低以减少显存和CPU使用）
            mixup=0.0,          # Mixup增强
            copy_paste=0.0,     # Copy-paste增强
            
            # 损失函数权重（针对mAP优化 - 提高box和dfl权重）
            box=7.5,            # box损失权重（保持较高以提升定位精度）
            cls=0.5,            # 分类损失权重
            dfl=1.5,            # DFL损失权重（保持较高以提升边界框质量）
            
            # mAP相关配置
            iou=0.7,            # 训练时的IoU阈值
            conf=0.001,         # 目标置信度阈值（低阈值以检测更多目标）
            
            # 验证和保存配置
            val=True,           # 每个epoch后验证
            save=True,          # 保存检查点
            save_period=save_period,  # 每N个epoch保存一次
            patience=patience,  # 早停耐心值
            plots=False,        # 关闭训练过程中的绘图以节省资源
            
            # 其他配置
            project=project,
            name=name,
            exist_ok=True,
            pretrained=True,
            verbose=True,
            seed=42,
            deterministic=False,
            single_cls=False,
            rect=False,         # 矩形训练
            cos_lr=True,        # 余弦学习率调度
            close_mosaic=10,    # 最后N个epoch关闭mosaic
            amp=True,           # 自动混合精度训练
            fraction=1.0,       # 使用全部数据
            profile=False,
            freeze=None,        # 冻结层数
            
            # 多尺度训练（暂时关闭以减少显存使用）
            multi_scale=False,
            
            # 类别权重（如果类别不平衡可以调整）
            # cls_weight=None,  # 可以设置为[1.0, 1.0, 2.0, 2.0]来增加火灾类别权重
        )
        
        print("\n" + "="*60)
        print("✅ 训练完成！")
        print("="*60)
        
        return results
    
    def evaluate(self, weights='runs/detect/lkyw_fire_detection/weights/best.pt'):
        """
        评估模型性能
        
        Args:
            weights: 模型权重路径
        """
        print("\n" + "="*60)
        print("📊 评估模型性能")
        print("="*60)
        
        model = YOLO(weights)
        
        # 在验证集上评估
        metrics = model.val(
            data=self.data_yaml,
            split='val',
            imgsz=640,
            batch=16,
            conf=0.001,  # 低置信度阈值
            iou=0.6,     # NMS IoU阈值
            max_det=300,
            plots=True,
            save_json=True,
            verbose=True
        )
        
        print("\n📈 关键指标:")
        print(f"  mAP50: {metrics.box.map50:.4f}")
        print(f"  mAP50-95: {metrics.box.map:.4f}")
        print(f"  Precision: {metrics.box.mp:.4f}")
        print(f"  Recall: {metrics.box.mr:.4f}")
        
        # 在测试集上评估
        print("\n" + "="*60)
        print("📊 测试集评估")
        print("="*60)
        
        test_metrics = model.val(
            data=self.data_yaml,
            split='test',
            imgsz=640,
            batch=16,
            conf=0.001,
            iou=0.6,
            max_det=300,
            plots=True,
            save_json=True,
            verbose=True
        )
        
        print("\n📈 测试集关键指标:")
        print(f"  mAP50: {test_metrics.box.map50:.4f}")
        print(f"  mAP50-95: {test_metrics.box.map:.4f}")
        print(f"  Precision: {test_metrics.box.mp:.4f}")
        print(f"  Recall: {test_metrics.box.mr:.4f}")
        
        return metrics, test_metrics


def main():
    """主函数"""
    # 配置路径
    data_yaml = 'dataset_split/dataset.yaml'
    
    # 选择模型大小
    # yolo11n.pt - 最快，适合快速实验
    # yolo11s.pt - 平衡速度和精度
    # yolo11m.pt - 中等模型，推荐
    # yolo11l.pt - 大模型，更高精度
    # yolo11x.pt - 最大模型，最高精度
    
    model_name = 'yolo11n.pt'  # 使用n模型（最轻量）确保系统稳定，mAP略低但不会死机
    
    # 创建训练器
    trainer = YOLOv11Trainer(
        data_yaml=data_yaml,
        model_name=model_name
    )
    
    # 开始训练
    print("\n💡 训练提示:")
    print("  - 使用YOLOv11n模型（轻量级，确保系统稳定）")
    print("  - Batch size=2，Workers=4（防止系统死机）")
    print("  - 使用AdamW优化器和余弦学习率调度")
    print("  - 启用Mosaic增强提升小目标检测")
    print("  - 早停机制防止过拟合")
    print("  - 重点优化mAP50和mAP50-95指标")
    print("  - 关闭缓存和绘图以节省资源")
    print("\n⚠️  如果仍然死机，请:")
    print("  1. 关闭其他占用资源的程序")
    print("  2. 确保虚拟内存设置为32GB")
    print("  3. 考虑使用更小的图片尺寸(如480)\n")
    
    results = trainer.train(
        epochs=300,        # 训练轮数
        imgsz=640,         # 图片尺寸
        batch=2,           # 批次大小（降低到2以确保系统稳定）
        patience=50,       # 早停耐心值
        save_period=20,    # 每20个epoch保存一次（减少IO操作）
        project='runs/detect',
        name='lkyw_fire_detection'
    )
    
    # 训练完成后评估
    print("\n🎯 开始模型评估...")
    trainer.evaluate()
    
    print("\n" + "="*60)
    print("🎉 所有任务完成！")
    print("="*60)
    print("📁 模型保存位置: runs/detect/lkyw_fire_detection/weights/")
    print("📊 最佳模型: best.pt")
    print("📊 最后模型: last.pt")
    print("\n💡 使用模型进行预测:")
    print("  yolo predict model=runs/detect/lkyw_fire_detection/weights/best.pt source=your_image.jpg")


if __name__ == "__main__":
    main()
