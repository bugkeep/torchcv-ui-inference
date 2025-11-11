#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
UI数据集类
从 dataset/train/image 加载图片，从 dataset/train/label 加载掩码
"""

import os
import numpy as np
from torch.utils import data

from lib.parallel.data_container import DataContainer
from lib.tools.helper.image_helper import ImageHelper
from lib.tools.helper.file_helper import FileHelper
from lib.tools.util.logger import Logger as Log


class UIDataset(data.Dataset):
    def __init__(self, root_dir, dataset=None, aug_transform=None,
                 img_transform=None, label_transform=None, configer=None):
        self.configer = configer
        self.aug_transform = aug_transform
        self.img_transform = img_transform
        self.label_transform = label_transform
        self.img_list, self.label_list = self.__list_dirs(root_dir, dataset)

    def __len__(self):
        return len(self.img_list)

    def __getitem__(self, index):
        img = ImageHelper.read_image(self.img_list[index],
                                     tool=self.configer.get('data', 'image_tool'),
                                     mode=self.configer.get('data', 'input_mode'))
        img_size = ImageHelper.get_size(img)
        labelmap = ImageHelper.read_image(self.label_list[index],
                                          tool=self.configer.get('data', 'image_tool'), mode='P')
        
        # 如果配置了标签列表，进行编码
        if self.configer.get('data.label_list', default=None):
            labelmap = self._encode_label(labelmap)

        # 如果配置了减少零标签，进行处理
        if self.configer.get('data.reduce_zero_label', default=None):
            labelmap = self._reduce_zero_label(labelmap)

        ori_target = ImageHelper.to_np(labelmap)

        if self.aug_transform is not None:
            img, labelmap = self.aug_transform(img, labelmap=labelmap)

        border_size = ImageHelper.get_size(img)

        if self.img_transform is not None:
            img = self.img_transform(img)

        if self.label_transform is not None:
            labelmap = self.label_transform(labelmap)

        meta = dict(
            ori_img_wh=img_size,
            border_wh=border_size,
            ori_target=ori_target
        )
        return dict(
            img=DataContainer(img, stack=True),
            labelmap=DataContainer(labelmap, stack=True),
            meta=DataContainer(meta, stack=False, cpu_only=True),
        )

    def _reduce_zero_label(self, labelmap):
        """减少零标签：将0标签转换为255（忽略标签），其他标签减1"""
        if not self.configer.get('data', 'reduce_zero_label'):
            return labelmap

        labelmap = np.array(labelmap)
        labelmap[labelmap == 0] = 255
        labelmap = labelmap - 1
        labelmap[labelmap == 254] = 255
        if self.configer.get('data', 'image_tool') == 'pil':
            labelmap = ImageHelper.to_img(labelmap.astype(np.uint8))

        return labelmap

    def _encode_label(self, labelmap):
        """根据label_list将标签映射到连续的类别ID"""
        labelmap = np.array(labelmap)
        shape = labelmap.shape
        encoded_labelmap = np.ones(shape=(shape[0], shape[1]), dtype=np.float32) * 255
        for i in range(len(self.configer.get('data', 'label_list'))):
            class_id = self.configer.get('data', 'label_list')[i]
            encoded_labelmap[labelmap == class_id] = i

        if self.configer.get('data', 'image_tool') == 'pil':
            encoded_labelmap = ImageHelper.to_img(encoded_labelmap.astype(np.uint8))

        return encoded_labelmap

    def __list_dirs(self, root_dir, dataset):
        """
        列出图片和标签文件
        
        Args:
            root_dir: 数据集根目录
            dataset: 数据集分割 ('train', 'val', 'test')
        
        Returns:
            img_list: 图片文件路径列表
            label_list: 标签文件路径列表
        """
        img_list = list()
        label_list = list()
        image_dir = os.path.join(root_dir, dataset, 'image')
        label_dir = os.path.join(root_dir, dataset, 'label')

        if not os.path.exists(image_dir):
            Log.error('Image directory not exists: {}'.format(image_dir))
            return img_list, label_list

        if not os.path.exists(label_dir):
            Log.error('Label directory not exists: {}'.format(label_dir))
            return img_list, label_list

        # 获取所有标签文件
        label_files = FileHelper.list_dir(label_dir)
        
        for label_file in label_files:
            # 获取对应的图片文件名（假设图片和标签文件名相同，只是扩展名不同）
            image_name = os.path.splitext(label_file)[0]
            label_path = os.path.join(label_dir, label_file)
            
            # 尝试查找对应的图片文件（支持多种格式）
            img_path = None
            for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                candidate_path = os.path.join(image_dir, image_name + ext)
                if os.path.exists(candidate_path):
                    img_path = candidate_path
                    break
            
            if img_path is None:
                # 如果找不到，尝试使用ImageHelper的imgpath方法
                img_path = ImageHelper.imgpath(image_dir, image_name)
            
            if img_path is None or not os.path.exists(img_path):
                Log.warn('Image file not found for label: {}'.format(label_path))
                continue

            if not os.path.exists(label_path):
                Log.warn('Label file not exists: {}'.format(label_path))
                continue

            img_list.append(img_path)
            label_list.append(label_path)

        # 如果训练时包含验证集
        if dataset == 'train' and self.configer.get('data', 'include_val', default=False):
            val_image_dir = os.path.join(root_dir, 'val', 'image')
            val_label_dir = os.path.join(root_dir, 'val', 'label')
            
            if os.path.exists(val_image_dir) and os.path.exists(val_label_dir):
                val_label_files = FileHelper.list_dir(val_label_dir)
                
                for label_file in val_label_files:
                    image_name = os.path.splitext(label_file)[0]
                    label_path = os.path.join(val_label_dir, label_file)
                    
                    img_path = None
                    for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                        candidate_path = os.path.join(val_image_dir, image_name + ext)
                        if os.path.exists(candidate_path):
                            img_path = candidate_path
                            break
                    
                    if img_path is None:
                        img_path = ImageHelper.imgpath(val_image_dir, image_name)
                    
                    if img_path is None or not os.path.exists(img_path):
                        continue
                    
                    if not os.path.exists(label_path):
                        continue
                    
                    img_list.append(img_path)
                    label_list.append(label_path)

        Log.info('Found {} images in {} dataset.'.format(len(img_list), dataset))
        return img_list, label_list


if __name__ == "__main__":
    # Test UI dataset loader.
    pass

