from bs4 import BeautifulSoup
import pycurl
from io import BytesIO
import os
import ast
import numpy as np
import json

base_cert_url = "https://cms-service-dqmdc.web.cern.ch/CAF/certification/"
base_cert_path = "/eos/user/c/cmsdqm/www/CAF/certification/"

def get_url_clean(url):
    
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    
    return BeautifulSoup(buffer.getvalue(), "lxml").text

def get_cert_type(dataset):

    year = dataset.split("Run")[1][2:4] # from 20XX to XX
    PD = dataset.split("/")[1]
    cert_type = "Collisions" + str(year)
    if "Cosmics" in dataset:
        cert_type = "Cosmics" + str(year)
    elif "Commisioning" in dataset:
        cert_type = "Commisioning2020"
    elif "HI" in PD:
        cert_type = "Collisions" + str(year) + "HI"
    
    return cert_type

def get_json_list(dataset,cert_type,web_fallback):

    ## if we have access to eos we get from there ...
    if not web_fallback:
        cert_path = base_cert_path + cert_type + "/"
        json_list = os.listdir(cert_path)
        if len(json_list) == 0:
            web_fallback == True
        json_list = [c for c in json_list if "Golden" in c and "era" not in c]
        json_list = [c for c in json_list if c.startswith("Cert_C") and c.endswith("json")]
    ## ... if not we go to the website
    else:
        cert_url = base_cert_url + cert_type + "/"
        json_list = get_url_clean(cert_url).split("\n")
        json_list = [c for c in json_list if "Golden" in c and "era" not in c and "Cert_C" in c]
        json_list = [[cc for cc in c.split(" ") if cc.startswith("Cert_C") and cc.endswith("json")][0] for c in json_list]

    return json_list

def get_golden_json(dataset):
    ''' 
    Get the flattened golden json with highest 
    lumi range based on the dataset name.
    '''

    golden_flat = {}

    cert_type = get_cert_type(dataset)
    cert_path = base_cert_path + cert_type + "/"
    cert_url = base_cert_url + cert_type + "/"
    web_fallback = not os.path.isdir(cert_path)

    json_list = get_json_list(dataset,cert_type,web_fallback)

    # the larger the better, assuming file naming schema
    # Cert_X_RunStart_RunFinish_Type.json
    run_ranges = [int(c.split("_")[3]) - int(c.split("_")[2]) for c in json_list]
    latest_json = np.array(json_list[np.argmax(run_ranges)]).reshape(1,-1)[0].astype(str)
    best_json = str(latest_json[0])
    if not web_fallback:
        with open(cert_path + "/" + best_json) as js:
            golden = json.load(js)
    else:
        golden = get_url_clean(cert_url + best_json)
        golden = ast.literal_eval(golden) #converts string to dict
    
    # golden json with all the lumisections one by one
    for k in golden:
        R = []
        for r in golden[k]:
            R = R + [f for f in range(r[0],r[1]+1)]
        golden_flat[k] = R

    return golden_flat

