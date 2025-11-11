#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
掩码解析器
将分割掩码转换为UI组件列表
"""

import numpy as np
import cv2
from skimage import measure
from typing import List, Dict, Tuple


def parse_mask_to_components(prediction_mask: np.ndarray, class_names: List[str]) -> List[Dict]:
    """
    将预测掩码转换为UI组件列表
    
    Args:
        prediction_mask: 模型的预测输出，形状为 (height, width) 的 NumPy 数组，值为类别 ID
        class_names: 类别名称列表，索引对应类别 ID（不包括背景，背景通常是0）
    
    Returns:
        组件字典列表，每个字典包含：
        - 'type': 组件类型（类别名称）
        - 'bbox': (x, y, w, h) 边界框
        - 'class_id': 类别ID
    """
    components = []
    height, width = prediction_mask.shape
    
    # 获取所有唯一的类别ID（排除背景0）
    unique_classes = np.unique(prediction_mask)
    unique_classes = unique_classes[unique_classes > 0]  # 排除背景
    
    for class_id in unique_classes:
        # 创建当前类别的二值掩码
        class_mask = (prediction_mask == class_id).astype(np.uint8)
        
        # 使用连通域分析找到所有该类别的区域
        # 使用 OpenCV 的 connectedComponentsWithStats
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            class_mask, connectivity=8
        )
        
        # 遍历每个连通域（跳过背景标签0）
        for label_id in range(1, num_labels):
            # 获取边界框信息
            x = int(stats[label_id, cv2.CC_STAT_LEFT])
            y = int(stats[label_id, cv2.CC_STAT_TOP])
            w = int(stats[label_id, cv2.CC_STAT_WIDTH])
            h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
            
            # 过滤掉太小的区域（可能是噪声）
            if w < 5 or h < 5:
                continue
            
            # 获取类别名称
            class_idx = int(class_id) - 1  # 假设类别ID从1开始
            if 0 <= class_idx < len(class_names):
                component_type = class_names[class_idx]
            else:
                component_type = f'class_{class_id}'
            
            # 添加组件
            components.append({
                'type': component_type,
                'bbox': (x, y, w, h),
                'class_id': int(class_id)
            })
    
    return components


def parse_mask_to_components_skimage(prediction_mask: np.ndarray, class_names: List[str]) -> List[Dict]:
    """
    使用 scikit-image 进行连通域分析的替代实现
    
    Args:
        prediction_mask: 模型的预测输出，形状为 (height, width) 的 NumPy 数组
        class_names: 类别名称列表
    
    Returns:
        组件字典列表
    """
    components = []
    
    # 获取所有唯一的类别ID（排除背景0）
    unique_classes = np.unique(prediction_mask)
    unique_classes = unique_classes[unique_classes > 0]  # 排除背景
    
    for class_id in unique_classes:
        # 创建当前类别的二值掩码
        class_mask = (prediction_mask == class_id).astype(np.uint8)
        
        # 使用 scikit-image 的 label 和 regionprops
        labeled_mask = measure.label(class_mask, connectivity=2)
        regions = measure.regionprops(labeled_mask)
        
        for region in regions:
            # 获取边界框 (min_row, min_col, max_row, max_col)
            min_row, min_col, max_row, max_col = region.bbox
            
            x = int(min_col)
            y = int(min_row)
            w = int(max_col - min_col)
            h = int(max_row - min_row)
            
            # 过滤掉太小的区域
            if w < 5 or h < 5:
                continue
            
            # 获取类别名称
            class_idx = int(class_id) - 1
            if 0 <= class_idx < len(class_names):
                component_type = class_names[class_idx]
            else:
                component_type = f'class_{class_id}'
            
            # 添加组件
            components.append({
                'type': component_type,
                'bbox': (x, y, w, h),
                'class_id': int(class_id)
            })
    
    return components

