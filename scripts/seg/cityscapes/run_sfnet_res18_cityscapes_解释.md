# SFNet Cityscapes 训练脚本详细解释

## 脚本文件：`run_sfnet_res18_cityscapes.sh`

这个脚本用于在 Cityscapes 数据集上训练和测试 SFNet (Semantic Flow Network) 模型，使用 ResNet-18 作为骨干网络。

---

## 脚本结构解析

### 1. 环境检查和初始化 (第 1-11 行)

```bash
#!/usr/bin/env bash
# check the enviroment info
nvidia-smi
PYTHON="python"

WORK_DIR=$(cd $(dirname $0)/../../../;pwd)
export PYTHONPATH=${WORK_DIR}:${PYTHONPATH}
cd ../../
```

**解释：**
- `#!/usr/bin/env bash`: 指定使用 bash 解释器
- `nvidia-smi`: 检查 GPU 状态（显示 GPU 信息）
- `PYTHON="python"`: 设置 Python 命令
- `WORK_DIR`: 获取工作目录（项目根目录）
- `export PYTHONPATH`: 将项目根目录添加到 Python 路径，使得可以导入项目模块
- `cd ../../../`: 切换到项目根目录

---

### 2. 配置变量设置 (第 12-24 行)

```bash
DATA_DIR="/data/donny/Cityscapes"

BACKBONE="deepbase_resnet$2"
MODEL_NAME="res_sfnet"
CHECKPOINTS_NAME="sfnet_res18_cityscapes"$2
PRETRAINED_MODEL="./pretrained_models/3x3resnet18-imagenet.pth"

CONFIG_FILE='configs/seg/cityscapes/sfnet_res18_cityscapes_seg.conf'
MAX_ITERS=50000
LOSS_TYPE="fpndsnohemce_loss2"

LOG_DIR="./log/seg/cityscapes/"
LOG_FILE="${LOG_DIR}${CHECKPOINTS_NAME}.log"
```

**变量说明：**

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `DATA_DIR` | Cityscapes 数据集路径 | `/data/donny/Cityscapes` |
| `BACKBONE` | 骨干网络名称，`$2` 是脚本第二个参数 | `deepbase_resnet18` |
| `MODEL_NAME` | 模型名称 | `res_sfnet` |
| `CHECKPOINTS_NAME` | 检查点文件名称前缀 | `sfnet_res18_cityscapes` |
| `PRETRAINED_MODEL` | 预训练模型路径 | `./pretrained_models/3x3resnet18-imagenet.pth` |
| `CONFIG_FILE` | 配置文件路径 | `configs/seg/cityscapes/sfnet_res18_cityscapes_seg.conf` |
| `MAX_ITERS` | 最大训练迭代次数 | `50000` |
| `LOSS_TYPE` | 损失函数类型 | `fpndsnohemce_loss2` |
| `LOG_DIR` | 日志文件目录 | `./log/seg/cityscapes/` |
| `LOG_FILE` | 日志文件路径 | `./log/seg/cityscapes/sfnet_res18_cityscapes.log` |

**注意：**
- `$2` 是脚本的第二个命令行参数，可以用于指定 ResNet 的版本（如 `18`, `50` 等）
- `LOSS_TYPE="fpndsnohemce_loss2"` 表示使用 FPN DSN OHEM CE Loss，包含多个损失项的组合

---

### 3. 日志目录创建 (第 26-29 行)

```bash
if [[ ! -d ${LOG_DIR} ]]; then
    echo ${LOG_DIR}" not exists!!!"
    mkdir -p ${LOG_DIR}
fi
```

**解释：**
- 检查日志目录是否存在，如果不存在则创建

---

### 4. 分布式训练设置 (第 31-32 行)

```bash
NGPUS=8
DIST_PYTHON="${PYTHON} -u -m torch.distributed.launch --nproc_per_node=${NGPUS}"
```

**解释：**
- `NGPUS=8`: 使用 8 个 GPU 进行分布式训练
- `DIST_PYTHON`: 使用 PyTorch 的分布式启动命令
  - `-u`: 无缓冲输出（unbuffered）
  - `-m torch.distributed.launch`: 使用分布式启动模块
  - `--nproc_per_node=${NGPUS}`: 每个节点使用的进程数（GPU 数）

---

### 5. 训练模式 (第 34-38 行)

```bash
if [[ "$1"x == "train"x ]]; then
  ${DIST_PYTHON} main.py --config_file ${CONFIG_FILE} --phase train --train_batch_size 2 --val_batch_size 1 --workers 1 \
                            --backbone ${BACKBONE} --model_name ${MODEL_NAME} --drop_last y --syncbn y --dist y \
                            --data_dir ${DATA_DIR} --loss_type ${LOSS_TYPE} --max_iters ${MAX_ITERS} \
                            --checkpoints_name ${CHECKPOINTS_NAME} --pretrained ${PRETRAINED_MODEL} 2>&1 | tee ${LOG_FILE}
```

**命令解析：**

这是训练命令，使用分布式训练。下面详细解释每个参数：

#### 基础参数
- `--config_file ${CONFIG_FILE}`: 指定配置文件路径
  - 配置文件包含数据增强、学习率策略、优化器设置等
  
- `--phase train`: 指定训练阶段
  - 可选值：`train`, `test`, `val`

#### 数据相关参数
- `--train_batch_size 2`: 训练时每个 GPU 的批次大小
  - 总批次大小 = 2 × 8 (GPUs) = 16
  - 较小的批次大小可能是因为 Cityscapes 图像较大（1024×2048）
  
- `--val_batch_size 1`: 验证时每个 GPU 的批次大小
  - 验证时使用较小的批次大小以节省内存
  
- `--workers 1`: 数据加载的工作进程数
  - 每个 GPU 使用 1 个数据加载进程
  - 总数据加载进程数 = 1 × 8 = 8

- `--data_dir ${DATA_DIR}`: 数据集根目录路径

- `--drop_last y`: 是否丢弃最后一个不完整的批次
  - `y` = yes，丢弃最后一个批次
  - 这在分布式训练中使用 SyncBN 时很重要，可以避免批次大小不一致的问题

#### 模型相关参数
- `--backbone ${BACKBONE}`: 骨干网络名称
  - 例如：`deepbase_resnet18`
  
- `--model_name ${MODEL_NAME}`: 模型名称
  - `res_sfnet` 对应 `ResSFNet` 类

- `--syncbn y`: 是否使用同步批归一化（Synchronized Batch Normalization）
  - `y` = yes，在分布式训练中同步 BN 统计量
  - 这对于多 GPU 训练很重要，可以提高训练稳定性

- `--dist y`: 是否使用分布式训练
  - `y` = yes，启用分布式训练

- `--checkpoints_name ${CHECKPOINTS_NAME}`: 检查点文件名称
  - 用于保存和加载模型权重

- `--pretrained ${PRETRAINED_MODEL}`: 预训练模型路径
  - 加载 ImageNet 预训练的 ResNet-18 权重
  - 用于初始化骨干网络

#### 训练相关参数
- `--loss_type ${LOSS_TYPE}`: 损失函数类型
  - `fpndsnohemce_loss2` 表示：
    - `ohem_ce_loss`: 主分支的 OHEM 交叉熵损失（权重 1.0）
    - `dsn_ohem_ce_loss`: DSN 分支的 OHEM 交叉熵损失（权重 1.0）
    - `fpn_ohem_ce_loss0`: FPN DSN 分支 0 的 OHEM 交叉熵损失（权重 1.0）
    - `fpn_ohem_ce_loss1`: FPN DSN 分支 1 的 OHEM 交叉熵损失（权重 1.0）
    - `fpn_ce_loss2`: FPN DSN 分支 2 的交叉熵损失（权重 1.0）

- `--max_iters ${MAX_ITERS}`: 最大训练迭代次数
  - `50000` 次迭代

#### 输出重定向
- `2>&1 | tee ${LOG_FILE}`: 将标准输出和错误输出都重定向到日志文件
  - `2>&1`: 将标准错误重定向到标准输出
  - `tee`: 同时输出到终端和文件

---

### 6. 恢复训练模式 (第 40-45 行)

```bash
elif [[ "$1"x == "resume"x ]]; then
  ${DIST_PYTHON} main.py --config_file ${CONFIG_FILE} --phase train --train_batch_size 2 --val_batch_size 1 \
                            --backbone ${BACKBONE} --model_name ${MODEL_NAME} --drop_last y --syncbn y --dist y \
                            --data_dir ${DATA_DIR} --loss_type ${LOSS_TYPE} --max_iters ${MAX_ITERS} \
                            --resume_continue y --resume ./checkpoints/seg/cityscapes/${CHECKPOINTS_NAME}_latest.pth \
                            --checkpoints_name ${CHECKPOINTS_NAME} --pretrained ${PRETRAINED_MODEL}  2>&1 | tee -a ${LOG_FILE}
```

**与训练模式的区别：**

- `--resume_continue y`: 继续训练标志
  - 从检查点恢复训练，包括优化器状态、学习率调度器等
  
- `--resume ./checkpoints/seg/cityscapes/${CHECKPOINTS_NAME}_latest.pth`: 检查点文件路径
  - 加载最新的检查点文件

- `tee -a`: 追加模式写入日志文件（`-a` 表示 append）

---

### 7. 验证模式 (第 47-55 行)

```bash
elif [[ "$1"x == "val"x ]]; then
  ${PYTHON} main.py --config_file ${CONFIG_FILE} --phase test --gpu 0 1 2 3 --gather n \
                       --backbone ${BACKBONE} --model_name ${MODEL_NAME} --checkpoints_name ${CHECKPOINTS_NAME} \
                       --resume ./checkpoints/seg/cityscapes/${CHECKPOINTS_NAME}_latest.pth \
                       --test_dir ${DATA_DIR}/val/image --out_dir val  2>&1 | tee -a ${LOG_FILE}
  cd metric/seg/
  ${PYTHON} seg_evaluator.py --config_file "../../"${CONFIG_FILE} \
   --pred_dir ../../results/seg/cityscapes/${CHECKPOINTS_NAME}/val/label \
                                       --gt_dir ${DATA_DIR}/val/label  2>&1 | tee -a "../../"${LOG_FILE}
```

**命令解析：**

#### 第一部分：模型推理
- `${PYTHON}`: 使用单进程 Python（非分布式）
  
- `--phase test`: 测试阶段
  
- `--gpu 0 1 2 3`: 使用 GPU 0, 1, 2, 3
  - 验证时使用 4 个 GPU 而不是 8 个
  
- `--gather n`: 不收集分布式输出
  - `n` = no，每个 GPU 独立处理
  
- `--test_dir ${DATA_DIR}/val/image`: 测试图像目录
  - Cityscapes 验证集图像路径
  
- `--out_dir val`: 输出目录名称
  - 预测结果保存在 `results/seg/cityscapes/${CHECKPOINTS_NAME}/val/label/`

#### 第二部分：评估指标计算
- `cd metric/seg/`: 切换到评估脚本目录
  
- `seg_evaluator.py`: 语义分割评估脚本
  
- `--config_file`: 配置文件路径
  
- `--pred_dir`: 预测结果目录
  - 模型生成的预测标签图
  
- `--gt_dir`: 真实标签目录
  - Cityscapes 验证集的真实标签
  
- 评估指标包括：mIoU (mean Intersection over Union)、像素准确率等

---

### 8. 测试模式 (第 57-61 行)

```bash
elif [[ "$1"x == "test"x ]]; then
  ${PYTHON} -u main.py --config_file ${CONFIG_FILE} --phase test --gpu 0 --test_batch_size 1 --gather n \
                       --backbone ${BACKBONE} --model_name ${MODEL_NAME} --checkpoints_name ${CHECKPOINTS_NAME} \
                       --resume ./checkpoints/seg/cityscapes/${CHECKPOINTS_NAME}_latest.pth \
                       --test_dir ${DATA_DIR}/test --out_dir test  2>&1 | tee -a ${LOG_FILE}
```

**与验证模式的区别：**

- `--gpu 0`: 只使用单个 GPU（GPU 0）
  
- `--test_batch_size 1`: 测试批次大小为 1
  
- `--test_dir ${DATA_DIR}/test`: 测试集目录
  - Cityscapes 测试集（没有标签）
  
- `--out_dir test`: 输出目录名称
  - 结果保存在 `results/seg/cityscapes/${CHECKPOINTS_NAME}/test/label/`

---

## 使用方法

### 训练模型
```bash
bash run_sfnet_res18_cityscapes.sh train 18
```
- 第一个参数：`train` - 训练模式
- 第二个参数：`18` - ResNet-18 骨干网络

### 恢复训练
```bash
bash run_sfnet_res18_cityscapes.sh resume 18
```

### 验证模型
```bash
bash run_sfnet_res18_cityscapes.sh val 18
```

### 测试模型
```bash
bash run_sfnet_res18_cityscapes.sh test 18
```

---

## 参数总结表

### 训练参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `--config_file` | 配置文件路径 | 包含所有超参数配置 |
| `--phase` | `train` | 训练阶段 |
| `--train_batch_size` | `2` | 每个 GPU 的批次大小 |
| `--val_batch_size` | `1` | 验证批次大小 |
| `--workers` | `1` | 数据加载进程数 |
| `--backbone` | `deepbase_resnet18` | 骨干网络 |
| `--model_name` | `res_sfnet` | 模型名称 |
| `--drop_last` | `y` | 丢弃最后一个批次 |
| `--syncbn` | `y` | 同步批归一化 |
| `--dist` | `y` | 分布式训练 |
| `--data_dir` | 数据集路径 | Cityscapes 数据集 |
| `--loss_type` | `fpndsnohemce_loss2` | 损失函数类型 |
| `--max_iters` | `50000` | 最大迭代次数 |
| `--checkpoints_name` | 检查点名称 | 模型保存名称 |
| `--pretrained` | 预训练模型路径 | ImageNet 预训练权重 |

### 验证/测试参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `--phase` | `test` | 测试阶段 |
| `--gpu` | `0 1 2 3` (val) / `0` (test) | 使用的 GPU |
| `--gather` | `n` | 不收集分布式输出 |
| `--test_dir` | 测试图像目录 | 输入图像路径 |
| `--out_dir` | `val` / `test` | 输出目录名称 |
| `--resume` | 检查点路径 | 模型权重文件 |

---

## 损失函数详解

### `fpndsnohemce_loss2` 损失类型

根据配置文件，这个损失类型包含以下损失项：

```json
"fpndsnohemce_loss2": {
    "ohem_ce_loss": 1.0,           // 主分支 OHEM 交叉熵损失
    "dsn_ohem_ce_loss": 1.0,       // DSN 分支 OHEM 交叉熵损失
    "fpn_ohem_ce_loss0": 1.0,      // FPN DSN 分支 0 OHEM 交叉熵损失
    "fpn_ohem_ce_loss1": 1.0,      // FPN DSN 分支 1 OHEM 交叉熵损失
    "fpn_ce_loss2": 1.0            // FPN DSN 分支 2 交叉熵损失
}
```

**OHEM (Online Hard Example Mining)**:
- 只对困难样本计算损失
- 可以提高模型对困难样本的学习能力
- 参数：`thresh=0.7`, `minkeep=100000`

**多级监督**:
- 主分支：最终输出
- DSN 分支：Stage3 输出的辅助监督
- FPN DSN 分支：三个对齐特征的辅助监督

---

## 配置文件说明

配置文件 `configs/seg/cityscapes/sfnet_res18_cityscapes_seg.conf` 包含：

1. **数据配置**:
   - 类别数：19
   - 输入尺寸：1024×1024 (训练), 2048×1024 (验证)
   - 数据增强：随机缩放、裁剪、翻转

2. **网络配置**:
   - 骨干网络：`deepbase_resnet18`
   - 模型：`res_sfnet`
   - 归一化类型：`batchnorm`

3. **优化器配置**:
   - 优化方法：SGD
   - 学习率：0.01
   - 学习率策略：`lambda_poly` (多项式衰减)
   - 权重衰减：0.0005
   - 动量：0.9

4. **训练配置**:
   - 显示间隔：50 次迭代
   - 保存间隔：1000 次迭代
   - 验证间隔：1000 次迭代
   - 最大迭代次数：50000

---

## 注意事项

1. **数据路径**: 需要修改 `DATA_DIR` 为实际的数据集路径
2. **预训练模型**: 确保预训练模型文件存在
3. **GPU 数量**: 脚本默认使用 8 个 GPU，需要根据实际情况调整
4. **批次大小**: 根据 GPU 内存调整批次大小
5. **日志文件**: 训练日志会保存到 `LOG_FILE` 指定的路径

---

## 总结

这个脚本提供了一个完整的训练流程：
1. **训练**: 使用 8 个 GPU 分布式训练 SFNet 模型
2. **恢复**: 从检查点继续训练
3. **验证**: 在验证集上评估模型性能
4. **测试**: 在测试集上生成预测结果

脚本通过命令行参数灵活控制训练过程，并通过配置文件管理超参数，使得训练过程更加规范和可复现。

