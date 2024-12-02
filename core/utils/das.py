#!/usr/bin/env python3
import pandas as pd
import subprocess
import itertools
import numpy as np

def get_lumi_ranges(i):
    result = []
    for _, b in itertools.groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        result.append([b[0][1],b[-1][1]]) 
    return result

def das_do_command(cmd):
    out = subprocess.check_output(cmd, shell=True, executable="/bin/bash").decode('utf8')
    return out.split("\n")

def das_file_site(dataset, site):
    cmd = "dasgoclient --query='file dataset=%s site=%s'"%(dataset,site)
    out = das_do_command(cmd)
    df = pd.DataFrame(out,columns=["file"])

    return df

def das_file_data(dataset,opt=""):
    cmd = "dasgoclient --query='file dataset=%s %s| grep file.name, file.nevents'"%(dataset,opt)
    out = das_do_command(cmd)
    out = [np.array(r.split(" "))[[0,3]] for r in out if len(r) > 0]

    df = pd.DataFrame(out,columns=["file","events"])
    df.events = df.events.values.astype(int)
    
    return df

def das_lumi_data(dataset,opt=""):
    cmd = "dasgoclient --query='file,lumi,run dataset=%s %s'"%(dataset,opt)
    
    out = das_do_command(cmd)
    out = [r.split(" ") for r in out if len(r)>0]
    
    df = pd.DataFrame(out,columns=["file","run","lumis"])
    
    return df

def das_run_events_data(dataset,run,opt=""):
    cmd = "dasgoclient --query='file dataset=%s run=%s %s | sum(file.nevents) '"%(dataset,run,opt)
    out = das_do_command(cmd)[0]

    out = [o for o in out.split(" ") if "sum" not in o]
    out = int([r.split(" ") for r in out if len(r)>0][0][0])

    return out

def das_run_data(dataset,opt=""):
    cmd = "dasgoclient --query='run dataset=%s %s '"%(dataset,opt)
    out = das_do_command(cmd)

    return out

def get_events_df(golden,dataset,events):

    '''
    Given in input:
    - a run by run certification json
    - the dataset name
    - the number of desired events
    this produces a pandas dataframe with a file per row.

    For each row it has: the file name, lumisections, run and number
    of events and the cumulative sum of the events.
    '''

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

    if len(df) == 0:
        return {}

    run_list = np.unique(df.run.values).tolist()
    lumi_list = [get_lumi_ranges(np.sort(np.concatenate(df.loc[df["run"]==r,"lumis"].values).ravel()).tolist()) for r in run_list]
    
    lumi_ranges = dict(zip(run_list,lumi_list))

    return lumi_ranges

def get_lumi_dict(golden,dataset,events):
    
    df = get_events_df(golden,dataset,events)
    lumi = get_run_lumi(df)

    return lumi
    
