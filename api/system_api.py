"""
Module that contains all system APIs
"""
from core_lib.api.api_base import APIBase
from core_lib.utils.locker import Locker
from core_lib.database.database import Database
from core_lib.utils.user_info import UserInfo
from core.utils.submitter import RequestSubmitter


class SubmissionWorkerStatusAPI(APIBase):
    """
    Endpoint for getting submission workers status
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get status of all request submission workers
        """
        status = RequestSubmitter().get_worker_status()
        return self.output_text({'response': status, 'success': True, 'message': ''})


class SubmissionQueueAPI(APIBase):
    """
    Endpoint for getting names in submission queue
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get status of all request submission workers
        """
        status = RequestSubmitter().get_names_in_queue()
        return self.output_text({'response': status, 'success': True, 'message': ''})


class LockerStatusAPI(APIBase):
    """
    Endpoint for getting status of all locks in the system
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    @APIBase.ensure_role('administrator')
    def get(self):
        """
        Get status of all locks in the system
        """
        status = Locker().get_status()
        status = {k: ('count=0' not in v['l']) for k, v in status.items()}
        return self.output_text({'response': status, 'success': True, 'message': ''})


class UserInfoAPI(APIBase):
    """
    Endpoint for getting user information
    """

    def __init__(self):
        APIBase.__init__(self)

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get status of all locks in the system
        """
        user_info = UserInfo().get_user_info()
        return self.output_text({'response': user_info, 'success': True, 'message': ''})


class ObjectsInfoAPI(APIBase):
    """
    Endpoint for getting database information
    """

    def __init__(self):
        APIBase.__init__(self)

    def get_relvals(self):
        """
        Return summary of RelVals by status and submitted RelVals by CMSSW and batch name
        """
        collection = Database('relvals').collection
        by_status = collection.aggregate([{'$match': {'deleted': {'$ne': True}}},
                                          {'$group': {'_id': '$status',
                                                      'count': {'$sum': 1}}}])

        by_batch = collection.aggregate([{'$match': {'deleted': {'$ne': True}}},
                                         {'$match': {'status': 'submitted'}},
                                         {'$group': {'_id': {'release': '$cmssw_release',
                                                             'batch': '$batch_name'},
                                                     'counts': {'$sum': 1}}},
                                         {'$group': {"_id": "$_id.release",
                                                     "batches": {"$push": {"batch_name": "$_id.batch",
                                                                           "count": "$counts"}}}}])
        statuses = ['new', 'approved', 'submitting', 'submitted', 'done']
        by_status = sorted(list(by_status), key=lambda x: statuses.index(x['_id']))
        by_batch = sorted(list(by_batch), key=lambda x: tuple(x['_id'].split('_')), reverse=True)
        return by_status, by_batch

    def get_tickets(self):
        """
        Return summary of tickets by status and new tickets by CMSSW and batch name
        """
        collection = Database('tickets').collection
        by_status = collection.aggregate([{'$match': {'deleted': {'$ne': True}}},
                                          {'$group': {'_id': '$status',
                                                      'count': {'$sum': 1}}}])

        by_batch = collection.aggregate([{'$match': {'deleted': {'$ne': True}}},
                                         {'$match': {'status': 'new'}},
                                         {'$group': {'_id': {'release': '$cmssw_release',
                                                             'batch': '$batch_name'},
                                                     'counts': {'$sum': 1}}},
                                         {'$group': {"_id": "$_id.release",
                                                     "batches": {"$push": {"batch_name": "$_id.batch",
                                                                           "count": "$counts"}}}}])
        statuses = ['new', 'done']
        by_status = sorted(list(by_status), key=lambda x: statuses.index(x['_id']))
        by_batch = sorted(list(by_batch), key=lambda x: tuple(x['_id'].split('_')), reverse=True)
        return by_status, by_batch

    @APIBase.exceptions_to_errors
    def get(self):
        """
        Get number of RelVals with each status and processing strings of submitted requests
        """
        relvals_by_status, relvals_by_batch = self.get_relvals()
        tickets_by_status, tickets_by_batch = self.get_tickets()
        return self.output_text({'response': {'relvals' : {'by_status': relvals_by_status,
                                                           'by_batch': relvals_by_batch},
                                              'tickets' : {'by_status': tickets_by_status,
                                                           'by_batch': tickets_by_batch}},
                                 'success': True,
                                 'message': ''})