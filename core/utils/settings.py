"""
Module that contains Settings class
"""
from core.database.database import Database


class Settings:
    """
    Class that acts as a settings getter
    """
    def __init__(self):
        self.database = Database('settings')

    def get_all(self):
        """
        Return all settings documents in the database
        """
        return self.database.query(limit=self.database.get_count())

    def get(self, setting_name):
        """
        Return value of specific setting
        """
        return self.database.get(setting_name).get('value')
