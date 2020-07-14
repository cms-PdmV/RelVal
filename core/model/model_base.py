"""
Module that contains ModelBase class
"""
import re
from core_lib.pdmv_model.model_base import ModelBase as PdmVModelBase


class ModelBase(PdmVModelBase):
    """
    Base class for all model objects
    Has some convenience methods as well as somewhat smart setter
    Contains a bunch of sanity checks
    """
    __cmssw_regex = 'CMSSW_[0-9]{1,3}_[0-9]{1,3}_[0-9]{1,3}.{0,20}'  # CMSSW_ddd_ddd_ddd[_XXX...]
    __globaltag_regex = '[a-zA-Z0-9_\\-]{0,75}'
    __dataset_regex = '^/[a-zA-Z0-9\\-_]{1,99}/[a-zA-Z0-9\\.\\-_]{1,199}/[A-Z\\-]{1,50}$'
    __ps_regex = '[a-zA-Z0-9_]{1,100}'  # Processing String
    __sample_tag_regex = '[a-zA-Z0-9_\\-]{0,75}'
    default_lambda_checks = {
        'batch_name': lambda batch: ModelBase.matches_regex(batch, '[a-zA-Z0-9_\\-]{0,75}'),
        'campaign': lambda campaign: ModelBase.matches_regex(campaign, '[a-zA-Z0-9_\\-]{1,75}'),
        'cmssw_release': lambda cmssw: ModelBase.matches_regex(cmssw, ModelBase.__cmssw_regex),
        'cpu_cores': lambda cpus: 1 <= cpus <= 32,
        'dataset': lambda ds: ModelBase.matches_regex(ds, ModelBase.__dataset_regex),
        'globaltag': lambda gt: ModelBase.matches_regex(gt, ModelBase.__globaltag_regex),
        'label': lambda label: ModelBase.matches_regex(label, '[a-zA-Z0-9]{0,75}'),
        'memory': lambda mem: 0 <= mem <= 64000,
        'processing_string': lambda ps: ModelBase.matches_regex(ps, ModelBase.__ps_regex),
        'relval_set': lambda rs: rs in ('standard', 'upgrade', 'generator', 'pileup', 'premix'),
        'sample_tag': lambda gt: ModelBase.matches_regex(gt, ModelBase.__sample_tag_regex),
    }
