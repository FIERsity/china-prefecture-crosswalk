from requests_html import HTMLSession
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

## Fetch the html file
session = HTMLSession()
response = session.get('https://geodata.gov.hk/gs/geodataQueryAPI-datasets')
# print(response.text)

## Parse the html file
soup = BeautifulSoup(response.text, 'html.parser')
# print(soup.title)

## Format the parsed html file
# strhtm = soup.prettify()

## Find all script content
script_list = soup.find_all('script')

## Get DatasetInfo data to Json object
for script in script_list:
  if 'var g_gsDatasetInfo' in str(script):
    # print(str(script))
    m = re.search(r'var g_gsDatasetInfo = (.+?);', str(script), re.DOTALL)
    open('docs/g_gsDatasetInfo.json', 'w').write(m.group(1))
    g_gsDatasetInfo_json = json.loads(m.group(1))

  if 'var g_hkgsCategoryInfo' in str(script):
    m = re.search(r'var g_hkgsCategoryInfo = (.+?);', str(script), re.DOTALL)
    open('docs/g_hkgsCategoryInfo.json', 'w').write(m.group(1))
    g_hkgsCategoryInfo_json = json.loads(m.group(1))

  if 'var hkgsDataProviderList' in str(script):
    m = re.search(r'var hkgsDataProviderList = (\[.+?\])', str(script), re.DOTALL)
    open('docs/hkgsDataProviderList.json', 'w').write(m.group(1))
    hkgsDataProviderList_json = json.loads(m.group(1))

  if 'var hkgsDataProviderAndDatasetMapping' in str(script):
    m = re.search(r'var hkgsDataProviderAndDatasetMapping = ({.+?})', str(script), re.DOTALL)
    open('docs/hkgsDataProviderAndDatasetMapping.json', 'w').write(m.group(1))
    hkgsDataProviderAndDatasetMapping_json = json.loads(m.group(1))

  if 'var hkgsCategoryList' in str(script):
    m = re.search(r'var hkgsCategoryList = (.+?);', str(script), re.DOTALL)
    open('docs/hkgsCategoryList.json', 'w').write(m.group(1))
    hkgsCategoryList_json = json.loads(m.group(1))


## Changing Json object to DataFrame
df_g_gsDatasetInfo = pd.DataFrame.from_records(g_gsDatasetInfo_json)
df_hkgsDataProviderList = pd.DataFrame.from_records(hkgsDataProviderList_json)
df_hkgsCategoryList= pd.DataFrame.from_records(hkgsCategoryList_json)
# df_hkgsDataProviderAndDatasetMapping = pd.DataFrame.from_records(hkgsDataProviderAndDatasetMapping_json)
# df_g_hkgsCategoryInfo = pd.DataFrame.from_records(g_hkgsCategoryInfo_json)


## Mapping Provider Name
df_maindata = pd.merge(df_g_gsDatasetInfo[['DATASET_UUID','DATASET_NAME_EN','DATASET_NAME_TC','DATA_PROVIDER_ID']],
         df_hkgsDataProviderList[['dpid','nameEN','nameTC']], left_on='DATA_PROVIDER_ID', right_on='dpid').drop(columns=['dpid', 'DATA_PROVIDER_ID'])


## Save Mapping dataset info to Json
open('static/json/simplified_datasetinfo.json', 'w').write(df_maindata.to_json(orient='records'))


## fetch all geojson and save to static folder
df_maindata['link'] = "https://geodata.gov.hk/gs/api/v1.0.0/geoDataQuery?q=%7Bv%3A%221%2E0%2E0%22%2Cid%3A%22" + df_maindata['DATASET_UUID'].astype(str) + "%22%2Clang%3A%22ALL%22%7D"
for index, row in df_maindata[['DATASET_NAME_EN','link']].iterrows():
  print('Downloading: %s (%s) ' % (re.sub('[^\w_-]+', '_', row['DATASET_NAME_EN'])+'.geojson', row.link))
  response = session.get(row.link)
  open('static/json/' + re.sub('[^\w_-]+', '_', row['DATASET_NAME_EN'])+'.geojson', 'w').write(response.text)

df_maindata = df_maindata.drop('link', 1)

## Change as hyperlink
df_maindata['DATASET_UUID'] =  "<a href='https://geojson.tools/?url=https://geodata.gov.hk/gs/api/v1.0.0/geoDataQuery?q=%7Bv%3A%221%2E0%2E0%22%2Cid%3A%22" + df_maindata['DATASET_UUID'].astype(str) + "%22%2Clang%3A%22ALL%22%7D'  target=\"_blank\">" + df_maindata['DATASET_UUID'].astype(str) + "</a>"


## write to index page with datatable
with open('docs/index.html', 'w') as fo:

    fo.write('''
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.css"/>
<script src="https://code.jquery.com/jquery-3.6.0.slim.min.js" integrity="sha256-u7e5khyithlIdTpu22PHhENmPcRdFiHRjhAuHcs05RI=" crossorigin="anonymous"></script>
<script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.js"></script>
 ''')

    df_maindata.to_html(fo,escape=False, table_id='example')

    fo.write('''<script>$(document).ready(function () { $("#example").DataTable();}); </script> ''')
