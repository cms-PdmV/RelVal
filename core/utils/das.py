#!/usr/bin/env python3
import pandas as pd
import subprocess
import itertools
import numpy as np

def get_lumi_ranges(i):
    """
    Having in input a list of lumis this outputs a list of list
    grouping contigous elements in a single rangel-like list.
    E.g.
     > input = [4,5,6,7,8,200,201,202,222]
     > output = [[4, 8], [200, 202], [222, 222]]
    """
    result = []
    for _, b in itertools.groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        result.append([b[0][1],b[-1][1]]) 
    return result

def das_do_command(cmd):
    """
    A simple wrapper for dasgoclient
    """
    out = subprocess.check_output(cmd, shell=True, executable="/bin/bash").decode('utf8')
    return out.split("\n")

def das_file_data(dataset,opt=""):
    """
    Given a dataset create a pandas DataFrame
    with the list of file names and number 
    of events per file
    """
    cmd = "dasgoclient --query='file dataset=%s %s| grep file.name, file.nevents'"%(dataset,opt)
    out = das_do_command(cmd)
    out = [np.array(r.split(" "))[[0,3]] for r in out if len(r) > 0]

    df = pd.DataFrame(out,columns=["file","events"])
    df.events = df.events.values.astype(int)
    
    return df

def das_lumi_data(dataset,opt=""):
    """
    Produces a file by file+lumi+run pandas DataFrame

    Args:
        dataset: the dataset anme '/PD/GTString/DATA-TIER'
    
    Returns:
        A pandas DataFrame having for each row a single file and as columns: 
        - the file name;
        - the lumisections;
    
    """
    cmd = "dasgoclient --query='file,lumi,run dataset=%s %s'"%(dataset,opt)
    
    out = das_do_command(cmd)
    out = [r.split(" ") for r in out if len(r)>0]
    
    df = pd.DataFrame(out,columns=["file","run","lumis"])
    
    return df

def get_events_df(golden,dataset,events):

    """
    Produces a file by file pandas DataFrame

    Args:
        golden: a run by run certification json
        dataset: the dataset anme '/PD/GTString/DATA-TIER'
        events: max number of events (an int).

    Returns:
        A pandas DataFrame having for each row a single file and as columns: 
        - the file name;
        - the lumisections;
        - the run;
        - the number of events.

    """

    lumi_df = das_lumi_data(dataset)
    file_df = das_file_data(dataset)

    df = lumi_df.merge(file_df,on="file",how="inner") # merge file informations with run and lumis
    df["lumis"] = [[int(ff) for ff in f.replace("[","").replace("]","").split(",")] for f in df.lumis.values]
    
    df_rs = []

    for r in golden:
        cut = (df["run"] == r)
        if not any(cut):
            continue

        df_r = df[cut]

        # jumping very low event count runs
        if df_r["events"].sum() < 10000:
            continue

        good_lumis = np.array([len([ll for ll in l if ll in golden[r]]) for l in df_r.lumis])
        n_lumis = np.array([len(l) for l in df_r.lumis])
        df_rs.append(df_r[good_lumis==n_lumis])

    if len(df_rs)==0:
        return pd.DataFrame([])
    elif len(df_rs)==1:
        df = df_rs
    else:
        df = pd.concat(df_rs)

    ## lumi sorting
    df.loc[:,"min_lumi"] = [min(f) for f in df.lumis]
    df.loc[:,"max_lumi"] = [max(f) for f in df.lumis]
    df = df.sort_values(["run","min_lumi","max_lumi"])

    ## events skimming
    df = df[df["events"] <= events] #jump too big files
    df.loc[:,"sum_evs"] = df.loc[:,"events"].cumsum()
    df = df[df["sum_evs"] < events]

    return df
    
def get_run_lumi(df):
    """
    Produces the lumi mask dict starting from a pandas DataFrame

    Args:
        df: a pandas DataFrame having for each row a single file and as columns: 
            - the file name;
            - the lumisections;
            - the run;
            - the number of events.
    Returns:
        A "CMS"-like lumi mask dict mapping:
        - the run number;
        - to the list of good lumisection ranges.

        E.g. {run : [[lumi_1,lumi_2],[lumi_3,lumi_4]]}
    """
    if len(df) == 0:
        return {}

    run_list = np.unique(df.run.values).tolist()
    lumi_list = [get_lumi_ranges(np.sort(np.concatenate(df.loc[df["run"]==r,"lumis"].values).ravel()).tolist()) for r in run_list]
    
    lumi_ranges = dict(zip(run_list,lumi_list))

    return lumi_ranges

def get_lumi_dict(golden,dataset,events):
    """
    Produces a lumi mask for a given datasets, up to envets, using a certification json

    Args:
        golden: a run by run certification json
        dataset: the dataset anme '/PD/GTString/DATA-TIER'
        events: max number of events (an int).

    Returns:
        A "CMS"-like lumi mask dict mapping:
        - the run number;
        - to the list of good lumisection ranges.
        
        E.g. {run : [[lumi_1,lumi_2],[lumi_3,lumi_4]]}
    """

    df = get_events_df(golden,dataset,events)
    lumi = get_run_lumi(df)

    return lumi
    
