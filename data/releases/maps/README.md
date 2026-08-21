# CTAmap 县级精度分析包

本目录提供两类地图下载包。它们不是官方法定边界数据库，也不是测绘成果；使用前请结合研究问题、原始来源和许可证核对。

## 全部网页地图资源

- `china_prefecture_crosswalk_web_maps_v4.0.zip`：网页运行时使用的完整地图包，包含 2000—2024 年初省级、地级、县级分片、港澳台地图层、`manifest.json` 和地图许可说明。解压后可直接作为 `docs/data/maps/` 使用。
- `china_prefecture_crosswalk_web_maps_v4.0.sha256`：完整网页地图包校验值。

网页地图包中的 `maps/` 目录就是仓库 `docs/data/maps/` 的完整副本：包括省级、地级、县级 25 年分片、港澳台图层、清单和许可说明。CTAmap 地级桥接表不在这个地图包中，而在研究数据包的 `data/ctamap_prefecture_links.csv`；它只是地图要素到 CNUR 的连接关系。

## 文件

- `ctamap_county_analysis_2000_2024_t002.zip`：2000—2024 年初县级 GeoJSON，按“年份 × 省份”分片；WGS84 经纬度；几何简化容差为 `0.002°`，坐标保留 5 位小数。
- `ctamap_county_analysis_2000_2024_t002.sha256`：下载校验值。
- `ctamap_county_analysis_manifest.json`（仓库同目录）：未压缩分析包的分片、要素数和构建参数清单。

压缩包内含 `county/`、`manifest.json`、`README.md` 和 `NOTICE.md`。分析包比网页展示版保留更多边界细节，但仍不是原始 Shapefile；需要原始数据时请按 `NOTICE.md` 的 CTAmap 上游地址下载并遵守上游条款。

网页使用的是展示版（县级容差 `0.005°`）；分析包使用县级容差 `0.002°`，不由网页运行时加载。
