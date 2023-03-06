"""
Main module that starts flask web server
"""
import os
import os.path
import sys
import logging
import logging.handlers
import argparse
from flask_restful import Api
from flask_cors import CORS
from flask import Flask, request, session, render_template
from jinja2.exceptions import TemplateNotFound
from werkzeug.middleware.proxy_fix import ProxyFix
from core_lib.middlewares.auth import AuthenticationMiddleware
from core_lib.database.database import Database
from core_lib.utils.global_config import Config
from core_lib.utils.username_filter import UsernameFilter
from api.system_api import (
    LockerStatusAPI,
    UserInfoAPI,
    SubmissionWorkerStatusAPI,
    SubmissionQueueAPI,
    ObjectsInfoAPI,
    BuildInfoAPI,
    UptimeInfoAPI,
)
from api.search_api import SearchAPI, SuggestionsAPI, WildSearchAPI
from api.ticket_api import (
    CreateTicketAPI,
    DeleteTicketAPI,
    UpdateTicketAPI,
    GetTicketAPI,
    GetEditableTicketAPI,
    CreateRelValsForTicketAPI,
    GetWorkflowsOfCreatedRelValsAPI,
    GetRunTheMatrixOfTicketAPI,
)
from api.relval_api import (
    CreateRelValAPI,
    DeleteRelValAPI,
    UpdateRelValAPI,
    GetRelValAPI,
    GetEditableRelValAPI,
    GetCMSDriverAPI,
    GetConfigUploadAPI,
    GetRelValJobDictAPI,
    GetDefaultRelValStepAPI,
    RelValNextStatus,
    RelValPreviousStatus,
    UpdateRelValWorkflowsAPI,
)
from api.settings_api import SettingsAPI

log_format = "[%(asctime)s][%(levelname)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.DEBUG)

app = Flask(
    __name__,
    static_folder="./vue_frontend/dist/static",
    template_folder="./vue_frontend/dist",
)
app.url_map.strict_slashes = False

# Set flask logging to warning
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Set paramiko logging to warning
logging.getLogger("paramiko").setLevel(logging.WARNING)

# Include API endpoints under the submodule
api = Api(app)
CORS(
    app,
    allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    supports_credentials=True,
)

# Handle redirections from a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# OAuth2 client
# We require some environment variables to configure properly this component
# Instantiate the middleware inside the main function
auth: AuthenticationMiddleware = None
app.before_request(lambda: auth(request=request, session=session))


@app.route("/", defaults={"_path": ""})
@app.route("/<path:_path>")
def catch_all(_path):
    """
    Return index.html for all paths except API
    """
    try:
        return render_template("index.html")
    except TemplateNotFound:
        response = "<script>setTimeout(function() {location.reload();}, 5000);</script>"
        response += "Webpage is starting, please wait a few minutes..."
        return response


@app.route("/api", defaults={"_path": ""})
@app.route("/api/<path:_path>")
def api_documentation(_path):
    """
    Endpoint for API documentation HTML
    """
    docs = {}
    for endpoint, view in app.view_functions.items():
        view_class = dict(view.__dict__).get("view_class")
        if view_class is None:
            continue

        class_name = view_class.__name__
        class_doc = view_class.__doc__.strip()
        # pylint: disable=protected-access
        urls = sorted([r.rule for r in app.url_map._rules_by_endpoint[endpoint]])
        # pylint: enable=protected-access
        category = [x for x in urls[0].split("/") if x][1]
        if category not in docs:
            docs[category] = {}

        docs[category][class_name] = {"doc": class_doc, "urls": urls, "methods": {}}
        for method_name in view_class.methods:
            method = view_class.__dict__.get(method_name.lower())
            method_dict = {"doc": method.__doc__.strip()}
            docs[category][class_name]["methods"][method_name] = method_dict
            if hasattr(method, "__role__"):
                method_dict["role"] = getattr(method, "__role__")

    return render_template("api_documentation.html", docs=docs)


api.add_resource(LockerStatusAPI, "/api/system/locks")
api.add_resource(UserInfoAPI, "/api/system/user_info")
api.add_resource(SubmissionWorkerStatusAPI, "/api/system/workers")
api.add_resource(SubmissionQueueAPI, "/api/system/queue")
api.add_resource(ObjectsInfoAPI, "/api/system/objects_info")
api.add_resource(BuildInfoAPI, "/api/system/build_info")
api.add_resource(UptimeInfoAPI, "/api/system/uptime")

api.add_resource(SettingsAPI, "/api/settings/get", "/api/settings/get/<string:name>")

api.add_resource(SearchAPI, "/api/search")
api.add_resource(SuggestionsAPI, "/api/suggestions")
api.add_resource(WildSearchAPI, "/api/wild_search")

api.add_resource(CreateTicketAPI, "/api/tickets/create")
api.add_resource(DeleteTicketAPI, "/api/tickets/delete")
api.add_resource(UpdateTicketAPI, "/api/tickets/update")
api.add_resource(GetTicketAPI, "/api/tickets/get/<string:prepid>")
api.add_resource(
    GetEditableTicketAPI,
    "/api/tickets/get_editable",
    "/api/tickets/get_editable/<string:prepid>",
)
api.add_resource(CreateRelValsForTicketAPI, "/api/tickets/create_relvals")
api.add_resource(
    GetWorkflowsOfCreatedRelValsAPI, "/api/tickets/relvals_workflows/<string:prepid>"
)
api.add_resource(
    GetRunTheMatrixOfTicketAPI, "/api/tickets/run_the_matrix/<string:prepid>"
)

api.add_resource(CreateRelValAPI, "/api/relvals/create")
api.add_resource(DeleteRelValAPI, "/api/relvals/delete")
api.add_resource(UpdateRelValAPI, "/api/relvals/update")
api.add_resource(GetRelValAPI, "/api/relvals/get/<string:prepid>")
api.add_resource(
    GetEditableRelValAPI,
    "/api/relvals/get_editable",
    "/api/relvals/get_editable/<string:prepid>",
)
api.add_resource(GetCMSDriverAPI, "/api/relvals/get_cmsdriver/<string:prepid>")
api.add_resource(GetConfigUploadAPI, "/api/relvals/get_config_upload/<string:prepid>")
api.add_resource(GetRelValJobDictAPI, "/api/relvals/get_dict/<string:prepid>")
api.add_resource(GetDefaultRelValStepAPI, "/api/relvals/get_default_step")
api.add_resource(RelValNextStatus, "/api/relvals/next_status")
api.add_resource(RelValPreviousStatus, "/api/relvals/previous_status")
api.add_resource(UpdateRelValWorkflowsAPI, "/api/relvals/update_workflows")


def setup_logging(debug):
    """
    Setup logging format and place - console for debug mode and rotating files for production
    """
    logger = logging.getLogger()
    logger.propagate = False
    if debug:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
    else:
        if not os.path.isdir("logs"):
            os.mkdir("logs")

        handler = logging.handlers.RotatingFileHandler(
            "logs/relval.log", "a", 8 * 1024 * 1024, 50
        )
        handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="[%(asctime)s][%(user)s][%(levelname)s] %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(UsernameFilter())
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


def set_app(config_path: str = "config.cfg", mode: str = "dev", debug: bool = True) -> tuple[str, int, bool]:
    """
    Set Flask appplication configuration via config.cfg file
    
    Parameters
    ----------
    config_path : str
        Path to config.cfg file with all environment variables
    mode: str
        Web server deployment mode: dev or prod
    debug: bool
        Set DEBUG logging level

    Returns
    ----------
    tuple[str, int, bool]
        Host name, port number, debug mode configurations for deployment server
    """
    # Instantiate the middleware here
    # Configure cookie security settings for the Flask application
    global auth, app
    
    logger = setup_logging(debug)
    logger.info(f"Setting up Flask application in mode: {mode}")
    logger.info(f"Configuration file path: {config_path}")
    
    config = Config.load(config_path, mode)
    database_auth = config.get("database_auth")

    # Include the application secret key used to sign cookiess
    app.secret_key = config.get("secret_key")

    # Include the middleware
    logger.info(f"Creating authetication middleware")
    auth = AuthenticationMiddleware(
        app=app,
        client_id=config.get("oidc_client_id"),
        client_secret=config.get("oidc_client_secret"),
        home_endpoint="catch_all",
        valid_audiences=config.get("valid_audiences"),
    )
    logger.info(f"Authentication middleware: {auth}")

    Database.set_database_name("relval")
    if database_auth:
        Database.set_credentials_file(database_auth)

    Database.add_search_rename("tickets", "created_on", "history.0.time")
    Database.add_search_rename("tickets", "created_by", "history.0.user")
    Database.add_search_rename("tickets", "workflows", "workflow_ids<float>")
    Database.add_search_rename("relvals", "created_on", "history.0.time")
    Database.add_search_rename("relvals", "created_by", "history.0.user")
    Database.add_search_rename("relvals", "workflows", "workflows.name")
    Database.add_search_rename("relvals", "workflow", "workflows.name")
    Database.add_search_rename("relvals", "output_dataset", "output_datasets")

    # Deployment server configuration
    port: int = int(config.get("port", 8005))
    host: str = config.get("host", "0.0.0.0")
    logger.info(f"Deployment host: {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    return host, port, debug


def main():
    """
    Main function: start Flask web server
    """
    parser = argparse.ArgumentParser(description="RelVal Machine")
    parser.add_argument(
        "--mode",
        help="Use production (prod) or development (dev) section of config",
        choices=["prod", "dev"],
        required=True,
    )
    parser.add_argument(
        "--config", default="config.cfg", help="Specify non standard config file name"
    )
    parser.add_argument("--debug", help="Run Flask in debug mode", action="store_true")
    args = vars(parser.parse_args())
    debug = args.get("debug", False)

    # Set Flask app configurations
    host, port, debug = set_app(
        config_path=args.get("config"),
        mode=args.get("mode"),
        debug=debug,
    )

    logger = logging.getLogger()
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # Do only once, before the reloader
        pid = os.getpid()
        logger.info("PID: %s", pid)
        with open("relval.pid", "w") as pid_file:
            pid_file.write(str(pid))

    logger.info("Starting... Debug: %s, Host: %s, Port: %s", debug, host, port)
    app.run(host=host, port=port, threaded=True, debug=debug)


if __name__ == "__main__":
    main()
