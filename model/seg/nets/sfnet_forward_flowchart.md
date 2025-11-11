# SFNet (ResSFNet) Forward 方法数据流图

## 主要数据流程图

```mermaid
flowchart TD
    Start([输入: data_dict<br/>img, labelmap]) --> ExtractSize[提取目标尺寸<br/>target_size]
    
    ExtractSize --> Stage1[Stage1<br/>conv+bn+relu+maxpool+layer1]
    Stage1 --> Stage2[Stage2: layer2<br/>输出 x1]
    Stage2 --> Stage3[Stage3: layer3<br/>输出 x2]
    Stage3 --> Stage4[Stage4: layer4<br/>输出 x4]
    Stage4 --> Combine[组合特征<br/>x_ = [x1, x2, x3, x4]]
    
    Combine --> AlignHead[AlignHead<br/>特征对齐与融合]
    
    AlignHead --> AlignProcess[PSPModule处理x4<br/>FPN特征对齐x3/x2/x1<br/>特征融合拼接]
    AlignProcess --> AlignOut[输出:<br/>x融合特征, fpn_dsn列表]
    
    AlignOut --> ConvLast[conv_last<br/>3x3 conv + 1x1 conv]
    ConvLast --> Upsample[双线性插值上采样<br/>恢复到target_size]
    Upsample --> OutDict[构建输出字典<br/>out_dict = {out: x}]
    
    OutDict --> CheckPhase{phase == 'test'?}
    CheckPhase -->|是| TestReturn[返回 out_dict]
    CheckPhase -->|否| TrainBranch[训练分支]
    
    TrainBranch --> DSN[DSN分支<br/>处理 x3]
    DSN --> DSNConv[3x3 conv + BN + ReLU<br/>Dropout + 1x1 conv]
    DSNConv --> DSNUpsample[上采样 x_dsn]
    
    TrainBranch --> FPNDSN[FPN DSN分支<br/>处理3个对齐特征]
    FPNDSN --> FPNDSN1[FPN DSN[0]<br/>处理fpn_dsn[0]]
    FPNDSN --> FPNDSN2[FPN DSN[1]<br/>处理fpn_dsn[1]]
    FPNDSN --> FPNDSN3[FPN DSN[2]<br/>处理fpn_dsn[2]]
    
    FPNDSN1 --> FPNDSNConv1[3x3 conv + BN<br/>Dropout + 1x1 conv]
    FPNDSN2 --> FPNDSNConv2[3x3 conv + BN<br/>Dropout + 1x1 conv]
    FPNDSN3 --> FPNDSNConv3[3x3 conv + BN<br/>Dropout + 1x1 conv]
    
    FPNDSNConv1 --> FPNDSNUp1[上采样到target_size]
    FPNDSNConv2 --> FPNDSNUp2[上采样到target_size]
    FPNDSNConv3 --> FPNDSNUp3[上采样到target_size]
    
    DSNUpsample --> BuildLoss[构建损失字典]
    FPNDSNUp1 --> BuildLoss
    FPNDSNUp2 --> BuildLoss
    FPNDSNUp3 --> BuildLoss
    Upsample --> BuildLoss
    
    BuildLoss --> LossTypes[检查并添加损失:<br/>fpn_ce_loss0/1/2<br/>fpn_ohem_ce_loss0/1/2<br/>dsn_ce_loss<br/>dsn_ohem_ce_loss<br/>ce_loss<br/>ohem_ce_loss]
    
    LossTypes --> TrainReturn[返回 out_dict, loss_dict]
    
    style Start fill:#e1f5ff
    style TestReturn fill:#c8e6c9
    style TrainReturn fill:#c8e6c9
    style AlignHead fill:#fff9c4
    style ConvLast fill:#fff9c4
    style DSN fill:#ffccbc
    style FPNDSN fill:#ffccbc
    style CheckPhase fill:#f3e5f5
```

## 详细 AlignHead 内部流程

```mermaid
flowchart LR
    Input[输入: x_ = [x1,x2,x3,x4]] --> PSP[PSPModule处理x4<br/>生成psp_out]
    
    PSP --> F1[初始化 f = psp_out]
    F1 --> Loop[反向循环处理]
    
    Loop --> L1[处理 x3<br/>lateral连接]
    L1 --> A1[AlignModule对齐<br/>x3 与 f]
    A1 --> Add1[残差连接<br/>f = x3 + aligned_f]
    Add1 --> Conv1[3x3 conv处理]
    
    Conv1 --> L2[处理 x2<br/>lateral连接]
    L2 --> A2[AlignModule对齐<br/>x2 与 f]
    A2 --> Add2[残差连接<br/>f = x2 + aligned_f]
    Add2 --> Conv2[3x3 conv处理]
    
    Conv2 --> L3[处理 x1<br/>lateral连接]
    L3 --> A3[AlignModule对齐<br/>x1 与 f]
    A3 --> Add3[残差连接<br/>f = x1 + aligned_f]
    Add3 --> Conv3[3x3 conv处理]
    
    Conv3 --> Reverse[反转特征列表]
    Reverse --> Interpolate[上采样所有特征<br/>到相同尺寸]
    Interpolate --> Concat[拼接所有特征<br/>fusion_out]
    
    Concat --> Output[输出:<br/>fusion_out, out列表]
    
    style PSP fill:#fff9c4
    style A1 fill:#ffccbc
    style A2 fill:#ffccbc
    style A3 fill:#ffccbc
    style Concat fill:#c8e6c9
```

## 数据流详细说明

### 主要流程

1. **特征提取阶段** (Stage1-4)
   - 输入: `data_dict['img']` - 输入图像
   - Stage1: conv1+bn+relu → conv2+bn+relu → conv3+bn+relu → maxpool → layer1 → 输出 x1
   - Stage2: layer2 → 输出 x2
   - Stage3: layer3 → 输出 x3  
   - Stage4: layer4 → 输出 x4
   - 组合: `x_ = [x1, x2, x3, x4]` (特征图尺寸递减，通道数递增)

2. **特征对齐与融合** (AlignHead)
   - 输入: 多尺度特征列表 `x_ = [x1, x2, x3, x4]`
   - PSPModule: 对最深层 x4 进行金字塔池化，生成 psp_out
   - FPN特征对齐: 从深到浅 (x3 → x2 → x1) 依次处理
     - 对每层进行 lateral 连接 (1x1 conv 降维)
     - 使用 AlignModule 将高层特征对齐到低层特征
     - 残差连接: `f = conv_x + aligned_f`
     - 3x3 conv 处理对齐后的特征
   - 特征融合: 将所有层特征上采样到相同尺寸后拼接
   - 输出: 
     - `fusion_out`: 拼接后的融合特征 (4 * fpn_dim 通道)
     - `fpn_dsn`: 对齐后的中间特征列表 [对齐后的x1特征, 对齐后的x2特征, 对齐后的x3特征]

3. **主分支输出**
   - conv_last: 3x3 conv + BN + ReLU → 1x1 conv
   - 输出通道数: `num_classes`
   - 双线性插值上采样到 `target_size` (原始图像尺寸)
   - 构建输出字典: `out_dict = {'out': x}`

4. **辅助监督分支** (仅训练阶段)
   - **DSN 分支**: 
     - 输入: `x_[-2]` 即 x3 (Stage3 的输出)
     - 处理: 3x3 conv + BN + ReLU → Dropout(0.1) → 1x1 conv
     - 输出: `x_dsn` (num_classes 通道)
     - 上采样到 target_size
   
   - **FPN DSN 分支**:
     - 输入: `fpn_dsn` 列表中的3个对齐特征
     - 对每个特征: 3x3 conv + BN + ReLU → Dropout(0.1) → 1x1 conv
     - 输出: 3个分割预测图 (每个 num_classes 通道)
     - 上采样到 target_size

5. **损失构建** (仅训练阶段)
   - 根据 `valid_loss_dict` 配置，可选择添加以下损失:
     - `fpn_ce_loss0/1/2`: FPN DSN 分支的交叉熵损失
     - `fpn_ohem_ce_loss0/1/2`: FPN DSN 分支的 OHEM 交叉熵损失
     - `dsn_ce_loss`: DSN 分支的交叉熵损失
     - `dsn_ohem_ce_loss`: DSN 分支的 OHEM 交叉熵损失
     - `ce_loss`: 主分支的交叉熵损失
     - `ohem_ce_loss`: 主分支的 OHEM 交叉熵损失
   - 返回: `out_dict, loss_dict`

### 关键组件

- **AlignHead**: 实现语义流对齐的 FPN 结构，包含 PSPModule 和多个 AlignModule
- **AlignModule**: 使用可学习流场 (flow field) 对齐特征，实现语义对齐
- **PSPModule**: 金字塔池化模块，提取多尺度上下文信息
- **DSN**: Deep Supervision Network，提供辅助监督信号
- **多损失函数**: 支持标准交叉熵损失和 OHEM (Online Hard Example Mining) 交叉熵损失

### 输入输出规格

**输入:**
- `data_dict['img']`: 输入图像张量 [B, C, H, W]
- `data_dict['labelmap']`: 标签图 [B, H, W] (训练时)

**输出:**
- 测试阶段: `out_dict = {'out': x}` 其中 x 为 [B, num_classes, H, W]
- 训练阶段: `out_dict, loss_dict` 其中 loss_dict 包含配置的损失项

### 网络特点

1. **语义流对齐**: 通过 AlignModule 实现高层语义特征与低层细节特征的对齐
2. **多尺度特征融合**: 融合四个不同尺度的特征图
3. **深度监督**: 使用 DSN 和 FPN DSN 提供多级监督信号
4. **灵活损失配置**: 支持多种损失函数组合，可根据配置选择使用

