"""
测试文件名匹配逻辑
"""

import json

# 读取配置
with open('video_test_folder_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 测试文件名
test_filenames = [
    "video_test1_6.67.mp4",
    "video_test2_4.14.mp4",
    "video_test3_3.6_14.4.mp4",
    "video_test4_4.80.mp4",
    "video_test5_4.80_5.60.mp4",
    "video_test6_7.20.mp4",
    "video_test7_46.00.mp4",
    "video_test8_4.80.mp4",
    "video_test9_5.00.mp4",
    "normal_video.mp4",
    "video_test_3_5_10.mp4"
]

print("=" * 60)
print("文件名匹配测试")
print("=" * 60)

for filename in test_filenames:
    print(f"\n测试文件: {filename}")
    matched = False
    
    for config_name, config_data in config.items():
        if config_name in filename or filename in config_name:
            print(f"  ✓ 匹配配置: {config_name}")
            print(f"    秒数: {config_data['seconds']}")
            print(f"    说明: {config_data.get('description', '无')}")
            matched = True
            break
    
    if not matched:
        print(f"  ○ 无匹配，使用默认模式（每30帧）")

print("\n" + "=" * 60)
