# China Prefecture Crosswalk

面向研究者的中国地级行政实体跨期名称对照、平衡面板与行政区划变更事件资料库。

> `entity_id` 是稳定研究实体编号，不是官方行政区划代码。首版 processed 数据已系统对照 63 条维基百科年度变更事件；未逐条核验的继承记录会明确标为 `inherited_unverified`。

## 推荐使用的数据

| 文件 | 用途 |
|---|---|
| `data/processed/entities.csv` | 340 个稳定研究实体及核验状态 |
| `data/processed/entity_names.csv` | 名称和法定状态的有效年份区间 |
| `data/processed/legal_roster_2000_2024.csv` | 实体—年份长表；区分 active、未设立和已撤销 |
| `data/processed/events_2000_2026.csv` | 63 条地级核心变更事件 |
| `data/processed/event_entity_links.csv` | 事件与稳定研究实体的审计连接表 |
| `data/processed/sources.csv` | 来源注册表 |

字段定义见 [`CODEBOOK.md`](CODEBOOK.md)。`data/raw/` 仅保存原始输入快照，不应直接解释为法定年度名录。

## 数据内容

| 文件 | 规模 | 用途 |
|---|---:|---|
| `data/raw/entity_name_map_long.csv` | 375 行 | 实体名称及有效年份区间（长表） |
| `data/raw/entity_name_map_wide.csv` | 340 行 | 每个实体最多三段历史名称（宽表） |
| `data/raw/prefecture_master_wide_2000_2024.csv` | 340 × 25 年 | 研究用年度平衡面板 |
| `data/raw/china_prefecture_changes_2000_2026_master.xlsx` | 63 个核心事件 | 地级建制变化、年度日志与处理口径 |
| `docs/china_prefecture_entity_mapping_audit_report.pdf` | 6 页 | 数据审计、风险与重构建议 |

三张 CSV 内部结构一致：均覆盖 340 个稳定实体，无完全重复行；长表可用于还原年度名称矩阵。当前关键问题来自历史口径和行政层级混用，而不是表间转换错误。

## 快速开始

### 网页工具

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

网页提供批量检查、单个名称查询和行政区划变更查询。上传文件仅在当前会话内存中处理；OCR、模糊匹配、县级冲突以及合并拆分不会自动接受。

可用 [`examples/sample_panel.csv`](examples/sample_panel.csv) 测试完整流程。

### 部署

推荐使用仓库根目录的 `render.yaml` 在 Render 创建 Blueprint。服务会执行 `streamlit run app.py`，健康检查地址为 `/_stcore/health`。仓库也提供 Dockerfile，可部署到任何支持公开 HTTP 容器的平台。

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/FIERsity/china-prefecture-crosswalk)

### Python 接口

```python
from urban_crosswalk import match_name, match_dataframe

result = match_name("思茅市", year=2005, province="云南省")
print(result.entity_id, result.match_status)
```

批量接口保留原始列并追加 `crosswalk_*` 审计字段：

```python
import pandas as pd
from urban_crosswalk import match_dataframe

data = pd.read_csv("examples/sample_panel.csv")
matched, details = match_dataframe(data, "城市", "年份", "省份")
```

重新生成 processed 数据并运行不依赖第三方库的校验：

```bash
python3 scripts/build_release.py
python3 scripts/validate_data.py
```

## 推荐的小项目

1. **名称标准化与实体解析器**：输入城市历史名称和年份，返回稳定 `entity_id`、有效名称区间与匹配置信度。
2. **面板数据换名工具**：把研究者手中的 `city_name + year` 数据批量连接到稳定实体，并输出未匹配、歧义和越界记录。
3. **行政区划变更时间线**：将 63 条核心事件做成可筛选的省份—年份—事件类型时间线。
4. **法定名录与研究面板双层数据模型**：新增 `legal_roster`、`harmonized_panel` 和多对多关系表，避免把合并/拆分误当作简单改名。
5. **审计规则与回归测试**：优先修正 E533400 等高置信度问题，并为撤销后延续、设立前回填、层级混淆建立自动检测。

最适合先做的是第 2 项：它直接解决城市面板研究中常见的跨年名称连接问题，也能自然暴露当前映射表的边界。

## 重要限制

- `Exxxxxx` 仅为研究用稳定编号，不应解释为任一年度的官方行政区划代码。
- 原始 340 实体表是平衡面板；processed 法定状态层已经修正三沙、中卫等设立前回填以及巢湖、莱芜、伊犁地区等撤销后保留问题。
- `E533400` 已修正为“迪庆藏族自治州”；县级香格里拉沿革不再进入 processed 地级实体表。
- 公开发布前，应补充国务院、民政部或省级政府原始批复链接，并统一批准年、公告年或年末状态的归年规则。
- 维基百科在首版中是明确标注的二手来源；请根据 `verification_status` 判断能否用于高要求研究。

## 许可

代码采用 MIT License；processed 数据采用 CC BY 4.0。第三方来源内容仍受各自条款约束。

## 仓库结构

```text
data/raw/       原始输入快照，不在此目录直接修订
docs/           审计报告与方法文档
scripts/        可复现的数据校验脚本
outputs/        后续生成的数据与报告（默认不提交）
```

## 下一步路线

- 将 Excel 中的核心事件导出为机器可读 CSV。
- 建立 `data/processed/legal_roster.csv` 和 `harmonized_panel.csv`。
- 增加字段字典、来源清单、证据等级和版本变更日志。
- 对 340 个实体逐条补充官方批复级证据。
- 添加 Python/R 使用示例与自动化测试。
