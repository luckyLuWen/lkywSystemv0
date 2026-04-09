#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练集数据增强脚本
对现有训练集进行离线数据增强，生成增强后的图片和标签
"""

import os
import cv2
import numpy as np
import albumentations as A
from pathlib import Path
from tqdm import tqdm
import argparse


class TrainDatasetAugmentor:
    def __init__(self, train_dir, output_dir=None, num_augmentations=3):
        """
        初始化数据增强器
        
        Args:
            train_dir: 训练集目录路径（包含images和labels子目录）
            output_dir: 输出目录，如果为None则在原目录增强
            num_augmentations: 每张图片生成的增强版本数量
        """
        self.train_dir = Path(train_dir)
        self.output_dir = Path(output_dir) if output_dir else self.train_dir
        self.num_augmentations = num_augmentations
        
        # 确保输出目录存在
        (self.output_dir / 'images').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'labels').mkdir(parents=True, exist_ok=True)
        
        print(f"📂 训练集目录: {self.train_dir}")
        print(f"📂 输出目录: {self.output_dir}")
        print(f"🔢 每张图片生成 {num_augmentations} 个增强版本")
    
    def setup_augmentation(self):
        """
        设置数据增强管道
        针对火灾检测场景优化的增强策略
        """
        return A.Compose([
            # 几何变换
            A.HorizontalFlip(p=0.5),
            A.RandomRotate90(p=0.2),
            A.ShiftScaleRotate(
                shift_limit=0.1,      # 平移范围
                scale_limit=0.15,     # 缩放范围
                rotate_limit=15,      # 旋转角度
                border_mode=cv2.BORDER_CONSTANT,
                p=0.6
            ),
            
            # 颜色和亮度调整（对火焰检测很重要）
            A.RandomBrightnessContrast(
                brightness_limit=0.25,
                contrast_limit=0.25,
                p=0.6
            ),
            A.RandomGamma(gamma_limit=(80, 120), p=0.4),
            A.HueSaturationValue(
                hue_shift_limit=10,
                sat_shift_limit=20,
                val_shift_limit=20,
                p=0.4
            ),
            
            # 图像质量调整
            A.OneOf([
                A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
                A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
            ], p=0.3),
            
            A.OneOf([
                A.Blur(blur_limit=3, p=1.0),
                A.MedianBlur(blur_limit=3, p=1.0),
                A.GaussianBlur(blur_limit=3, p=1.0),
            ], p=0.2),
            
            # 对比度增强（帮助检测火焰）
            A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.3),
            
            # 天气和光照模拟
            A.RandomShadow(
                shadow_roi=(0, 0.5, 1, 1),
                num_shadows_lower=1,
                num_shadows_upper=2,
                shadow_dimension=5,
                p=0.2
            ),
            
        ], bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels'],
            min_visibility=0.3  # 保留至少30%可见的目标
        ))
    
    def load_yolo_labels(self, label_path):
        """
        加载YOLO格式的标签文件
        
        Returns:
            bboxes: list of [x_center, y_center, width, height]
            class_labels: list of class ids
        """
        bboxes = []
        class_labels = []
        
        if not label_path.exists():
            return bboxes, class_labels
        
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    x_center, y_center, width, height = map(float, parts[1:5])
                    bboxes.append([x_center, y_center, width, height])
                    class_labels.append(class_id)
        
        return bboxes, class_labels
    
    def save_yolo_labels(self, label_path, bboxes, class_labels):
        """保存YOLO格式的标签文件"""
        with open(label_path, 'w') as f:
            for bbox, class_id in zip(bboxes, class_labels):
                f.write(f"{class_id} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
    
    def augment_single_image(self, img_path, label_path, augmentation):
        """
        对单张图片进行增强
        
        Returns:
            list of dict: 增强后的图片和标签数据
        """
        # 读取图片
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"⚠️ 无法读取图片: {img_path}")
            return []
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 读取标签
        bboxes, class_labels = self.load_yolo_labels(label_path)
        
        augmented_data = []
        
        # 生成多个增强版本
        for i in range(self.num_augmentations):
            try:
                # 应用增强
                if len(bboxes) > 0:
                    augmented = augmentation(
                        image=image,
                        bboxes=bboxes,
                        class_labels=class_labels
                    )
                else:
                    # 没有标注框的图片也进行增强
                    augmented = augmentation(image=image, bboxes=[], class_labels=[])
                
                augmented_data.append({
                    'image': augmented['image'],
                    'bboxes': augmented['bboxes'],
                    'class_labels': augmented['class_labels'],
                    'suffix': f'_aug{i+1}'
                })
            except Exception as e:
                print(f"⚠️ 增强失败 {img_path.name} (版本{i+1}): {e}")
                continue
        
        return augmented_data
    
    def get_image_files(self):
        """获取所有训练集图片文件"""
        image_dir = self.train_dir / 'images'
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.avif', '.webp']
        
        image_files = []
        for ext in image_extensions:
            image_files.extend(list(image_dir.glob(f'*{ext}')))
            image_files.extend(list(image_dir.glob(f'*{ext.upper()}')))
        
        return sorted(image_files)
    
    def copy_original_files(self):
        """如果输出目录不同，先复制原始文件"""
        if self.output_dir == self.train_dir:
            print("📋 在原目录进行增强，跳过复制步骤")
            return
        
        print("📋 复制原始文件到输出目录...")
        import shutil
        
        # 复制图片
        for img_file in (self.train_dir / 'images').iterdir():
            if img_file.is_file():
                shutil.copy2(img_file, self.output_dir / 'images' / img_file.name)
        
        # 复制标签
        for label_file in (self.train_dir / 'labels').iterdir():
            if label_file.is_file():
                shutil.copy2(label_file, self.output_dir / 'labels' / label_file.name)
        
        print("✅ 原始文件复制完成")
    
    def augment_dataset(self):
        """对整个训练集进行增强"""
        print("\n" + "="*60)
        print("🚀 开始数据增强...")
        print("="*60)
        
        # 获取所有图片
        image_files = self.get_image_files()
        total_images = len(image_files)
        
        if total_images == 0:
            print("❌ 未找到图片文件！")
            return
        
        print(f"📊 找到 {total_images} 张原始图片")
        
        # 如果输出目录不同，先复制原始文件
        self.copy_original_files()
        
        # 设置增强管道
        augmentation = self.setup_augmentation()
        
        # 统计信息
        success_count = 0
        fail_count = 0
        total_augmented = 0
        
        # 使用进度条处理每张图片
        for img_path in tqdm(image_files, desc="增强进度", unit="张"):
            label_path = self.train_dir / 'labels' / f"{img_path.stem}.txt"
            
            # 生成增强数据
            augmented_data = self.augment_single_image(img_path, label_path, augmentation)
            
            if len(augmented_data) == 0:
                fail_count += 1
                continue
            
            # 保存增强后的图片和标签
            for aug_data in augmented_data:
                try:
                    # 生成文件名
                    aug_name = f"{img_path.stem}{aug_data['suffix']}{img_path.suffix}"
                    aug_img_path = self.output_dir / 'images' / aug_name
                    aug_label_path = self.output_dir / 'labels' / f"{img_path.stem}{aug_data['suffix']}.txt"
                    
                    # 保存图片
                    aug_image_bgr = cv2.cvtColor(aug_data['image'], cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(aug_img_path), aug_image_bgr)
                    
                    # 保存标签
                    self.save_yolo_labels(
                        aug_label_path,
                        aug_data['bboxes'],
                        aug_data['class_labels']
                    )
                    
                    total_augmented += 1
                except Exception as e:
                    print(f"⚠️ 保存失败 {aug_name}: {e}")
                    continue
            
            success_count += 1
        
        # 打印统计信息
        print("\n" + "="*60)
        print("✅ 数据增强完成！")
        print("="*60)
        print(f"📊 原始图片: {total_images} 张")
        print(f"✅ 成功增强: {success_count} 张")
        print(f"❌ 失败: {fail_count} 张")
        print(f"🎯 生成增强图片: {total_augmented} 张")
        print(f"📈 总图片数: {total_images + total_augmented} 张")
        print(f"📂 输出目录: {self.output_dir}")
        print("="*60)
        
        return {
            'original': total_images,
            'success': success_count,
            'failed': fail_count,
            'augmented': total_augmented,
            'total': total_images + total_augmented
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='训练集数据增强工具')
    parser.add_argument(
        '--train_dir',
        type=str,
        default='dataset_split/train',
        help='训练集目录路径（包含images和labels子目录）'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default=None,
        help='输出目录路径（默认为None，在原目录增强）'
    )
    parser.add_argument(
        '--num_aug',
        type=int,
        default=3,
        help='每张图片生成的增强版本数量（默认3）'
    )
    
    args = parser.parse_args()
    
    # 检查训练集目录
    train_dir = Path(args.train_dir)
    if not train_dir.exists():
        print(f"❌ 训练集目录不存在: {train_dir}")
        print("请确保目录路径正确")
        return
    
    if not (train_dir / 'images').exists() or not (train_dir / 'labels').exists():
        print(f"❌ 训练集目录缺少 images 或 labels 子目录")
        return
    
    # 创建增强器
    augmentor = TrainDatasetAugmentor(
        train_dir=args.train_dir,
        output_dir=args.output_dir,
        num_augmentations=args.num_aug
    )
    
    # 执行增强
    stats = augmentor.augment_dataset()
    
    print("\n🎉 数据增强完成！现在可以使用增强后的数据集进行YOLOv11训练了。")


if __name__ == "__main__":
    main()
