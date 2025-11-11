#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
UI数据集预处理脚本
将边界框标注转换为像素级分割掩码
"""

import os
import json
import numpy as np
from PIL import Image
import argparse


def create_segmentation_mask(width, height, boxes):
    """
    将边界框列表转换为像素级的分割掩码
    
    Args:
        width: 掩码宽度
        height: 掩码高度
        boxes: 边界框列表，每个元素是 [x_min, y_min, x_max, y_max, class_id]
    
    Returns:
        形状为 (height, width) 的二维 NumPy 数组，像素值就是 class_id
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    
    for box in boxes:
        x_min, y_min, x_max, y_max, class_id = box
        
        # 确保坐标在有效范围内
        x_min = max(0, int(x_min))
        y_min = max(0, int(y_min))
        x_max = min(width, int(x_max))
        y_max = min(height, int(y_max))
        
        # 将边界框区域填充为对应的类别ID
        if x_max > x_min and y_max > y_min:
            mask[y_min:y_max, x_min:x_max] = int(class_id)
    
    return mask


def parse_rico_json(json_path):
    """
    解析Rico数据集的JSON标注文件
    
    Args:
        json_path: JSON文件路径
    
    Returns:
        包含图片路径和边界框列表的字典
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Rico数据集格式：假设JSON包含 'bounds' 字段，每个元素有 'class' 和坐标信息
    # 这里需要根据实际JSON格式调整
    boxes = []
    class_mapping = {}  # 类别名称到ID的映射
    
    if 'bounds' in data:
        for i, item in enumerate(data['bounds']):
            if 'class' in item:
                class_name = item['class']
                if class_name not in class_mapping:
                    class_mapping[class_name] = len(class_mapping) + 1  # 从1开始，0作为背景
                
                class_id = class_mapping[class_name]
                
                # 提取坐标 (假设格式为 [x, y, width, height] 或 [x_min, y_min, x_max, y_max])
                if 'bounds' in item:
                    bounds = item['bounds']
                    if len(bounds) == 4:
                        # 判断是 [x, y, w, h] 还是 [x_min, y_min, x_max, y_max]
                        if bounds[2] > bounds[0] and bounds[3] > bounds[1]:
                            # 可能是 [x_min, y_min, x_max, y_max]
                            x_min, y_min, x_max, y_max = bounds
                        else:
                            # 可能是 [x, y, w, h]
                            x_min, y_min, w, h = bounds
                            x_max = x_min + w
                            y_max = y_min + h
                        
                        boxes.append([x_min, y_min, x_max, y_max, class_id])
    
    return boxes, class_mapping


def main():
    """
    主函数：读取JSON标注文件，生成分割掩码并保存
    """
    parser = argparse.ArgumentParser(description='将UI标注JSON文件转换为分割掩码')
    parser.add_argument('--json_dir', type=str, required=True,
                        help='包含JSON标注文件的目录')
    parser.add_argument('--image_dir', type=str, required=True,
                        help='图片目录')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='输出掩码文件的目录')
    parser.add_argument('--image_ext', type=str, default='.png',
                        help='图片文件扩展名 (默认: .png)')
    parser.add_argument('--json_ext', type=str, default='.json',
                        help='JSON文件扩展名 (默认: .json)')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 获取所有JSON文件
    json_files = [f for f in os.listdir(args.json_dir) if f.endswith(args.json_ext)]
    
    class_mapping = {}
    total_images = 0
    processed_images = 0
    
    for json_file in json_files:
        json_path = os.path.join(args.json_dir, json_file)
        
        # 获取对应的图片文件名
        image_name = os.path.splitext(json_file)[0] + args.image_ext
        image_path = os.path.join(args.image_dir, image_name)
        
        if not os.path.exists(image_path):
            print(f"警告: 图片文件不存在: {image_path}")
            continue
        
        # 读取图片获取尺寸
        try:
            img = Image.open(image_path)
            width, height = img.size
        except Exception as e:
            print(f"错误: 无法读取图片 {image_path}: {e}")
            continue
        
        # 解析JSON文件
        try:
            boxes, file_class_mapping = parse_rico_json(json_path)
            
            # 更新全局类别映射
            for class_name, class_id in file_class_mapping.items():
                if class_name not in class_mapping:
                    class_mapping[class_name] = len(class_mapping) + 1
            
            # 重新映射类别ID以匹配全局映射
            for box in boxes:
                # 这里需要根据实际JSON格式调整，暂时保持原样
                pass
            
        except Exception as e:
            print(f"错误: 无法解析JSON文件 {json_path}: {e}")
            continue
        
        # 生成掩码
        mask = create_segmentation_mask(width, height, boxes)
        
        # 保存掩码
        mask_name = os.path.splitext(json_file)[0] + '.png'
        mask_path = os.path.join(args.output_dir, mask_name)
        
        mask_image = Image.fromarray(mask, mode='P')
        mask_image.save(mask_path)
        
        processed_images += 1
        total_images += 1
        
        if processed_images % 100 == 0:
            print(f"已处理 {processed_images} 张图片...")
    
    print(f"处理完成! 总共处理了 {processed_images}/{total_images} 张图片")
    print(f"类别映射: {class_mapping}")
    
    # 保存类别映射到文件
    mapping_path = os.path.join(args.output_dir, 'class_mapping.json')
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(class_mapping, f, indent=2, ensure_ascii=False)
    print(f"类别映射已保存到: {mapping_path}")


if __name__ == '__main__':
    main()

