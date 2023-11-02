# -*- coding:utf-8 -*-
import time
from typing import List

import requests
from bs4 import BeautifulSoup as Bs4

stickers: List[str] = []

SPY_FAMILY_URLS = [
    "https://spy-family.net/tvseries/special/special1.php",
    "https://spy-family.net/tvseries/special/special2.php",
    "https://spy-family.net/tvseries/special/special9.php",
    "https://spy-family.net/tvseries/special/special13.php",
    "https://spy-family.net/tvseries/special/special16.php",
    "https://spy-family.net/tvseries/special/special17.php",
]

ICHIGO_PRODUCTION_URL = "https://ichigoproduction.com/special/present_icon.html"

# 載入貼圖(爬蟲)
for url in SPY_FAMILY_URLS:
    response = requests.get(url)
    soup = Bs4(response.text, "html.parser")
    temp = soup.select("ul.icondlLists > li > a > img")

    for i in temp:
        stickers.append("https://spy-family.net/" + i["src"][3:])

    time.sleep(0.05)

response = requests.get(ICHIGO_PRODUCTION_URL)
soup = Bs4(response.text, "html.parser")
temp = soup.select("ul.tp5 > li > div.ph > a")

for i in temp:
    stickers.append("https://ichigoproduction.com/" + i["href"][3:])