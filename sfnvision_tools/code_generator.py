#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
HTML/CSS 代码生成器
根据UI组件列表生成HTML文件
"""

import os
from typing import List, Dict, Tuple


def generate_html_css(components: List[Dict], output_path: str, image_size: Tuple[int, int], 
                     background_image: str = None) -> None:
    """
    生成HTML文件，包含内联CSS
    
    Args:
        components: UI组件列表，每个组件包含：
            - 'type': 组件类型（如 'button', 'text', 'image' 等）
            - 'bbox': (x, y, w, h) 边界框
            - 'class_id': 类别ID（可选）
        output_path: 输出HTML文件路径
        image_size: 原始图片尺寸 (width, height)
        background_image: 背景图片路径（可选）
    """
    width, height = image_size
    
    # HTML 头部
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UI Components</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            position: relative;
            width: {width}px;
            height: {height}px;
            overflow: hidden;
        }}
        
        .container {{
            position: relative;
            width: {width}px;
            height: {height}px;
            {background_style}
        }}
        
        /* 通用组件样式 */
        .component {{
            position: absolute;
            border: 2px solid rgba(255, 0, 0, 0.5);
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: #333;
            background-color: rgba(200, 200, 200, 0.3);
        }}
        
        /* 根据组件类型设置不同的样式 */
        .button {{
            background-color: rgba(0, 123, 255, 0.3);
            border-color: rgba(0, 123, 255, 0.8);
        }}
        
        .text {{
            background-color: rgba(255, 255, 255, 0.5);
            border-color: rgba(100, 100, 100, 0.8);
        }}
        
        .image {{
            background-color: rgba(255, 192, 203, 0.3);
            border-color: rgba(255, 20, 147, 0.8);
        }}
        
        .icon {{
            background-color: rgba(255, 165, 0, 0.3);
            border-color: rgba(255, 140, 0, 0.8);
        }}
        
        .input {{
            background-color: rgba(144, 238, 144, 0.3);
            border-color: rgba(0, 128, 0, 0.8);
        }}
        
        .list {{
            background-color: rgba(138, 43, 226, 0.3);
            border-color: rgba(138, 43, 226, 0.8);
        }}
        
        .card {{
            background-color: rgba(255, 20, 147, 0.3);
            border-color: rgba(199, 21, 133, 0.8);
        }}
        
        .toolbar {{
            background-color: rgba(70, 130, 180, 0.3);
            border-color: rgba(70, 130, 180, 0.8);
        }}
        
        .drawer {{
            background-color: rgba(128, 128, 128, 0.3);
            border-color: rgba(64, 64, 64, 0.8);
        }}
        
        .background {{
            background-color: rgba(240, 240, 240, 0.3);
            border-color: rgba(200, 200, 200, 0.8);
        }}
    </style>
</head>
<body>
    <div class="container">
"""
    
    # 设置背景样式
    if background_image:
        background_style = f'background-image: url("{background_image}"); background-size: cover; background-position: center;'
    else:
        background_style = 'background-color: #f0f0f0;'
    
    html_content = html_content.format(
        width=width,
        height=height,
        background_style=background_style
    )
    
    # 生成组件HTML
    for i, component in enumerate(components):
        component_type = component.get('type', 'component')
        bbox = component.get('bbox', (0, 0, 0, 0))
        x, y, w, h = bbox
        
        # 确保坐标和尺寸在合理范围内
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))
        
        # 将组件类型转换为CSS类名（小写，替换空格为下划线）
        css_class = component_type.lower().replace(' ', '_')
        
        # 生成组件div
        html_content += f"""        <div class="component {css_class}" style="left: {x}px; top: {y}px; width: {w}px; height: {h}px;" title="{component_type} ({x}, {y}, {w}, {h})">
            <span>{component_type}</span>
        </div>
"""
    
    # HTML 尾部
    html_content += """    </div>
</body>
</html>"""
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML file generated: {output_path}")
    print(f"Total components: {len(components)}")

