import json
import ndjson
import logging
import urllib.parse
error_log = 'C:/Users/jamlung/Documents/LOINC/LOINC_2.72.21AB_OCL.json/Staging Test/Error Log.txt'
OCL_FILE = 'C:/Users/jamlung/Documents/LOINC/LOINC_2.72.21AB_OCL.json/Staging Test/export.json'
DIFF_FILE = 'C:/Users/jamlung/Documents/LOINC/LOINC_2.72.21AB_OCL.json/Staging Test/diff.json'

with open(OCL_FILE, 'r', encoding="utf-8-sig") as f:
    ocl_data = json.load(f)

errors = []
with open(error_log, 'r', encoding="utf-8-sig") as e:
    for line in e:
        errors.append(line.replace("ERROR: OCL has more than one concept with id ","").replace("\n",'').replace('"',''))
# print(errors)

for row in ocl_data:
    for id in errors:
        if row['id'] == id:
            print(row)
