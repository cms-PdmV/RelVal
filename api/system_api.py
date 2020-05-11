"""
Module that contains all system APIs
"""
from api.api_base import APIBase
from core.utils.locker import Locker
from core.utils.user_info import UserInfo
from core.database.database import Database


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
