"""
Module that contains RelValStep class
"""
import weakref
from copy import deepcopy
from core.model.model_base import ModelBase


class RelValStep(ModelBase):

    _ModelBase__schema = {
        # PrepID
        'name': '',
        # Arguments if step is a cmsDriver step
        'arguments': {},
        # Input information if step is list of input files
        'input': {},
    }

    lambda_checks = {

    }

    def __init__(self, json_input=None, parent=None):
        self.parent = None
        if json_input:
            json_input = deepcopy(json_input)
            # Remove -- from argument names
            json_input['arguments'] = {k.lstrip('-'): v for k, v in json_input['arguments'].items()}

        ModelBase.__init__(self, json_input)
        if parent:
            self.parent = weakref.ref(parent)
