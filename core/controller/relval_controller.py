"""
Module that contains RelValController class
"""
import json
from core.model.relval import RelVal
from core.controller.controller_base import ControllerBase


class RelValController(ControllerBase):

    def __init__(self):
        ControllerBase.__init__(self)
        self.database_name = 'relvals'
        self.model_class = RelVal

    def get_editing_info(self, obj):
        editing_info = super().get_editing_info(obj)
        prepid = obj.get_prepid()
        new = not bool(prepid)
        editing_info['prepid'] = new
        return editing_info
