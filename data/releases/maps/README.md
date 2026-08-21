# CTAmap 县级精度分析包

本目录提供本项目网页地图之外的县级精度分析下载包。它不是官方法定边界数据库，也不是测绘成果；使用前请结合研究问题、原始来源和许可证核对。

## 文件

- `ctamap_county_analysis_2000_2024_t002.zip`：2000—2024 年初县级 GeoJSON，按“年份 × 省份”分片；WGS84 经纬度；几何简化容差为 `0.002°`，坐标保留 5 位小数。
- `ctamap_county_analysis_2000_2024_t002.sha256`：下载校验值。
- `ctamap_county_analysis_manifest.json`（仓库同目录）：未压缩分析包的分片、要素数和构建参数清单。

压缩包内含 `county/`、`manifest.json`、`README.md` 和 `NOTICE.md`。分析包比网页展示版保留更多边界细节，但仍不是原始 Shapefile；需要原始数据时请按 `NOTICE.md` 的 CTAmap 上游地址下载并遵守上游条款。

网页使用的是较小的展示版（县级容差 `0.005°`），分析包不由网页运行时加载。
