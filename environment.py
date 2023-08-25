"""
This module parses some configuration variables from
the runtime environment to use them in different sections
from this application

Attributes:
    DEVELOPMENT (bool): If True, this indicates if the application should run in
        development mode. By default, the application will start in development mode
        the value is going to be True.
        To disable it and run in production, please set the environment variable "PRODUCTION"
        with a value.
    REMOTE_PATH (str): This is the folder, into AFS or EOS, where RelVal submissions files will
        be stored before to submit a job via ReqMgr2.
    SERVICE_URL (str): RelVal Service access URL. For example, https://cms-pdmv-prod.web.cern.ch/relval
    CMSWEB_URL (str): URL to CMS WEB Services. For example, https://cmsweb.cern.ch
    REMOTE_SSH_USERNAME (str): Username to authenticate to the remote node via SSH
    REMOTE_SSH_PASSWORD (str): Password to authenticate to the remote node via SSH
    MONGO_DB_USERNAME (str): Username to authenticate to MongoDB database
    MONGO_DB_PASSWORD (str): Password to authenticate to MongoDB database
    MONGO_DB_HOST (str): MongoDB database hostname
    MONGO_DB_PORT (int): MongoDB database port
    GRID_USER_CERT (str): Path to Grid Certificate to authenticate to CMS WEB Services
    GRID_USER_KEY (str): Path to Private Key to authenticate to CMS WEB Services
"""
import os
import inspect
import pprint

# Variables retrieved from runtime environment
DEVELOPMENT: bool = not bool(os.getenv("PRODUCTION"))
REMOTE_PATH: str = os.getenv("REMOTE_PATH", "")
SERVICE_URL: str = os.getenv(
    "SERVICE_URL", "https://cms-pdmv-dev.web.cern.ch/relval")
CMSWEB_URL: str = os.getenv("CMSWEB_URL", "")
REMOTE_SSH_USERNAME: str = os.getenv("REMOTE_SSH_USERNAME", "")
REMOTE_SSH_PASSWORD: str = os.getenv("REMOTE_SSH_PASSWORD", "")
MONGO_DB_USERNAME: str = os.getenv("MONGO_DB_USERNAME", "")
MONGO_DB_PASSWORD: str = os.getenv("MONGO_DB_PASSWORD", "")
MONGO_DB_HOST: str = os.getenv("MONGO_DB_HOST", "")
MONGO_DB_PORT: int = int(os.getenv("MONGO_DB_PORT", "27017"))
GRID_USER_CERT: str = os.getenv("GRID_USER_CERT", "")
GRID_USER_KEY: str = os.getenv("GRID_USER_KEY", "")

# Raise an error if they are empty variables
missing_environment_variables: dict[str, str] = dict(
    [
        (k, v)
        for k, v in globals().items()
        if not k.startswith("__")
        and not inspect.ismodule(v)
        and not isinstance(v, bool)
        and not v
    ]
)

if missing_environment_variables:
    msg: str = (
        "There are some environment variables "
        "required to be set before running this application\n"
        "Please set the following values via environment variables\n"
        "For more details, please see the description available into `environment.py` module\n"
        f"{pprint.pformat(list(missing_environment_variables.keys()), indent=4)}"
    )
    raise RuntimeError(msg)
