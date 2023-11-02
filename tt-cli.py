import json
import teletekst
import requests
import sys

NOS_URL = "https://teletekst-data.nos.nl/json/{}"
# '{}' is a placeholder for the page ID

page_id = sys.argv[1]
if len(page_id) > 6:
    print("page id too long, must be in format '100' or '100-1'")

r = requests.get(NOS_URL.format(page_id))

rj = r.json()

ttp = teletekst.TeletekstPage(rj)

ttp.printPageContent()