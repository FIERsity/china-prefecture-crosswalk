# CTAmap 数据来源与许可说明

本包的县级几何派生自 **CTAmap 1.30（2000—2024）**，来源项目：

- 数据与下载平台：[shengshixian.com](http://www.shengshixian.com)
- GitHub 数据/平台仓库：[ruiduobao/shengshixian.com](https://github.com/ruiduobao/shengshixian.com)
- 地图项目：[ruiduobao/china-divisions-map](https://github.com/ruiduobao/china-divisions-map)

原始 CTAmap Shapefile 约 2.5 GB，不随本仓库重新分发。上游提供多格式、分行政区下载接口；请以其当前页面、数据包和许可声明为准。本项目只对本仓库生成的派生包记录构建参数，不对行政边界的法律效力、完整性或精度作保证。

分析包参数：

- 年份：2000—2024 年初快照（对应 1999—2023 面板年份）
- 层级：县级
- 坐标系：WGS84 / EPSG:4326；2000—2010 年源数据先从 Web Mercator 转换
- 几何处理：Shapely `preserve_topology=True`，Douglas–Peucker 容差 `0.002°`
- 坐标输出：保留 5 位小数

本包仍属于第三方来源内容，不适用本项目 CC BY 4.0 数据许可；不得据此替代官方行政区划或测绘数据。
