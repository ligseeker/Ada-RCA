# Ada-RCA

Ada-RCA 是一个面向已确认故障事件的服务级根因排序方法。给定固定、合法的候选服务集合，它从指标、日志、Trace Error 和 Trace Latency 四类遥测中构造事件相对特征，再用事件级条件逻辑回归输出完整的候选服务排名。

本仓库是精简后的最终方法实现，保留数据适配与特征提取、模型主体、评测代码、最小复现入口、核心测试，以及验证最终结果所需的冻结输入和参考产物。开发阶段的消融、诊断、一次性审计、外部基线和论文打包代码不在本分支中。

## 方法概述

Ada-RCA 使用 `[t0-600s, t0+600s)` 的半开事件窗口，并将其划分为 80 个 15 秒时间桶（40 个故障前桶、40 个故障后桶）。每个候选服务按固定顺序处理四个遥测通道：

1. Metric
2. Log
3. Trace Error
4. Trace Latency

每个标量指标只用故障前观测进行 median/MAD 归一化；当 MAD 过小时使用 IQR fallback。随后按服务与通道取 Q90 聚合，形成 32 维基础特征和 36 维形态特征，最终得到固定顺序的 68 维 Z2 表示。

模型对每个事件的候选服务联合建模：每个数据集独立进行按重复编号划分的三折 OOF 训练，`StandardScaler` 仅拟合训练折候选行，条件逻辑回归使用 L2 `lambda=1.0`、float64、零初始化、L-BFGS-B 与确定性 Newton polishing。输出必须覆盖全部合法候选服务，并以服务名作为精确分数并列时的确定性次序。

更完整的冻结表示定义见 [`docs/REPRESENTATION_FREEZE.md`](docs/REPRESENTATION_FREEZE.md)。本方法不声称进行故障检测、因果发现或拓扑推理。

## 目录结构

```text
.
├── artifacts/
│   ├── source/                 # 冻结输入、标签侧车和候选服务注册表
│   ├── features/               # 180 个冻结 Z2 特征文件及清单
│   ├── splits/                 # RE2-OB/RE2-TT 的固定三折划分
│   ├── p4_g0/predictions/a2/   # 最终方法身份校验所需的参考预测
│   └── final_method/           # 已提交的模型状态、预测、指标和校验记录
├── docs/
│   ├── REPRESENTATION_FREEZE.md
│   └── REPRODUCIBILITY.md
├── scripts/
│   ├── prepare_dataset.py      # 从原始 RCAEval 目录生成 source bundle
│   ├── create_splits.py        # 生成确定性三折划分
│   ├── extract_features.py     # label-free 特征提取
│   └── run_final_method.py     # 最终 OOF 训练、持久化和身份校验入口
├── src/rca/
│   ├── schema.py               # 输入/标签契约与 label firewall
│   ├── rcaeval.py              # RE2-OB/RE2-TT 适配器
│   ├── features.py             # 四通道事件相对表示
│   ├── p4.py                   # 条件逻辑回归、OOF 训练和排序
│   ├── evaluator.py            # AC@k、Avg@5、MRR
│   ├── p4_stats.py             # 预测聚合与配对统计
│   └── final_method.py         # 冻结 Z2 执行和模型状态重放
└── tests/                      # 核心方法、数据契约和复现测试
```

## 环境与安装

冻结参考环境：

- Python 3.8.20
- NumPy 1.24.1
- pandas 1.5.3
- SciPy 1.10.1
- scikit-learn 1.2.1

在仓库根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

代码使用标准库 `unittest`，无需安装 pytest。

## 快速验证与复现

先运行核心测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

复现 RE2-OB 的最终三折 OOF 训练、模型持久化和参考预测校验：

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/run_final_method.py --dataset re2ob
```

默认输出写入被 Git 忽略的 `artifacts/reproduced/final_method/<dataset>/`，不会覆盖已提交的冻结产物。入口要求启动时工作树为 clean，且目标数据集输出目录尚不存在。

RE2-TT 使用相同命令并将数据集改为 `re2tt`。即使 Python 包版本相同，不同 BLAS/浮点实现也可能在排名完全一致时使最大分数误差略高于严格的 `1e-12` 身份阈值；入口会按冻结规则报错而不会静默放宽阈值。详情见 [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md)。

## 从原始 RCAEval 数据重建输入

原始 RCAEval 数据不随仓库分发。以下命令只用于重建和审计数据准备阶段，并将结果写入 `scratch/`，避免覆盖冻结产物：

```bash
python scripts/prepare_dataset.py \
  --re2ob-root /path/to/RCAEval/RE2-OB \
  --re2tt-root /path/to/RCAEval/RE2/RE2-TT \
  --output-root scratch/source

python scripts/create_splits.py \
  --source-root scratch/source \
  --output-root scratch/splits

python scripts/extract_features.py \
  --source-root scratch/source \
  --output-root scratch/features
```

特征提取入口只读取 `inputs.jsonl` 和 `sources.jsonl`，不读取 `labels.jsonl`。这些 `scratch/` 结果不能直接驱动最终 runner；`run_final_method.py` 刻意绑定仓库中已提交的冻结 source/features/splits，以避免无意改变评测输入。完整的产物角色和校验边界见复现文档。

## 冻结结果与适用边界

已提交产物覆盖每个数据集 90 个案例：

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

这些结果是同一 180-case RE2-OB/RE2-TT 语料上的冻结方法描述性证据和身份复现，不是未触碰的独立确认。支持范围限于固定候选注册表、固定折分及已知 root × 已知 fault 的新 repetition；不支持 unseen-root、unseen-fault、跨系统、因果或 SOTA 声明。
