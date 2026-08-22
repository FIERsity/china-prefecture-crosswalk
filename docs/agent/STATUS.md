# 项目近况

> 动态快照。最后核验：2026-08-22（Asia/Shanghai）。新 Agent 应用 Git 和 GitHub 实时状态复核本页，发现变化时直接刷新。

## 仓库与发布

| 项目 | 已核验状态 |
|---|---|
| 远程仓库 | [`FIERsity/china-prefecture-crosswalk`](https://github.com/FIERsity/china-prefecture-crosswalk)，公开仓库，默认分支 `main` |
| 本次建档前远程基线 | `66da364`（2026-08-21，网页静态资源 cache-busting） |
| 项目版本 | `4.0.2` |
| 最新 Release | [`v4.0.2`](https://github.com/FIERsity/china-prefecture-crosswalk/releases/tag/v4.0.2)，2026-08-21 发布，含主表、研究包与地图包 |
| 开放 Issues / PR | 0 / 0（2026-08-22 核验） |
| 建档时已核验的 `validate-data` 基线 | [`run 32499754506`](https://github.com/FIERsity/china-prefecture-crosswalk/actions/runs/32499754506)，`66da364`，成功 |
| 建档时已核验的 `deploy-pages` 基线 | [`run 32499754596`](https://github.com/FIERsity/china-prefecture-crosswalk/actions/runs/32499754596)，`66da364`，成功 |
| 线上站点 | <https://fiersity.github.io/china-prefecture-crosswalk/> |

这里记录“文件修订前最后已核验的基线”，而不是声称永远等于文件所在提交。版本化文件无法引用验证自身的 workflow run；每次开始任务和最终交付仍应重新查询远程。

## 当前重点

- 没有开放 Issue 或 PR 指定下一项工作。
- 当前维护重点是让项目事实、远程近况、长期决定和交接方式可被后续 Agent 持续更新。
- 数据、网页或发布发生实质变化后，应由完成该变化的 Agent 同步刷新本页，而不是另建聊天日志。

## 最近完成

- `v4.0.2` 全量覆盖检查补回 10 个此前因句式未覆盖而漏抽的地级升格事件；统一事件增至 167，地级展示事件层增至 234。
- `v4.0.1` 增加 2020 参考年的固定边界单位、历史链接、市辖区事件和 337 城市 × 22 年事件旗标面板。
- 补齐 1989—1991 无同类维基年度页时的日照、潮州、揭阳官方文本事件，并补强事件关系和来源字段。
- 发布 25 年省/地/县地图、港澳台独立外部展示层、研究包和完整网页地图包。
- 修复 Pages 构建链；最近的 `validate-data` 与 `deploy-pages` 均为绿色。
- 网页加入品牌资源、深色模式、主题滑块和静态资源版本参数。

## 已知数据与产品缺口

- V4.0 不声称每条事件都完成官方批复原件级核验；维基、报纸摘要和二次转录仍需按 `verification_status`、`confidence`、`risk_flags` 使用。
- 1983—1986 主要是事件证据层，不是完整年末法定名册；1989—1991 没有同类维基年度变更表。
- 事件查询窗口延伸到 2026，但当前地级事件记录实际终点是 2018；不能把“无记录”表述成“无变更”。
- CTAmap 原始 Shapefile 约 2.5 GB，不在仓库内；重建完整网页地图需要本地原始目录。
- 澳门尚无许可明确、可重发布的细分行政边界，因此当前只显示一个未拆分外部区域。
- 港澳台层是当前展示数据，不具备逐年历史可比性，也不参与 CNUR 或面板匹配。

## 候选后续工作

这些是缺口推导出的候选方向，不代表已经承诺的路线图：

1. 继续用国务院公报扫描件或官方批复原文替换摘要级证据，并保留逐条定位。
2. 对 2019—2026 的地级事件“无新增记录”做来源层面的完整性核验。
3. 若找到许可清晰的澳门细分边界，按独立 external layer 流程评估，不改变 CNUR 范围。
4. 为网页关键查询和地图交互增加可重复的浏览器回归脚本。

## 刷新本页时

- 使用 `git fetch origin --prune`、`git status --short --branch` 和 GitHub 实时查询，不从旧聊天推断。
- 更新绝对日期、版本、Release、开放 Issue/PR，以及文件修订前最后已核验的两个 workflow run。
- “最近完成”保留最有影响的 5—8 项；较旧版本历史交给 `CHANGELOG.md`。
- 已知缺口解决后删除或改写，并在 [`DECISIONS.md`](DECISIONS.md) 追加任何新的长期决定。
- 不记录临时进度、未经验证的 TODO、密钥或个人信息。
