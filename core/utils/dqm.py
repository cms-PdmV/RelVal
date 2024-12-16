import json
import os

import numpy as np
import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

base_cert_path = "/eos/user/c/cmsdqm/www/CAF/certification/"

def list_certification_files(cert_type):
    """
    List all the certification files related to a certification type
    in the CMS DQM certification server.

    Args:
        cert_type (str): Certification type. This corresponds to the folder
            name available in the server.

    Returns:
        list[str]: All the JSON certification file names.

    Raises:
        HTTPError: If it is not possible to retrieve the index HTML
            page related to the certification type from the server.
    """
    dqm_cert_url = "https://cms-service-dqmdc.web.cern.ch/CAF/certification"
    url = "%s/%s/" % (dqm_cert_url, cert_type)
    page_content = requests.get(url=url)
    if page_content.status_code != 200:
        raise HTTPError(
            "Unable to retrieve the content related to: %s",
            cert_type,
            response=page_content
        )

    # Parse the HTML and retrieve the file names
    page_content = BeautifulSoup(page_content.text, "lxml").text

    file_names = []
    for file_line in page_content.strip().split("\n"):
        if file_line and ".json" in file_line:
            metadata = file_line.strip().split(" ")
            file_name = metadata[0]
            if file_name.endswith(".json"):
                file_names.append(file_name)

    return file_names

def get_certification_file(path):
    """
    Get a certification file from the CMS DQM certification
    server.

    Args:
        path (str): Path to the certification file on the server.

    Returns:
        dict: Golden JSON file.
    """
    dqm_cert_url = "https://cms-service-dqmdc.web.cern.ch/CAF/certification"
    url = "%s/%s" % (dqm_cert_url, path)
    file = requests.get(url=url)
    if file.status_code != 200:
        raise HTTPError(
            "Unable to retrieve the content related to: %s",
            path,
            response=file
        )

    return file.json()

def get_cert_type(dataset):
    """
    List all the certification files related to a certification type
    in the CMS DQM certification server.

    Args:
        dataset: the dataset name as a string '/PD/GTString/DATA-TIER'.

    Returns:
        str: The type of certification we seek (Collisions, HI, Cosmics 
            or Commisioning).

    """
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

def get_json_list(cert_type,web_fallback):
    """
    List all the certification files related to a certification type
    either stored on CMS DQM EOS either, as a fallback,
    in the CMS DQM certification server.

    Args:
        dataset: the dataset name as a string '/PD/GTString/DATA-TIER'.
        web_fallback: a bool flag enabling looking for the list on CMS DQM server.

    Returns:
        list[str]: All the JSON certification file names.

    """
    
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

        json_list = list_certification_files(cert_type=cert_type)
        json_list = [
            file_name
            for file_name in json_list
            if "Golden" in file_name 
            and "Cert_C" in file_name
            and "era" not in file_name 
        ]

    return json_list

def get_golden_json(dataset):
    """ 
    Output a the golden certification dictionary (json) for a specific datasets. 
    In case of multiple json files available, the one with the highest 
    lumi range is selected. The dictionary maps each run number with a complete list
    of the correspondinig golden lumisections. 

    Args:
       dataset: the dataset name as a string '/PD/GTString/DATA-TIER'

    Returns:
        dict: Golden Run-Lumisection dictionary.

    """

    golden_flat = {}

    cert_type = get_cert_type(dataset)
    cert_path = base_cert_path + cert_type + "/"
    web_fallback = not os.path.isdir(cert_path)

    json_list = get_json_list(cert_type,web_fallback)

    # the larger the better, assuming file naming schema
    # Cert_X_RunStart_RunFinish_Type.json
    run_ranges = [int(c.split("_")[3]) - int(c.split("_")[2]) for c in json_list]
    latest_json = np.array(json_list[np.argmax(run_ranges)]).reshape(1,-1)[0].astype(str)
    best_json = str(latest_json[0])
    if not web_fallback:
        with open(cert_path + "/" + best_json) as js:
            golden = json.load(js)
    else:
        path = "%s/%s" % (cert_type, best_json)
        golden = get_certification_file(path=path)
    
    # golden json with all the lumisections one by one
    for k in golden:
        R = []
        for r in golden[k]:
            R = R + [f for f in range(r[0],r[1]+1)]
        golden_flat[k] = R

    return golden_flat

