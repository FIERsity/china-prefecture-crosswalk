# External boundary acquisition cache

These files are fetched from public GitHub repositories for external display-layer construction only. They are not merged into CTAmap or assigned CNUR IDs.

| Region | Local directory | Upstream | Status |
|---|---|---|---|
| Hong Kong | `hongkong_github_scraper/` | [funglkf/hk-geodata](https://github.com/funglkf/hk-geodata) | MIT-licensed scraper; it fetches Hong Kong Government GeoData API datasets. Direct API access was unavailable in this environment. |
| Hong Kong | `hongkong_github_18districts/` | [Paulkit/HKMap](https://github.com/Paulkit/HKMap), [bmkor/hk_osm_map](https://github.com/bmkor/hk_osm_map) | 18-district GeoJSON/GeoBuf and Hong Kong boundary candidates. Paulkit's repo has no declared license; bmkor's source and license need review before publication. |
| Macau | `macau_github_2017/` | [Macau_Boundary_Line_04282017](https://github.com/justinelliotmeyers/Macau_Boundary_Line_04282017) | 2017 WGS84 Shapefile candidate retained for audit only; upstream repository declares no license. Runtime county display currently uses the already-reviewed external Macau background polygon as one unsplit display region. |
| Taiwan | `taiwan_github_official/` | [official_taiwan_administrative_boundary_shapefile](https://github.com/justinelliotmeyers/official_taiwan_administrative_boundary_shapefile) | RAR archive described as official Taiwan boundaries; `source_license.txt` points to the government source and license. Keep attribution and verify current terms before publication. |
| Taiwan | `taiwan_geoboundaries/` | [wmgeolab/geoBoundaries](https://github.com/wmgeolab/geoBoundaries) | Pinned ADM0/ADM1/ADM2 WGS84 GeoJSON, with source metadata and attribution terms; used only for the external display layer. |

The Taiwan official archive is a source cache; pinned geoBoundaries ADM0/ADM1/ADM2 files are used for the runtime external display layer. The Macau Shapefile remains audit-only. Hong Kong's cached 18-district files are MIT-licensed and used for the county display layer; they are external display regions, not CNUR county entities.
