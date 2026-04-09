#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成训练过程的可视化图表
包括：损失曲线、mAP曲线、Precision-Recall曲线等
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

def plot_training_curves(csv_path, output_dir):
    """
    绘制训练曲线图
    
    Args:
        csv_path: results.csv文件路径
        output_dir: 输出目录
    """
    # 读取训练结果
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()  # 去除列名空格
    
    print(f"📊 读取训练数据: {len(df)} 个epoch")
    print(f"📋 可用列: {list(df.columns)}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 损失函数曲线（训练集）
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('训练集损失函数变化曲线', fontsize=16, fontweight='bold')
    
    # Box Loss
    axes[0].plot(df['epoch'], df['train/box_loss'], 'b-', linewidth=2, label='Box Loss')
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('边界框损失 (Box Loss)', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Cls Loss
    axes[1].plot(df['epoch'], df['train/cls_loss'], 'g-', linewidth=2, label='Cls Loss')
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Loss', fontsize=12)
    axes[1].set_title('分类损失 (Classification Loss)', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    # DFL Loss
    axes[2].plot(df['epoch'], df['train/dfl_loss'], 'r-', linewidth=2, label='DFL Loss')
    axes[2].set_xlabel('Epoch', fontsize=12)
    axes[2].set_ylabel('Loss', fontsize=12)
    axes[2].set_title('分布焦点损失 (DFL Loss)', fontsize=14)
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    plt.tight_layout()
    train_loss_path = os.path.join(output_dir, '1_训练集损失曲线.png')
    plt.savefig(train_loss_path, dpi=300, bbox_inches='tight')
    print(f"✅ 保存: {train_loss_path}")
    plt.close()
    
    # 2. 损失函数曲线（验证集）
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('验证集损失函数变化曲线', fontsize=16, fontweight='bold')
    
    # Box Loss
    axes[0].plot(df['epoch'], df['val/box_loss'], 'b-', linewidth=2, label='Val Box Loss')
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('边界框损失 (Box Loss)', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Cls Loss
    axes[1].plot(df['epoch'], df['val/cls_loss'], 'g-', linewidth=2, label='Val Cls Loss')
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Loss', fontsize=12)
    axes[1].set_title('分类损失 (Classification Loss)', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    # DFL Loss
    axes[2].plot(df['epoch'], df['val/dfl_loss'], 'r-', linewidth=2, label='Val DFL Loss')
    axes[2].set_xlabel('Epoch', fontsize=12)
    axes[2].set_ylabel('Loss', fontsize=12)
    axes[2].set_title('分布焦点损失 (DFL Loss)', fontsize=14)
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    plt.tight_layout()
    val_loss_path = os.path.join(output_dir, '2_验证集损失曲线.png')
    plt.savefig(val_loss_path, dpi=300, bbox_inches='tight')
    print(f"✅ 保存: {val_loss_path}")
    plt.close()
    
    # 3. 训练集vs验证集损失对比
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('训练集 vs 验证集损失对比', fontsize=16, fontweight='bold')
    
    # Box Loss
    axes[0].plot(df['epoch'], df['train/box_loss'], 'b-', linewidth=2, label='Train', alpha=0.7)
    axes[0].plot(df['epoch'], df['val/box_loss'], 'r-', linewidth=2, label='Val', alpha=0.7)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('边界框损失对比', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Cls Loss
    axes[1].plot(df['epoch'], df['train/cls_loss'], 'b-', linewidth=2, label='Train', alpha=0.7)
    axes[1].plot(df['epoch'], df['val/cls_loss'], 'r-', linewidth=2, label='Val', alpha=0.7)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Loss', fontsize=12)
    axes[1].set_title('分类损失对比', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    # DFL Loss
    axes[2].plot(df['epoch'], df['train/dfl_loss'], 'b-', linewidth=2, label='Train', alpha=0.7)
    axes[2].plot(df['epoch'], df['val/dfl_loss'], 'r-', linewidth=2, label='Val', alpha=0.7)
    axes[2].set_xlabel('Epoch', fontsize=12)
    axes[2].set_ylabel('Loss', fontsize=12)
    axes[2].set_title('DFL损失对比', fontsize=14)
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    plt.tight_layout()
    compare_loss_path = os.path.join(output_dir, '3_损失对比曲线.png')
    plt.savefig(compare_loss_path, dpi=300, bbox_inches='tight')
    print(f"✅ 保存: {compare_loss_path}")
    plt.close()
    
    # 4. mAP性能曲线
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('模型性能指标变化曲线', fontsize=16, fontweight='bold')
    
    # mAP@0.5
    axes[0, 0].plot(df['epoch'], df['metrics/mAP50(B)'], 'b-', linewidth=2, marker='o', 
                    markersize=3, label='mAP@0.5')
    axes[0, 0].set_xlabel('Epoch', fontsize=12)
    axes[0, 0].set_ylabel('mAP', fontsize=12)
    axes[0, 0].set_title('mAP@0.5 (IoU=0.5)', fontsize=14)
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].legend()
    axes[0, 0].set_ylim([0, 1])
    
    # mAP@0.5:0.95
    axes[0, 1].plot(df['epoch'], df['metrics/mAP50-95(B)'], 'g-', linewidth=2, marker='s', 
                    markersize=3, label='mAP@0.5:0.95')
    axes[0, 1].set_xlabel('Epoch', fontsize=12)
    axes[0, 1].set_ylabel('mAP', fontsize=12)
    axes[0, 1].set_title('mAP@0.5:0.95 (IoU=0.5-0.95)', fontsize=14)
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()
    axes[0, 1].set_ylim([0, 1])
    
    # Precision
    axes[1, 0].plot(df['epoch'], df['metrics/precision(B)'], 'r-', linewidth=2, marker='^', 
                    markersize=3, label='Precision')
    axes[1, 0].set_xlabel('Epoch', fontsize=12)
    axes[1, 0].set_ylabel('Precision', fontsize=12)
    axes[1, 0].set_title('精确率 (Precision)', fontsize=14)
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()
    axes[1, 0].set_ylim([0, 1])
    
    # Recall
    axes[1, 1].plot(df['epoch'], df['metrics/recall(B)'], 'm-', linewidth=2, marker='v', 
                    markersize=3, label='Recall')
    axes[1, 1].set_xlabel('Epoch', fontsize=12)
    axes[1, 1].set_ylabel('Recall', fontsize=12)
    axes[1, 1].set_title('召回率 (Recall)', fontsize=14)
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend()
    axes[1, 1].set_ylim([0, 1])
    
    plt.tight_layout()
    metrics_path = os.path.join(output_dir, '4_性能指标曲线.png')
    plt.savefig(metrics_path, dpi=300, bbox_inches='tight')
    print(f"✅ 保存: {metrics_path}")
    plt.close()
    
    # 5. 综合性能曲线（单图）
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df['epoch'], df['metrics/mAP50(B)'], 'b-', linewidth=2.5, 
            label='mAP@0.5', marker='o', markersize=4)
    ax.plot(df['epoch'], df['metrics/mAP50-95(B)'], 'g-', linewidth=2.5, 
            label='mAP@0.5:0.95', marker='s', markersize=4)
    ax.plot(df['epoch'], df['metrics/precision(B)'], 'r-', linewidth=2.5, 
            label='Precision', marker='^', markersize=4)
    ax.plot(df['epoch'], df['metrics/recall(B)'], 'm-', linewidth=2.5, 
            label='Recall', marker='v', markersize=4)
    
    ax.set_xlabel('Epoch', fontsize=14, fontweight='bold')
    ax.set_ylabel('Score', fontsize=14, fontweight='bold')
    ax.set_title('模型性能综合曲线', fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=12, loc='lower right')
    ax.set_ylim([0, 1])
    
    # 标注最佳值
    best_epoch = df['metrics/mAP50(B)'].idxmax()
    best_map50 = df.loc[best_epoch, 'metrics/mAP50(B)']
    ax.annotate(f'Best mAP@0.5: {best_map50:.4f}\nEpoch: {df.loc[best_epoch, "epoch"]:.0f}',
                xy=(df.loc[best_epoch, 'epoch'], best_map50),
                xytext=(df.loc[best_epoch, 'epoch']+10, best_map50-0.1),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2),
                fontsize=11, bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    plt.tight_layout()
    combined_path = os.path.join(output_dir, '5_综合性能曲线.png')
    plt.savefig(combined_path, dpi=300, bbox_inches='tight')
    print(f"✅ 保存: {combined_path}")
    plt.close()
    
    # 6. 学习率变化曲线（显示所有参数组）
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    fig.suptitle('学习率变化曲线', fontsize=16, fontweight='bold')
    
    # 左图：完整学习率曲线（三条线）
    axes[0].plot(df['epoch'], df['lr/pg0'], 'b-', linewidth=2.5, label='pg0 (偏置参数)', alpha=0.8)
    axes[0].plot(df['epoch'], df['lr/pg1'], 'g-', linewidth=2.5, label='pg1 (权重无衰减)', alpha=0.8)
    axes[0].plot(df['epoch'], df['lr/pg2'], 'r-', linewidth=2.5, label='pg2 (权重有衰减)', alpha=0.8)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Learning Rate', fontsize=12)
    axes[0].set_title('完整学习率曲线（含Warmup）', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=11)
    
    # 标注Warmup阶段的差异
    axes[0].axvline(x=5, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Warmup结束')
    axes[0].text(5, 0.04, 'Warmup结束\n(Epoch 5)', fontsize=10, 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    # 右图：Warmup后的学习率曲线（放大显示）
    warmup_end = 5
    axes[1].plot(df['epoch'][warmup_end:], df['lr/pg0'][warmup_end:], 'b-', 
                linewidth=2.5, label='pg0 (偏置参数)', alpha=0.8)
    axes[1].plot(df['epoch'][warmup_end:], df['lr/pg1'][warmup_end:], 'g-', 
                linewidth=2.5, label='pg1 (权重无衰减)', alpha=0.8)
    axes[1].plot(df['epoch'][warmup_end:], df['lr/pg2'][warmup_end:], 'r-', 
                linewidth=2.5, label='pg2 (权重有衰减)', alpha=0.8)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Learning Rate', fontsize=12)
    axes[1].set_title('Warmup后学习率曲线（余弦衰减）', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=11)
    
    plt.tight_layout()
    lr_path = os.path.join(output_dir, '6_学习率曲线.png')
    plt.savefig(lr_path, dpi=300, bbox_inches='tight')
    print(f"✅ 保存: {lr_path}")
    plt.close()
    
    # 7. 生成训练结果摘要
    print("\n" + "="*60)
    print("📊 训练结果摘要")
    print("="*60)
    
    last_epoch = df.iloc[-1]
    best_epoch_idx = df['metrics/mAP50(B)'].idxmax()
    best_epoch = df.iloc[best_epoch_idx]
    
    print(f"\n【最后一轮 (Epoch {last_epoch['epoch']:.0f})】")
    print(f"  mAP@0.5:        {last_epoch['metrics/mAP50(B)']:.4f} ({last_epoch['metrics/mAP50(B)']*100:.2f}%)")
    print(f"  mAP@0.5:0.95:   {last_epoch['metrics/mAP50-95(B)']:.4f} ({last_epoch['metrics/mAP50-95(B)']*100:.2f}%)")
    print(f"  Precision:      {last_epoch['metrics/precision(B)']:.4f} ({last_epoch['metrics/precision(B)']*100:.2f}%)")
    print(f"  Recall:         {last_epoch['metrics/recall(B)']:.4f} ({last_epoch['metrics/recall(B)']*100:.2f}%)")
    
    print(f"\n【最佳性能 (Epoch {best_epoch['epoch']:.0f})】")
    print(f"  mAP@0.5:        {best_epoch['metrics/mAP50(B)']:.4f} ({best_epoch['metrics/mAP50(B)']*100:.2f}%)")
    print(f"  mAP@0.5:0.95:   {best_epoch['metrics/mAP50-95(B)']:.4f} ({best_epoch['metrics/mAP50-95(B)']*100:.2f}%)")
    print(f"  Precision:      {best_epoch['metrics/precision(B)']:.4f} ({best_epoch['metrics/precision(B)']*100:.2f}%)")
    print(f"  Recall:         {best_epoch['metrics/recall(B)']:.4f} ({best_epoch['metrics/recall(B)']*100:.2f}%)")
    
    print(f"\n【损失函数 (最后一轮)】")
    print(f"  Train Box Loss: {last_epoch['train/box_loss']:.4f}")
    print(f"  Train Cls Loss: {last_epoch['train/cls_loss']:.4f}")
    print(f"  Train DFL Loss: {last_epoch['train/dfl_loss']:.4f}")
    print(f"  Val Box Loss:   {last_epoch['val/box_loss']:.4f}")
    print(f"  Val Cls Loss:   {last_epoch['val/cls_loss']:.4f}")
    print(f"  Val DFL Loss:   {last_epoch['val/dfl_loss']:.4f}")
    
    # 保存摘要到文本文件
    summary_path = os.path.join(output_dir, '训练结果摘要.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("两客一危火灾检测系统 - 训练结果摘要\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"【最后一轮 (Epoch {last_epoch['epoch']:.0f})】\n")
        f.write(f"  mAP@0.5:        {last_epoch['metrics/mAP50(B)']:.4f} ({last_epoch['metrics/mAP50(B)']*100:.2f}%)\n")
        f.write(f"  mAP@0.5:0.95:   {last_epoch['metrics/mAP50-95(B)']:.4f} ({last_epoch['metrics/mAP50-95(B)']*100:.2f}%)\n")
        f.write(f"  Precision:      {last_epoch['metrics/precision(B)']:.4f} ({last_epoch['metrics/precision(B)']*100:.2f}%)\n")
        f.write(f"  Recall:         {last_epoch['metrics/recall(B)']:.4f} ({last_epoch['metrics/recall(B)']*100:.2f}%)\n\n")
        
        f.write(f"【最佳性能 (Epoch {best_epoch['epoch']:.0f})】\n")
        f.write(f"  mAP@0.5:        {best_epoch['metrics/mAP50(B)']:.4f} ({best_epoch['metrics/mAP50(B)']*100:.2f}%)\n")
        f.write(f"  mAP@0.5:0.95:   {best_epoch['metrics/mAP50-95(B)']:.4f} ({best_epoch['metrics/mAP50-95(B)']*100:.2f}%)\n")
        f.write(f"  Precision:      {best_epoch['metrics/precision(B)']:.4f} ({best_epoch['metrics/precision(B)']*100:.2f}%)\n")
        f.write(f"  Recall:         {best_epoch['metrics/recall(B)']:.4f} ({best_epoch['metrics/recall(B)']*100:.2f}%)\n\n")
        
        f.write(f"【损失函数 (最后一轮)】\n")
        f.write(f"  Train Box Loss: {last_epoch['train/box_loss']:.4f}\n")
        f.write(f"  Train Cls Loss: {last_epoch['train/cls_loss']:.4f}\n")
        f.write(f"  Train DFL Loss: {last_epoch['train/dfl_loss']:.4f}\n")
        f.write(f"  Val Box Loss:   {last_epoch['val/box_loss']:.4f}\n")
        f.write(f"  Val Cls Loss:   {last_epoch['val/cls_loss']:.4f}\n")
        f.write(f"  Val DFL Loss:   {last_epoch['val/dfl_loss']:.4f}\n")
    
    print(f"\n✅ 保存摘要: {summary_path}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # 配置路径
    csv_path = "runs/detect/lkyw_fire_detection/results.csv"
    output_dir = "runs/detect/lkyw_fire_detection/training_plots"
    
    print("🚀 开始生成训练可视化图表...")
    print(f"📂 输入文件: {csv_path}")
    print(f"📂 输出目录: {output_dir}\n")
    
    try:
        plot_training_curves(csv_path, output_dir)
        print("\n🎉 所有图表生成完成！")
        print(f"📁 请查看目录: {output_dir}")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
