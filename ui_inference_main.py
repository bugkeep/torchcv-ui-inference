#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
UI推理主脚本
使用训练好的SFNet模型对UI图片进行分割，并生成HTML代码
"""

import os
import sys
import argparse
import numpy as np
import torch
import cv2
from PIL import Image

# 处理打包场景下的资源路径（PyInstaller）
APP_BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
# 添加项目路径
sys.path.insert(0, APP_BASE_DIR)

from lib.tools.util.configer import Configer
from lib.tools.util.logger import Logger as Log
from lib.tools.helper.image_helper import ImageHelper
from lib.runner.runner_helper import RunnerHelper
from lib.runner.blob_helper import BlobHelper
from lib.tools.helper.dc_helper import DCHelper
from model.seg.model_manager import ModelManager
from data.test.test_data_loader import TestDataLoader
from sfnvision_tools.mask_parser import parse_mask_to_components
from sfnvision_tools.code_generator import generate_html_css


def load_and_preprocess_image(image_path, configer):
    """加载并预处理图片"""
    image_tool = configer.get('data', 'image_tool', default='cv2')
    input_mode = configer.get('data', 'input_mode', default='BGR')
    
    # 读取图片（ImageHelper.read_image已修复中文路径问题，会自动尝试多种方法）
    try:
        # 使用配置的工具读取图片（cv2或pil）
        img_np = ImageHelper.read_image(image_path, tool=image_tool, mode=input_mode)
        # 确保返回的是numpy数组
        if isinstance(img_np, Image.Image):
            img_np = np.array(img_np)
            # 如果input_mode是BGR，需要将RGB转换为BGR
            if input_mode == 'BGR':
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    except Exception as e:
        # 如果读取失败，记录错误并重新抛出
        Log.error(f"Failed to load image from {image_path}: {e}")
        raise
    
    # 获取原始图片尺寸 (width, height)
    height, width = img_np.shape[:2]
    img_size = [width, height]
    
    # 为了显示，创建一个PIL Image（用于后续的可视化）
    # 如果input_mode是BGR，转换为RGB用于显示
    if input_mode == 'BGR':
        img_for_display = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB))
    else:
        img_for_display = Image.fromarray(img_np)
    
    # 预处理为tensor（使用numpy数组，保持BGR格式）
    from lib.data.transforms import ToTensor, Normalize, Compose
    
    img_transform = Compose([
        ToTensor(),
        Normalize(**configer.get('data', 'normalize')),
    ])
    
    # ToTensor可以处理numpy数组，会保持颜色通道顺序（BGR）
    img_tensor = img_transform(img_np)
    
    return img_tensor, img_size, img_for_display


def inference_single_image(model, img_tensor, original_size, device, configer, blob_helper):
    """对单张图片进行推理"""
    model.eval()

    # 将 [C, H, W] 转为 [1, C, H, W] 并移动到设备
    img_bchw = img_tensor.unsqueeze(0).to(device)

    # 构建最简数据字典（模型只使用 'img'）
    data_dict = {'img': img_bchw}
    
    # 推理
    with torch.no_grad():
        output = model(data_dict)
        
        # 处理输出
        if isinstance(output, dict):
            logits = output['out']
        elif isinstance(output, (list, tuple)):
            logits = output[0]['out'] if isinstance(output[0], dict) else output[0]
        else:
            logits = output
        
        # 转换为numpy
        if isinstance(logits, torch.Tensor):
            logits = logits.cpu().numpy()
        
        # 获取预测类别（argmax）
        if len(logits.shape) == 4:  # [batch, classes, height, width]
            logits = logits[0]  # 取第一个batch
        
        # 如果logits是3D [classes, height, width]，需要resize回原始尺寸
        if len(logits.shape) == 3:
            prediction_logits = logits
            # Resize到原始尺寸
            # 直接根据 original_size resize 回原图宽高
            prediction_logits = cv2.resize(
                prediction_logits.transpose(1, 2, 0),
                tuple(original_size),
                interpolation=cv2.INTER_CUBIC
            ).transpose(2, 0, 1)
            prediction = np.argmax(prediction_logits, axis=0)
        else:
            prediction = np.argmax(logits, axis=0)
    
    return prediction


def main():
    parser = argparse.ArgumentParser(description='UI图片分割推理并生成HTML')
    parser.add_argument('--image', type=str, required=True,
                        help='输入图片路径')
    parser.add_argument('--config', type=str, 
                        default='configs/seg/sfnet_res101_ui.conf',
                        help='配置文件路径')
    parser.add_argument('--checkpoint', type=str,
                        default='./checkpoints/seg/ui/sfnet_res101_ui_latest.pth',
                        help='模型检查点路径')
    parser.add_argument('--output', type=str, default='./output',
                        help='输出目录')
    parser.add_argument('--class_names', type=str, nargs='+',
                        default=['button', 'text', 'image', 'icon', 'input', 
                                'list', 'card', 'toolbar', 'drawer', 'background'],
                        help='类别名称列表（不包括背景）')
    parser.add_argument('--gpu', type=int, default=0,
                        help='使用的GPU ID（-1表示使用CPU）')
    
    args = parser.parse_args()
    
    # 规范化可能的相对路径（支持打包目录）
    def resolve_path(p):
        if os.path.isabs(p):
            return p
        cand = os.path.join(os.getcwd(), p)
        if os.path.exists(cand):
            return cand
        return os.path.join(APP_BASE_DIR, p)

    args.config = resolve_path(args.config)
    args.checkpoint = resolve_path(args.checkpoint)
    args.image = resolve_path(args.image)
    args.output = os.path.abspath(args.output)

    # 初始化日志
    Log.init(log_level='info')
    
    # 加载配置 - 处理配置文件路径
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.normpath(config_path)
        # 在打包环境中，优先从 _MEIPASS 目录查找配置文件
        if getattr(sys, 'frozen', False):
            # 单文件模式：配置文件在临时解压目录中
            meipass_path = os.path.join(APP_BASE_DIR, config_path)
            if os.path.exists(meipass_path):
                config_path = meipass_path
            else:
                # 尝试从当前工作目录查找
                cwd_path = os.path.abspath(config_path)
                if os.path.exists(cwd_path):
                    config_path = cwd_path
                else:
                    # 尝试从可执行文件目录查找
                    exe_dir = os.path.dirname(sys.executable)
                    candidate = os.path.normpath(os.path.join(exe_dir, args.config))
                    if os.path.exists(candidate):
                        config_path = candidate
        else:
            # 开发环境：从当前工作目录或项目根目录查找
            if not os.path.isabs(config_path):
                config_path = os.path.abspath(config_path)
    
    if not os.path.exists(config_path):
        Log.error(f"Config file not found: {config_path}")
        Log.error(f"Tried paths: {args.config}, {os.path.abspath(args.config)}, {os.path.join(APP_BASE_DIR, args.config) if getattr(sys, 'frozen', False) else 'N/A'}")
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    configer = Configer(config_file=config_path)
    configer.add('network.resume', args.checkpoint)  # 临时设置，后面会更新为解析后的路径
    # 推理阶段设置为 test，避免模型内根据 phase 访问失败
    _phase = configer.get('phase', default=None)
    if _phase is None:
        configer.add('phase', 'test')
    else:
        configer.update('phase', 'test')
    # 兼容缺失的严格加载开关
    if configer.get('network', 'resume_strict', default=None) is None:
        configer.add('network.resume_strict', False)
    if configer.get('network', 'resume_continue', default=None) is None:
        configer.add('network.resume_continue', False)
    if configer.get('network', 'resume_val', default=None) is None:
        configer.add('network.resume_val', False)
    if configer.get('network', 'gather', default=None) is None:
        configer.add('network.gather', True)
    
    # 设置设备
    if args.gpu >= 0 and torch.cuda.is_available():
        device = torch.device(f'cuda:{args.gpu}')
        torch.cuda.set_device(args.gpu)
    else:
        device = torch.device('cpu')
        # 确保存在 gpu 键且为 None（CPU）
        if configer.get('gpu', default=None) is None:
            configer.add('gpu', None)
        else:
            try:
                configer.update('gpu', None)
            except Exception:
                pass
    
    Log.info(f'Using device: {device}')
    
    # 加载模型
    Log.info('Loading model...')
    model_manager = ModelManager(configer)
    model = model_manager.get_seg_model()
    
    # 加载检查点 - 处理相对路径
    checkpoint_path = args.checkpoint
    if not os.path.isabs(checkpoint_path):
        checkpoint_path = os.path.normpath(checkpoint_path)
        if not os.path.isabs(checkpoint_path):
            checkpoint_path = os.path.abspath(checkpoint_path)
        # 如果还是不存在，尝试从可执行文件目录解析
        if not os.path.exists(checkpoint_path) and getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            candidate = os.path.normpath(os.path.join(exe_dir, args.checkpoint))
            if os.path.exists(candidate):
                checkpoint_path = candidate
    
    if os.path.exists(checkpoint_path):
        Log.info(f'Loading checkpoint from {checkpoint_path}')
        configer.update('network.resume', checkpoint_path)
        model = RunnerHelper.load_net(type('obj', (object,), {'configer': configer})(), model)
        # 如果模型是DataParallel，获取底层模型
        if hasattr(model, 'module'):
            model = model.module
    else:
        Log.warn(f'Checkpoint not found: {checkpoint_path}')
        Log.warn(f'Original path: {args.checkpoint}')
        if getattr(sys, 'frozen', False):
            Log.warn(f'Executable directory: {os.path.dirname(sys.executable)}')
        Log.warn('Using untrained model!')
    
    model = model.to(device)
    model.eval()
    
    # 初始化BlobHelper
    blob_helper = BlobHelper(configer)
    
    # 加载图片 - 处理相对路径和绝对路径
    image_path = args.image
    # 如果是相对路径，先尝试规范化（处理 .. 等）
    if not os.path.isabs(image_path):
        # 规范化路径（解析 .. 和 .）
        image_path = os.path.normpath(image_path)
        # 如果不是绝对路径，尝试从当前工作目录解析
        if not os.path.isabs(image_path):
            # 从当前工作目录解析
            image_path = os.path.abspath(image_path)
        # 如果还是不存在，尝试从可执行文件目录解析（针对打包后的exe）
        if not os.path.exists(image_path) and getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            # 尝试将路径相对于exe目录解析
            candidate = os.path.normpath(os.path.join(exe_dir, args.image))
            if os.path.exists(candidate):
                image_path = candidate
    
    Log.info(f'Loading image: {image_path}')
    if not os.path.exists(image_path):
        Log.error(f'Image not found: {image_path}')
        Log.error(f'Current working directory: {os.getcwd()}')
        Log.error(f'Original path: {args.image}')
        if getattr(sys, 'frozen', False):
            Log.error(f'Executable directory: {os.path.dirname(sys.executable)}')
        return 1
    
    img_tensor, img_size, original_img = load_and_preprocess_image(image_path, configer)
    
    Log.info(f'Image size: {img_size[0]}x{img_size[1]}')
    
    # 推理
    Log.info('Running inference...')
    prediction_mask = inference_single_image(model, img_tensor, img_size, device, configer, blob_helper)
    
    Log.info(f'Prediction mask shape: {prediction_mask.shape}')
    Log.info(f'Unique classes in prediction: {np.unique(prediction_mask)}')
    
    # 确保预测掩码尺寸与原始图片一致
    if prediction_mask.shape[0] != img_size[1] or prediction_mask.shape[1] != img_size[0]:
        Log.info('Resizing prediction mask to original image size...')
        prediction_mask = cv2.resize(
            prediction_mask.astype(np.uint8),
            (img_size[0], img_size[1]),
            interpolation=cv2.INTER_NEAREST
        ).astype(np.int32)
    
    # 解析掩码为组件
    Log.info('Parsing mask to components...')
    components = parse_mask_to_components(prediction_mask, args.class_names)
    Log.info(f'Found {len(components)} components')
    
    # 打印组件信息
    for i, comp in enumerate(components):
        Log.info(f'Component {i+1}: {comp["type"]} at {comp["bbox"]}')
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 保存预测掩码可视化
    mask_vis_path = os.path.join(args.output, 'prediction_mask.png')
    mask_vis = (prediction_mask * 255 / max(1, prediction_mask.max())).astype(np.uint8)
    Image.fromarray(mask_vis).save(mask_vis_path)
    Log.info(f'Saved prediction mask to {mask_vis_path}')
    
    # 生成HTML
    output_html_path = os.path.join(args.output, 'output.html')
    image_name = os.path.basename(image_path)
    
    # 复制图片到输出目录（相对路径）
    output_image_path = os.path.join(args.output, image_name)
    if not os.path.exists(output_image_path):
        import shutil
        shutil.copy2(image_path, output_image_path)
    
    Log.info('Generating HTML...')
    generate_html_css(
        components,
        output_html_path,
        img_size,
        background_image=image_name  # 使用相对路径
    )
    Log.info(f'HTML generated: {output_html_path}')
    
    Log.info('Done!')
    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        # 如果是打包后的可执行文件，等待用户按键以便查看错误
        if getattr(sys, 'frozen', False):
            input("\nPress Enter to exit...")
        sys.exit(1)

