"""
添加演示视频配置工具

使用方法：
1. 直接运行脚本，按提示输入
2. 或者在代码中调用 add_demo_video() 函数

示例：
    python add_demo_video.py
"""

import json
import os
import cv2


def add_demo_video(video_filename=None, target_frames=None):
    """
    添加演示视频配置
    
    Args:
        video_filename: 视频文件名（如 "demo1.mp4"）
        target_frames: 目标帧列表（如 [0, 30, 60, 90]）
    """
    config_path = 'demo_frames_config.json'
    
    # 加载现有配置
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # 交互式输入
    if video_filename is None:
        video_filename = input("请输入视频文件名（如 demo1.mp4）: ").strip()
    
    if target_frames is None:
        print("\n请输入目标帧号，多个帧号用逗号分隔（如 0,30,60,90）")
        frames_input = input("目标帧号: ").strip()
        target_frames = [int(x.strip()) for x in frames_input.split(',')]
    
    # 添加到配置
    config[video_filename] = target_frames
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已添加配置:")
    print(f"  视频: {video_filename}")
    print(f"  目标帧: {target_frames}")
    print(f"\n配置文件: {config_path}")


def analyze_video(video_path):
    """
    分析视频，帮助选择关键帧
    
    Args:
        video_path: 视频文件路径
    """
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"\n视频信息:")
    print(f"  总帧数: {total_frames}")
    print(f"  帧率: {fps} fps")
    print(f"  时长: {duration:.2f} 秒")
    print(f"\n建议:")
    print(f"  - 每秒1帧: {list(range(0, total_frames, fps))[:10]}...")
    print(f"  - 每2秒1帧: {list(range(0, total_frames, fps*2))[:10]}...")
    print(f"  - 每5秒1帧: {list(range(0, total_frames, fps*5))[:10]}...")
    
    cap.release()


def list_demo_videos():
    """列出所有已配置的演示视频"""
    config_path = 'demo_frames_config.json'
    
    if not os.path.exists(config_path):
        print("暂无演示视频配置")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n已配置的演示视频:")
    print("-" * 50)
    for video_name, frames in config.items():
        print(f"\n视频: {video_name}")
        print(f"目标帧: {frames}")
        print(f"帧数量: {len(frames)}")


def remove_demo_video(video_filename):
    """删除演示视频配置"""
    config_path = 'demo_frames_config.json'
    
    if not os.path.exists(config_path):
        print("配置文件不存在")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if video_filename in config:
        del config[video_filename]
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✓ 已删除配置: {video_filename}")
    else:
        print(f"未找到配置: {video_filename}")


if __name__ == '__main__':
    print("=" * 50)
    print("演示视频配置工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 添加演示视频配置")
        print("2. 列出所有配置")
        print("3. 删除配置")
        print("4. 分析视频（帮助选择关键帧）")
        print("0. 退出")
        
        choice = input("\n请输入选项: ").strip()
        
        if choice == '1':
            add_demo_video()
        elif choice == '2':
            list_demo_videos()
        elif choice == '3':
            video_name = input("请输入要删除的视频文件名: ").strip()
            remove_demo_video(video_name)
        elif choice == '4':
            video_path = input("请输入视频文件路径: ").strip()
            analyze_video(video_path)
        elif choice == '0':
            print("\n再见!")
            break
        else:
            print("无效选项，请重新选择")
