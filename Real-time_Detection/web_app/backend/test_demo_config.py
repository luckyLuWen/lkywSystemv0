"""
测试演示视频配置
"""

import json
import os


def test_config():
    """测试配置文件是否正确"""
    config_path = 'demo_frames_config.json'
    
    print("=" * 50)
    print("测试演示视频配置")
    print("=" * 50)
    
    # 检查文件是否存在
    if not os.path.exists(config_path):
        print(f"\n❌ 配置文件不存在: {config_path}")
        return False
    
    print(f"\n✓ 配置文件存在: {config_path}")
    
    # 尝试加载配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✓ 配置文件格式正确")
    except Exception as e:
        print(f"❌ 配置文件解析失败: {e}")
        return False
    
    # 显示配置内容
    print(f"\n当前配置的演示视频数量: {len(config)}")
    print("\n配置详情:")
    print("-" * 50)
    
    for video_name, frames in config.items():
        print(f"\n视频: {video_name}")
        print(f"  目标帧: {frames}")
        print(f"  帧数量: {len(frames)}")
        
        # 验证帧号
        if not isinstance(frames, list):
            print(f"  ⚠️  警告: 帧列表格式不正确")
        elif not all(isinstance(f, int) for f in frames):
            print(f"  ⚠️  警告: 帧号必须是整数")
        elif not all(f >= 0 for f in frames):
            print(f"  ⚠️  警告: 帧号不能为负数")
        else:
            print(f"  ✓ 配置正确")
    
    # 测试文件名匹配
    print("\n" + "=" * 50)
    print("测试文件名匹配")
    print("=" * 50)
    
    test_filenames = [
        "demo1.mp4",
        "test_demo1.mp4",
        "演示视频1.mp4",
        "normal_video.mp4"
    ]
    
    for filename in test_filenames:
        matched = False
        matched_key = None
        
        for config_name in config.keys():
            if config_name in filename or filename in config_name:
                matched = True
                matched_key = config_name
                break
        
        if matched:
            print(f"\n✓ {filename}")
            print(f"  匹配到: {matched_key}")
            print(f"  目标帧: {config[matched_key]}")
        else:
            print(f"\n○ {filename}")
            print(f"  无匹配，将使用正常抽帧模式")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
    
    return True


if __name__ == '__main__':
    test_config()
