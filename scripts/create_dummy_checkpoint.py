#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
快速生成与配置文件兼容的占位权重（CPU 可用）
"""

import os
import argparse
import torch

from lib.tools.util.configer import Configer
from lib.tools.util.logger import Logger as Log
from model.seg.model_manager import ModelManager


def main():
    parser = argparse.ArgumentParser(description='Create a dummy checkpoint compatible with config.')
    parser.add_argument('--config', type=str, default='configs/seg/sfnet_res101_ui.conf',
                        help='Path to config file.')
    parser.add_argument('--output', type=str, default='',
                        help='Output checkpoint path (.pth). If empty, use config checkpoints_dir/name.')
    args = parser.parse_args()

    Log.init(log_level='info')

    # 加载配置
    configer = Configer(config_file=args.config)

    # 缺省字段兜底，保证可保存/可加载
    if configer.get('phase', default=None) is None:
        configer.add('phase', 'test')
    else:
        configer.update('phase', 'test')

    if configer.get('gpu', default=None) is None:
        configer.add('gpu', None)

    if configer.get('network', 'gather', default=None) is None:
        configer.add('network.gather', True)
    if configer.get('network', 'resume_strict', default=None) is None:
        configer.add('network.resume_strict', False)
    if configer.get('network', 'resume_continue', default=None) is None:
        configer.add('network.resume_continue', False)
    if configer.get('network', 'resume_val', default=None) is None:
        configer.add('network.resume_val', False)

    # 构建模型（不加载预训练）
    Log.info('Building model from config: {}'.format(args.config))
    model_manager = ModelManager(configer)
    model = model_manager.get_seg_model()

    # 组织保存路径
    if args.output:
        save_path = args.output
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
    else:
        checkpoints_dir_cfg = configer.get('network', 'checkpoints_dir', default='./checkpoints/seg/ui')
        checkpoints_name = configer.get('network', 'checkpoints_name', default='sfnet_res101_ui')
        checkpoints_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), checkpoints_dir_cfg)
        os.makedirs(checkpoints_dir, exist_ok=True)
        save_path = os.path.join(checkpoints_dir, f'{checkpoints_name}_latest.pth')

    # 生成占位权重
    state = {
        'config_dict': configer.to_dict(),
        'state_dict': model.state_dict(),
        'runner_state': {'max_performance': float('-inf'), 'min_val_loss': float('inf')}
    }
    torch.save(state, save_path)
    Log.info(f'Dummy checkpoint saved to: {save_path}')


if __name__ == '__main__':
    main()


