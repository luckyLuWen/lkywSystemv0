"""
为 video_test 文件夹生成配置文件
支持小数秒，自动转换为帧号
"""

import json
import os
import cv2
from pathlib import Path


def analyze_video_fps(video_path):
    """分析视频获取帧率"""
    if not os.path.exists(video_path):
        return 30  # 默认30fps
    
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    cap.release()
    
    return fps, total_frames, duration


def convert_seconds_to_frames(seconds_config, video_path=None, default_fps=30):
    """
    将秒数配置转换为帧号配置
    
    Args:
        seconds_config: 包含秒数的配置字典
        video_path: 视频文件路径（用于获取实际帧率）
        default_fps: 默认帧率
    
    Returns:
        帧号列表
    """
    # 获取视频帧率
    if video_path and os.path.exists(video_path):
        fps, total_frames, duration = analyze_video_fps(video_path)
    else:
        fps = default_fps
    
    # 转换秒数为帧号
    seconds = seconds_config.get('seconds', [])
    frames = [int(s * fps) for s in seconds]
    
    return frames, fps


def generate_demo_frames_config(video_test_folder, output_file='demo_frames_config.json'):
    """
    从 video_test 文件夹生成 demo_frames_config.json
    
    Args:
        video_test_folder: video_test 文件夹路径
        output_file: 输出配置文件名
    """
    # 读取 video_test_folder_config.json
    config_file = 'video_test_folder_config.json'
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        print("请先创建 video_test_folder_config.json 文件")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        seconds_config = json.load(f)
    
    # 生成帧号配置
    demo_config = {}
    
    print("=" * 60)
    print("正在生成配置...")
    print("=" * 60)
    
    for video_name, config in seconds_config.items():
        # 构建视频路径
        video_path = os.path.join(video_test_folder, video_name)
        
        # 转换秒数为帧号
        frames, fps = convert_seconds_to_frames(config, video_path)
        
        # 添加到配置
        demo_config[video_name] = frames
        
        # 显示信息
        print(f"\n视频: {video_name}")
        print(f"  秒数: {config['seconds']}")
        print(f"  帧率: {fps} fps")
        print(f"  帧号: {frames}")
        print(f"  说明: {config.get('description', '无')}")
    
    # 保存配置
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(demo_config, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✓ 配置已保存到: {output_file}")
    print("=" * 60)
    
    return demo_config


def add_video_test_config(video_name, seconds, description=""):
    """
    添加单个视频配置
    
    Args:
        video_name: 视频文件名
        seconds: 秒数列表（支持小数）
        description: 描述
    """
    config_file = 'video_test_folder_config.json'
    
    # 读取现有配置
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # 添加新配置
    config[video_name] = {
        "seconds": seconds if isinstance(seconds, list) else [seconds],
        "description": description
    }
    
    # 保存配置
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已添加配置: {video_name}")
    print(f"  秒数: {config[video_name]['seconds']}")
    print(f"  说明: {description}")


def interactive_add():
    """交互式添加配置"""
    print("=" * 60)
    print("添加 video_test 视频配置")
    print("=" * 60)
    
    video_name = input("\n视频文件名（如 video_test1.mp4）: ").strip()
    
    print("\n输入秒数（支持小数），多个用逗号分隔")
    print("例如: 6.67 或 3.5,6.67,10.2")
    seconds_input = input("秒数: ").strip()
    
    # 解析秒数
    try:
        seconds = [float(s.strip()) for s in seconds_input.split(',')]
    except ValueError:
        print("❌ 秒数格式错误")
        return
    
    description = input("描述（可选）: ").strip()
    
    # 添加配置
    add_video_test_config(video_name, seconds, description)


def list_video_test_config():
    """列出所有配置"""
    config_file = 'video_test_folder_config.json'
    
    if not os.path.exists(config_file):
        print("暂无配置")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n" + "=" * 60)
    print("video_test 文件夹配置")
    print("=" * 60)
    
    for video_name, video_config in config.items():
        print(f"\n视频: {video_name}")
        print(f"  秒数: {video_config['seconds']}")
        print(f"  说明: {video_config.get('description', '无')}")


def main():
    """主函数"""
    print("=" * 60)
    print("video_test 配置生成工具")
    print("=" * 60)
    
    while True:
        print("\n请选择操作:")
        print("1. 添加视频配置（交互式）")
        print("2. 列出所有配置")
        print("3. 生成 demo_frames_config.json")
        print("4. 批量添加（从文件夹扫描）")
        print("0. 退出")
        
        choice = input("\n请输入选项: ").strip()
        
        if choice == '1':
            interactive_add()
        elif choice == '2':
            list_video_test_config()
        elif choice == '3':
            video_folder = input("\nvideo_test 文件夹路径: ").strip()
            if not video_folder:
                video_folder = r"d:\All_Dataset\两客一危自制数据集\video_test"
            generate_demo_frames_config(video_folder)
        elif choice == '4':
            batch_add_from_folder()
        elif choice == '0':
            print("\n再见!")
            break
        else:
            print("无效选项")


def batch_add_from_folder():
    """从文件夹批量添加配置"""
    video_folder = input("\nvideo_test 文件夹路径: ").strip()
    if not video_folder:
        video_folder = r"d:\All_Dataset\两客一危自制数据集\video_test"
    
    if not os.path.exists(video_folder):
        print(f"❌ 文件夹不存在: {video_folder}")
        return
    
    # 扫描视频文件
    video_extensions = ['.mp4', '.avi', '.mov']
    video_files = []
    
    for file in os.listdir(video_folder):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            video_files.append(file)
    
    if not video_files:
        print("❌ 未找到视频文件")
        return
    
    print(f"\n找到 {len(video_files)} 个视频文件:")
    for i, video in enumerate(video_files, 1):
        print(f"  {i}. {video}")
    
    print("\n为每个视频输入检测秒数（支持小数）")
    print("直接回车跳过该视频")
    
    config_file = 'video_test_folder_config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    for video in video_files:
        print(f"\n{video}:")
        seconds_input = input("  秒数（逗号分隔）: ").strip()
        
        if not seconds_input:
            continue
        
        try:
            seconds = [float(s.strip()) for s in seconds_input.split(',')]
            description = input("  描述（可选）: ").strip()
            
            config[video] = {
                "seconds": seconds,
                "description": description
            }
            print(f"  ✓ 已添加")
        except ValueError:
            print(f"  ❌ 格式错误，跳过")
    
    # 保存配置
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 配置已保存到: {config_file}")


if __name__ == '__main__':
    main()
