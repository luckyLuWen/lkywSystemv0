#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集划分脚本
1. 从train/images中随机选取40张图片作为真实测试集，移动到real_test文件夹
2. 将剩余图片划分为训练集(70%)、验证集(20%)、测试集(10%)
"""

import os
import shutil
import random
from pathlib import Path
from collections import defaultdict

class DatasetSplitter:
    def __init__(self, train_images_dir, real_test_dir, output_dir="dataset_split",
                 real_test_count=40, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1):
        self.train_images_dir = Path(train_images_dir)
        self.real_test_dir = Path(real_test_dir)
        self.output_dir = Path(output_dir)
        self.real_test_count = real_test_count
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        
        # 创建输出目录结构
        for split in ['train', 'val', 'test']:
            (self.output_dir / split / 'images').mkdir(parents=True, exist_ok=True)
            (self.output_dir / split / 'labels').mkdir(parents=True, exist_ok=True)
        
        # 创建真实测试目录
        self.real_test_dir.mkdir(exist_ok=True)
        (self.real_test_dir / 'images').mkdir(exist_ok=True)
        (self.real_test_dir / 'labels').mkdir(exist_ok=True)
    
    def get_all_images(self):
        """获取所有图片文件"""
        print("🔍 获取所有图片文件...")
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.avif', '.webp']
        all_images = []
        
        # 获取所有图片文件
        for ext in image_extensions:
            for img_path in self.train_images_dir.glob(f"*{ext}"):
                all_images.append(img_path)
        
        print(f"   找到 {len(all_images)} 张图片")
        return all_images
    
    def move_to_real_test(self, all_images):
        """随机选取图片移动到真实测试集"""
        print(f"\n📦 随机选取 {self.real_test_count} 张图片作为真实测试集...")
        
        # 随机选择图片
        random.shuffle(all_images)
        real_test_images = all_images[:self.real_test_count]
        remaining_images = all_images[self.real_test_count:]
        
        # 移动图片和标签
        moved_count = 0
        for img_path in real_test_images:
            # 移动图片
            dest_img = self.real_test_dir / 'images' / img_path.name
            shutil.copy2(img_path, dest_img)
            
            # 查找并移动对应的标签文件
            label_path = self.train_images_dir.parent / 'labels' / f"{img_path.stem}.txt"
            if label_path.exists():
                dest_label = self.real_test_dir / 'labels' / label_path.name
                shutil.copy2(label_path, dest_label)
            
            moved_count += 1
            if moved_count % 10 == 0:
                print(f"   已移动 {moved_count}/{self.real_test_count} 张图片")
        
        print(f"✅ 成功移动 {moved_count} 张图片到真实测试集")
        return remaining_images
    
    def split_dataset(self, images):
        """将剩余图片划分为训练集、验证集和测试集"""
        print(f"\n📊 划分剩余 {len(images)} 张图片...")
        
        # 随机打乱
        random.shuffle(images)
        
        # 计算划分点
        total = len(images)
        train_end = int(total * self.train_ratio)
        val_end = train_end + int(total * self.val_ratio)
        
        splits = {
            'train': images[:train_end],
            'val': images[train_end:val_end],
            'test': images[val_end:]
        }
        
        print(f"   训练集: {len(splits['train'])} 张 ({self.train_ratio*100:.0f}%)")
        print(f"   验证集: {len(splits['val'])} 张 ({self.val_ratio*100:.0f}%)")
        print(f"   测试集: {len(splits['test'])} 张 ({self.test_ratio*100:.0f}%)")
        
        return splits
    
    def copy_files(self, splits):
        """复制文件到对应的目录"""
        print("\n📁 复制文件到目标目录...")
        
        for split_name, images in splits.items():
            print(f"\n   处理 {split_name} 集...")
            copied_count = 0
            
            for img_path in images:
                # 复制图片
                dest_img = self.output_dir / split_name / 'images' / img_path.name
                shutil.copy2(img_path, dest_img)
                
                # 复制标签
                label_path = self.train_images_dir.parent / 'labels' / f"{img_path.stem}.txt"
                if label_path.exists():
                    dest_label = self.output_dir / split_name / 'labels' / label_path.name
                    shutil.copy2(label_path, dest_label)
                
                copied_count += 1
                if copied_count % 100 == 0:
                    print(f"      已复制 {copied_count}/{len(images)} 张")
            
            print(f"   ✅ {split_name} 集完成: {copied_count} 张图片")
    
    def run(self):
        """执行完整的数据集划分流程"""
        print("=" * 60)
        print("🚀 开始数据集划分")
        print("=" * 60)
        
        # 设置随机种子以保证可重复性
        random.seed(42)
        
        # 1. 获取所有图片
        all_images = self.get_all_images()
        
        if len(all_images) < self.real_test_count:
            print(f"❌ 错误: 图片数量({len(all_images)})少于真实测试集需求({self.real_test_count})")
            return
        
        # 2. 移动到真实测试集
        remaining_images = self.move_to_real_test(all_images)
        
        # 3. 划分剩余数据
        splits = self.split_dataset(remaining_images)
        
        # 4. 复制文件
        self.copy_files(splits)
        
        print("\n" + "=" * 60)
        print("✨ 数据集划分完成!")
        print("=" * 60)
        print(f"\n📊 最终统计:")
        print(f"   真实测试集: {self.real_test_count} 张 (位于 {self.real_test_dir})")
        print(f"   训练集: {len(splits['train'])} 张")
        print(f"   验证集: {len(splits['val'])} 张")
        print(f"   测试集: {len(splits['test'])} 张")
        print(f"   总计: {self.real_test_count + sum(len(v) for v in splits.values())} 张")

if __name__ == "__main__":
    splitter = DatasetSplitter(
        train_images_dir=r"d:\All_Dataset\两客一危自制数据集\train\images",
        real_test_dir=r"d:\All_Dataset\两客一危自制数据集\real_test",
        output_dir=r"d:\All_Dataset\两客一危自制数据集\dataset_split",
        real_test_count=40,
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1
    )
    
    splitter.run()
