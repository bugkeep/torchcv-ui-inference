# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import site

block_cipher = None

# 当通过 PyInstaller 调用时，spec 中可能没有 __file__；改用当前工作目录
project_dir = os.path.abspath('.')

# 收集 PyTorch DLL 文件
torch_dlls = []
torch_lib_path = None
# 先检查虚拟环境路径
venv_paths = []
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # 在虚拟环境中
    venv_paths.append(os.path.join(sys.prefix, 'Lib', 'site-packages'))
# 添加系统site-packages路径
venv_paths.extend(site.getsitepackages())
# 添加sys.path中的路径
for path in sys.path:
    if 'site-packages' in path and path not in venv_paths:
        venv_paths.append(path)

for site_pkg in venv_paths:
    torch_path = os.path.join(site_pkg, 'torch', 'lib')
    if os.path.exists(torch_path):
        torch_lib_path = torch_path
        break

if torch_lib_path:
    for dll in ['torch_python.dll', 'torch_cpu.dll', 'c10.dll']:
        dll_path = os.path.join(torch_lib_path, dll)
        if os.path.exists(dll_path):
            torch_dlls.append((dll_path, '.'))

# 收集 Shapely DLL 文件
shapely_dlls = []
for site_pkg in venv_paths:
    shapely_path = os.path.join(site_pkg, 'Shapely', '.libs')
    if os.path.exists(shapely_path):
        try:
            for dll_file in os.listdir(shapely_path):
                if dll_file.endswith('.dll'):
                    shapely_dlls.append((os.path.join(shapely_path, dll_file), '.'))
        except:
            pass

datas = [
    (os.path.join(project_dir, 'configs', 'seg', 'sfnet_res101_ui.conf'), 'configs/seg'),
]

binaries = torch_dlls + shapely_dlls

hiddenimports = [
    'numpy.core._methods', 'numpy.lib.format',
    'PIL._imaging', 'PIL.Image',
    'cv2',
    'torch',
    'torchvision',
    'shapely',
]

a = Analysis(
    [os.path.join(project_dir, 'ui_inference_main.py')],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ui_inference',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用 UPX 压缩，避免 DLL 加载问题
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    argv_emulation=False,
)

