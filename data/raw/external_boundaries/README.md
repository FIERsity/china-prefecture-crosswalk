# External boundary acquisition cache

These files are fetched from public GitHub repositories for source evaluation only. They are not currently merged into CTAmap or assigned CNUR IDs.

| Region | Local directory | Upstream | Status |
|---|---|---|---|
| Hong Kong | `hongkong_github_scraper/` | [funglkf/hk-geodata](https://github.com/funglkf/hk-geodata) | MIT-licensed scraper; it fetches Hong Kong Government GeoData API datasets. Direct API access was unavailable in this environment. |
| Hong Kong | `hongkong_github_18districts/` | [Paulkit/HKMap](https://github.com/Paulkit/HKMap), [bmkor/hk_osm_map](https://github.com/bmkor/hk_osm_map) | 18-district GeoJSON/GeoBuf and Hong Kong boundary candidates. Paulkit's repo has no declared license; bmkor's source and license need review before publication. |
| Macau | `macau_github_2017/` | [Macau_Boundary_Line_04282017](https://github.com/justinelliotmeyers/Macau_Boundary_Line_04282017) | 2017 WGS84 Shapefile candidate; upstream repository declares no license, so do not redistribute or publish without permission. |
| Taiwan | `taiwan_github_official/` | [official_taiwan_administrative_boundary_shapefile](https://github.com/justinelliotmeyers/official_taiwan_administrative_boundary_shapefile) | RAR archive described as official Taiwan boundaries; `source_license.txt` points to the government source and license. Keep attribution and verify current terms before publication. |
| Taiwan | `taiwan_geoboundaries/` | [wmgeolab/geoBoundaries](https://github.com/wmgeolab/geoBoundaries) | Current ADM0 WGS84 GeoJSON, CC BY 4.0 / ODbL metadata; used only for the external display layer. |

The Taiwan archive is a source cache, not a runtime dependency. The Macau files are a review-only candidate. A current Taiwan ADM0 GeoJSON from geoBoundaries is additionally cached for the external display layer. Hong Kong data should be fetched from the upstream government API through the retained script after a specific boundary dataset and license are selected; the cached 18-district files are only a display candidate.
