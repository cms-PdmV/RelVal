"""
Module that contains ModelBase class
"""
import json
import logging
import re
import time
from copy import deepcopy
from core.utils.user_info import UserInfo


class ModelBase():
    """
    Base class for all model objects
    Has some convenience methods as well as somewhat smart setter
    Contains a bunch of sanity checks
    """
    __json = {}
    __schema = {}
    __model_name = None
    __logger = logging.getLogger()
    __class_name = None
    __cmssw_regex = 'CMSSW_[0-9]{1,3}_[0-9]{1,3}_[0-9]{1,3}.{0,20}'  # CMSSW_ddd_ddd_ddd[_XXX...]
    __globaltag_regex = '[a-zA-Z0-9_\\-]{0,75}'
    __dataset_regex = '^/[a-zA-Z0-9\\-_]{1,99}/[a-zA-Z0-9\\.\\-_]{1,199}/[A-Z\\-]{1,50}$'
    __ps_regex = '[a-zA-Z0-9_]{1,100}'  # Processing String
    __sample_tag_regex = '[a-zA-Z0-9_\\-]{0,75}'
    default_lambda_checks = {
        'batch_name': lambda batch: ModelBase.matches_regex(batch, '[a-zA-Z0-9]{0,75}'),
        'campaign': lambda campaign: ModelBase.matches_regex(campaign, '[a-zA-Z0-9_\\-]{1,75}'),
        'cmssw_release': lambda cmssw: ModelBase.matches_regex(cmssw, ModelBase.__cmssw_regex),
        'cpu_cores': lambda cpus: 1 <= cpus <= 32,
        'dataset': lambda ds: ModelBase.matches_regex(ds, ModelBase.__dataset_regex),
        'globaltag': lambda gt: ModelBase.matches_regex(gt, ModelBase.__globaltag_regex),
        'label': lambda label: ModelBase.matches_regex(label, '[a-zA-Z0-9]{0,75}'),
        'memory': lambda mem: 0 <= mem <= 64000,
        'processing_string': lambda ps: ModelBase.matches_regex(ps, ModelBase.__ps_regex),
        'relval_set': lambda rs: rs in ('standard', 'upgrade', 'generator'),
        'sample_tag': lambda gt: ModelBase.matches_regex(gt, ModelBase.__sample_tag_regex),
    }
    lambda_checks = {}

    def __init__(self, json_input=None):
        self.__json = {}
        self.logger = ModelBase.__logger
        self.__class_name = self.__class__.__name__

        self.logger.debug('Creating %s object. JSON input present: %s',
                          self.__class_name,
                          'YES' if json_input else 'NO')
        self.__fill_values(json_input)
        self.logger.debug('%s', str(self))

    def __fill_values(self, json_input):
        """
        Copy values from given dictionary to object's json
        Initialize default values from schema if any are missing
        """
        if json_input:
            if ('prepid' in self.__schema or '_id' in self.__schema):
                prepid = json_input.get('prepid')
                if not prepid:
                    raise Exception('PrepID cannot be empty')

                self.set('prepid', prepid)
                # CouchDB legacy, can be removed if CouchDB is not used
                if '_rev' in self.__schema and '_rev' in json_input:
                    self.__json['_rev'] = json_input['_rev']

        else:
            json_input = {}

        ignore_keys = set(['_id', '_rev', 'prepid'])
        keys = set(self.__schema.keys())
        if json_input:
            # Just to show errors if any incorrect keys are passed
            bad_keys = set(json_input.keys()) - keys - ignore_keys
            if bad_keys:
                self.logger.warning('Keys that are not in schema of %s: %s',
                                    self.__class_name,
                                    ', '.join(bad_keys))
                # raise Exception(f'Invalid key "{", ".join(bad_keys)}" for {self.__class_name}')

        for key in keys - ignore_keys:
            if key not in json_input:
                self.__json[key] = deepcopy(self.__schema[key])
            else:
                self.set(key, json_input[key])

    def set(self, attribute, value=None):
        """
        Set attribute of the object
        """
        prepid = self.get_prepid()
        if not prepid:
            prepid = self.__class_name

        if not attribute:
            raise Exception('Attribute name not specified')

        if attribute not in self.__schema:
            raise Exception(f'Attribute {attribute} could not be '
                            f'found in {self.__class_name} schema')

        if not isinstance(value, type(self.__schema[attribute])):
            self.logger.debug('%s of %s is not expected (%s) type (got %s). Will try to cast',
                              attribute,
                              prepid,
                              type(self.__schema[attribute]),
                              type(value))
            value = self.cast_value_to_correct_type(attribute, value)

        if not self.check_attribute(attribute, value):
            self.logger.error('Invalid value "%s" for key "%s" for object %s of type %s',
                              value,
                              attribute,
                              prepid,
                              self.__class_name)
            raise Exception(f'Invalid {attribute} value {value} for {prepid}')

        self.__json[attribute] = value
        if attribute == 'prepid':
            self.__json['_id'] = value

        return self.__json

    def get(self, attribute):
        """
        Get attribute of the object
        """
        if not attribute:
            raise Exception('Attribute name not specified')

        if attribute not in self.__schema:
            raise Exception(f'Attribute {attribute} does not exist in {self.__class_name} schema')

        return self.__json[attribute]

    def get_prepid(self):
        """
        Return prepid or _id if any of it exist
        Return none if it doesn't
        """
        if 'prepid' in self.__json:
            return self.__json['prepid']

        if '_id' in self.__json:
            return self.__json['_id']

        return None

    def check_attribute(self, attribute_name, attribute_value):
        """
        This method must return whether given value of attribute is valid
        or raise exception with error
        First it tries to find exact name match in lambda functions
        Then it checks for lambda function with double underscore prefix which
        indicates that this is a list of values
        """
        if attribute_name in self.lambda_checks:
            return self.lambda_checks.get(attribute_name)(attribute_value)

        if f'__{attribute_name}' in self.lambda_checks and isinstance(attribute_value, list):
            lambda_check = self.lambda_checks.get(f'__{attribute_name}')
            for item in attribute_value:
                if not lambda_check(item):
                    raise Exception(f'Bad {attribute_name} value "{item}"')

        return True

    def cast_value_to_correct_type(self, attribute_name, attribute_value):
        """
        If value is not correct type, try to cast it to
        correct type according to schema
        """
        expected_type = type(self.__schema[attribute_name])
        got_type = type(attribute_value)
        if expected_type == list and got_type == str:
            return [x.strip() for x in attribute_value.split(',') if x.strip()]

        prepid = self.get_prepid()
        expected_type_name = expected_type.__name__
        got_type_name = got_type.__name__
        try:
            return expected_type(attribute_value)
        except Exception as ex:
            self.logger.error(ex)
            raise Exception(f'Object {prepid} attribute {attribute_name} is wrong type. '
                            f'Expected {expected_type_name}, got {got_type_name}. '
                            f'It cannot be automatically casted to correct type')

    @classmethod
    def matches_regex(cls, value, regex):
        """
        Check if given string fully matches given regex
        """
        matcher = re.compile(regex)
        match = matcher.fullmatch(value)
        if match:
            return True

        return False

    def __get_json(self, item):
        """
        Internal method to recursively create dict representations of objects
        """
        if isinstance(item, ModelBase):
            return item.get_json()

        if isinstance(item, list):
            new_list = []
            for element in item:
                new_list.append(self.__get_json(element))

            return new_list

        return item

    def get_json(self):
        """
        Return JSON of the object
        """
        built_json = {}
        for attribute, value in self.__json.items():
            built_json[attribute] = self.__get_json(value)

        return deepcopy(built_json)

    @classmethod
    def schema(cls):
        """
        Return a copy of scema
        """
        return deepcopy(cls.__schema)

    def __str__(self):
        """
        String representation of the object
        """
        object_json = self.get_json()
        if 'history' in object_json:
            del object_json['history']

        return (f'Object ID: {self.get_prepid()}\n'
                f'Type: {self.__class_name}\n'
                f'Dict: {json.dumps(object_json, indent=2, sort_keys=True)}')

    def add_history(self, action, value, user, timestamp=None):
        """
        Add entry to object's history
        If no time is specified, use current time
        """
        if user is None:
            user = UserInfo().get_username()

        history = self.get('history')
        history.append({'action': action,
                        'time': int(timestamp if timestamp else time.time()),
                        'user': user,
                        'value': value})
        self.set('history', history)

    @staticmethod
    def lambda_check(name):
        """
        Return a lambda check from default lambda checks dictionary
        """
        return ModelBase.default_lambda_checks.get(name)
