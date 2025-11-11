#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: Donny You (youansheng@gmail.com)
# Repackage some image operations.


import os
import sys
import cv2
import numpy as np
from PIL import Image

from lib.tools.helper.file_helper import FileHelper
from lib.tools.util.logger import Logger as Log


PIL_INTER_DICT = {
    'nearest': Image.NEAREST,
    'linear': Image.BILINEAR,
    'cubic': Image.CUBIC
}

CV2_INTER_DICT = {
    'nearest': cv2.INTER_NEAREST,
    'linear': cv2.INTER_LINEAR,
    'cubic': cv2.INTER_CUBIC
}

IMG_EXTENSIONS = [
    '.jpg', '.JPG', '.jpeg', '.JPEG',
    '.png', '.PNG', '.ppm', '.PPM', '.bmp', '.BMP',
]


class ImageHelper(object):

    @staticmethod
    def read_image(image_path, tool='pil', mode='RGB'):
        if tool == 'pil':
            return ImageHelper.pil_read_image(image_path, mode=mode)
        elif tool == 'cv2':
            return ImageHelper.cv2_read_image(image_path, mode=mode)
        else:
            Log.error('Not support mode {}'.format(mode))
            sys.exit(1)

    @staticmethod
    def cv2_read_image(image_path, mode='RGB'):
        # 处理中文路径：直接使用numpy读取文件内容，然后使用cv2.imdecode解码
        # 这样可以避免cv2.imread对中文路径的兼容性问题
        img_bgr = None
        error_msg = None
        
        # 方法1: 尝试使用cv2.imread（对于非中文路径更快）
        try:
            img_bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if img_bgr is not None:
                # 成功读取，直接返回
                if mode in ['BGR', 'RGB', 'GRAY']:
                    return img_bgr
                elif mode == 'P':
                    return ImageHelper.to_np(Image.open(image_path).convert('P'))
                else:
                    Log.error('Not support mode {}'.format(mode))
                    raise ValueError(f'Not support mode {mode}')
        except Exception as e:
            error_msg = f"cv2.imread failed: {e}"
        
        # 方法2: 如果cv2.imread失败（可能是中文路径问题），使用numpy读取文件内容
        if img_bgr is None:
            try:
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                if len(img_data) == 0:
                    raise ValueError(f"Image file is empty: {image_path}")
                img_np = np.frombuffer(img_data, np.uint8)
                img_bgr = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                if img_bgr is not None:
                    # 成功解码，直接返回
                    if mode in ['BGR', 'RGB', 'GRAY']:
                        return img_bgr
                    elif mode == 'P':
                        return ImageHelper.to_np(Image.open(image_path).convert('P'))
                    else:
                        Log.error('Not support mode {}'.format(mode))
                        raise ValueError(f'Not support mode {mode}')
            except Exception as e:
                error_msg = f"cv2.imdecode failed: {e}"
        
        # 方法3: 如果前两种方法都失败，使用PIL作为备用方案
        if img_bgr is None:
            try:
                Log.warn(f"Failed to read image with cv2 (path may contain non-ASCII characters), trying PIL...")
                # 使用PIL读取并转换为BGR格式的numpy数组
                pil_img = Image.open(image_path).convert('RGB')
                img_bgr = np.array(pil_img)
                # PIL读取的是RGB，需要转换为BGR
                img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_RGB2BGR)
                
                if mode in ['BGR', 'RGB', 'GRAY']:
                    return img_bgr
                elif mode == 'P':
                    return ImageHelper.to_np(pil_img.convert('P'))
                else:
                    Log.error('Not support mode {}'.format(mode))
                    raise ValueError(f'Not support mode {mode}')
            except Exception as e:
                error_msg = f"PIL fallback failed: {e}"
        
        # 如果所有方法都失败，抛出异常
        final_error = f"Failed to read image {image_path}. Previous errors: {error_msg}"
        Log.error(final_error)
        raise IOError(final_error)

    @staticmethod
    def pil_read_image(image_path, mode='RGB'):
        with open(image_path, 'rb') as f:
            img = Image.open(f)
            if mode == 'RGB':
                return img.convert('RGB')

            elif mode == 'P':
                return img.convert('P')

            else:
                Log.error('Not support mode {}'.format(mode))
                sys.exit(1)

    @staticmethod
    def rgb2bgr(img_rgb):
        assert isinstance(img_rgb, np.ndarray)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        return img_bgr

    @staticmethod
    def bgr2rgb(img_bgr):
        assert isinstance(img_bgr, np.ndarray)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return img_rgb

    @staticmethod
    def bgr2gray(img, keepdim=False):
        """Convert a BGR image to grayscale image.

        Args:
            img (ndarray): The input image.
            keepdim (bool): If False (by default), then return the grayscale image
                with 2 dims, otherwise 3 dims.

        Returns:
            ndarray: The converted grayscale image.
        """
        out_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if keepdim:
            out_img = out_img[..., None]
        return out_img

    @staticmethod
    def gray2bgr(img):
        """Convert a grayscale image to BGR image.

        Args:
            img (ndarray or str): The input image.

        Returns:
            ndarray: The converted BGR image.
        """
        img = img[..., None] if img.ndim == 2 else img
        out_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        return out_img

    @staticmethod
    def get_cv2_bgr(img, mode='RGB'):
        if isinstance(img, Image.Image):
            img = ImageHelper.to_np(img)

        if mode == 'RGB':
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img_bgr

        return img

    @staticmethod
    def imshow(win_name, img, time=0):
        if isinstance(img, Image.Image):
            img = ImageHelper.rgb2bgr(ImageHelper.to_np(img))

        cv2.imshow(win_name, img)
        cv2.waitKey(time)

    @staticmethod
    def to_img(arr):
        if isinstance(arr, Image.Image):
            return arr

        if len(arr.shape) == 2:
            mode = 'P'
        else:
            mode = 'RGB'

        return Image.fromarray(arr, mode=mode)

    @staticmethod
    def to_np(img):
        return np.asarray(img)

    @staticmethod
    def get_size(img):
        if img is None:
            Log.error('Image is None.')
            raise ValueError('Image is None')
        
        if isinstance(img, Image.Image):
            return img.size

        elif isinstance(img, np.ndarray):
            if len(img.shape) < 2:
                Log.error(f'Image array has invalid shape: {img.shape}')
                raise ValueError(f'Image array has invalid shape: {img.shape}')
            height, width = img.shape[:2]
            return [width, height]

        else:
            Log.error(f'Image type is invalid: {type(img)}')
            raise TypeError(f'Image type is invalid: {type(img)}, expected PIL.Image or np.ndarray')

    @staticmethod
    def resize(img, target_size, interpolation=None):
        assert isinstance(target_size, (list, tuple))
        assert isinstance(interpolation, str)
        if isinstance(img, Image.Image):
            return img.resize(tuple(target_size), PIL_INTER_DICT[interpolation])

        elif isinstance(img, np.ndarray):
            return cv2.resize(img, tuple(target_size), interpolation=CV2_INTER_DICT[interpolation])

        else:
            Log.error('Image type is invalid.')
            sys.exit(1)

    @staticmethod
    def save(img, save_path):
        FileHelper.make_dirs(save_path, is_file=True)
        if isinstance(img, Image.Image):
            img.save(save_path)

        elif isinstance(img, np.ndarray):
            cv2.imwrite(save_path, img)

        else:
            Log.error('Image type is invalid.')
            sys.exit(1)

    @staticmethod
    def fig2img(fig):
        """
        @brief Convert a Matplotlib figure to a PIL Image in RGBA format and return it
        @param fig a matplotlib figure
        @return a Python Imaging Library ( PIL ) image
        """
        # put the figure pixmap into a numpy array
        buf = ImageHelper.fig2data(fig)
        h, w, d = buf.shape
        return Image.frombytes("RGBA", (w, h), buf.tostring())

    @staticmethod
    def fig2np(fig):
        fig.canvas.draw()
        data = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
        data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        return data

    @staticmethod
    def fig2data(fig):
        """
        @brief Convert a Matplotlib figure to a 4D numpy array with RGBA channels and return it
        @param fig a matplotlib figure
        @return a numpy 3D array of RGBA values
        """
        # draw the renderer
        fig.canvas.draw()

        # Get the RGBA buffer from the figure
        w, h = fig.canvas.get_width_height()
        buf = np.fromstring(fig.canvas.tostring_argb(), dtype=np.uint8)
        buf.shape = (w, h, 4)

        # canvas.tostring_argb give pixmap in ARGB mode. Roll the ALPHA channel to have it in RGBA mode
        buf = np.roll(buf, 3, axis=2)
        return buf.reshape(h, w, 4)

    @staticmethod
    def imfrombytes(content, flag='color'):
        """Read an image from bytes.

        Args:
            content (bytes): Image bytes got from files or other streams.
            flag (str): Same as :func:`imread`.

        Returns:
            ndarray: Loaded image array.
        """
        imread_flags = {
            'color': cv2.IMREAD_COLOR,
            'grayscale': cv2.IMREAD_GRAYSCALE,
            'unchanged': cv2.IMREAD_UNCHANGED
        }
        img_np = np.fromstring(content, np.uint8)
        flag = imread_flags[flag] if isinstance(flag, str) else flag
        img = cv2.imdecode(img_np, flag)
        return img

    @staticmethod
    def is_img(img_name):

        return any(img_name.endswith(extension) for extension in IMG_EXTENSIONS)

    @staticmethod
    def imgpath(data_dir, image_name):
        match_list = [os.path.join(data_dir, '{}{}'.format(image_name, ext)) for ext in IMG_EXTENSIONS
                      if os.path.exists(os.path.join(data_dir, '{}{}'.format(image_name, ext)))]
        return None if len(match_list) != 1 else match_list[0]


if __name__ == "__main__":
    target_size = (368, 368)
    image_path = '/home/donny/Projects/PyTorchCV/val/samples/pose/coco/ski.jpg'
    pil_img = ImageHelper.cv2_read_image(image_path)
    pil_img = ImageHelper.to_img(pil_img)
    cv2_img = ImageHelper.cv2_read_image(image_path)
    ImageHelper.imshow('main', np.array(pil_img) - cv2_img)

    pil_img = ImageHelper.cv2_resize(pil_img, target_size, interpolation=cv2.INTER_CUBIC)
    cv2_img = ImageHelper.cv2_resize(cv2_img, target_size, interpolation=cv2.INTER_CUBIC)
    # cv2_img = ImageHelper.bgr2rgb(cv2_img)
    ImageHelper.imshow('main', np.array(pil_img) - cv2_img)
    ImageHelper.imshow('main', pil_img)
    ImageHelper.imshow('main', cv2_img)

    # resize_pil_img.show()
    print(np.unique(np.array(pil_img) - np.array(cv2_img)))
