#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
SFNVision Tools
UI分割和代码生成工具
"""

from .mask_parser import parse_mask_to_components
from .code_generator import generate_html_css

__all__ = ['parse_mask_to_components', 'generate_html_css']

