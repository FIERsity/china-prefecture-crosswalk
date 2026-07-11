# China Prefecture Crosswalk

面向研究者的中国地级行政实体跨期名称对照、平衡面板与行政区划变更事件资料库。

> 当前版本是初始化快照。数据中的 `entity_id` 是稳定研究实体编号，不是官方行政区划代码；`prefecture_master_wide_2000_2024.csv` 是统一口径的研究面板，不是逐年法定行政单位名录。

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

```python
import pandas as pd

names = pd.read_csv("data/raw/entity_name_map_long.csv")
panel = pd.read_csv("data/raw/prefecture_master_wide_2000_2024.csv")

# 查询一个历史名称在指定年份对应的稳定研究实体
result = names.query("name == '普洱市' and start_year <= 2010 <= end_year")
print(result[["entity_id", "name"]])
```

运行不依赖第三方库的基础校验：

```bash
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
- 当前 340 实体表是平衡面板；三沙、中卫、儋州等存在设立前回填，巢湖、莱芜、伊犁地区等存在撤销后保留。
- 审计报告确认 E533400 应代表“迪庆藏族自治州”；现有香格里拉县级沿革误填入地级实体槽位。
- 公开发布前，应补充国务院、民政部或省级政府原始批复链接，并统一批准年、公告年或年末状态的归年规则。
- 本仓库暂不声明数据许可；确定原始数据来源与再分发权利后，再添加 LICENSE 和数据许可说明。

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

