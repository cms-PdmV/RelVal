"""
Main module that starts flask web server
"""
import os
import os.path
import sys
import pathlib
import datetime
import logging
import logging.handlers
from flask_restful import Api
from flask_cors import CORS
from flask import Flask, render_template, request, session
from jinja2.exceptions import TemplateNotFound
import environment
from core_lib.database.database import Database
from core_lib.utils.username_filter import UsernameFilter
from core_lib.middlewares.auth import AuthenticationMiddleware
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
# Set flask logging to warning
logging.getLogger("werkzeug").setLevel(logging.WARNING)
# Set paramiko logging to warning
logging.getLogger("paramiko").setLevel(logging.WARNING)

app.url_map.strict_slashes = False
api = Api(app)
CORS(
    app,
    allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    supports_credentials=True,
)

# Include OIDC middleware
app.secret_key = environment.SECRET_KEY
auth: AuthenticationMiddleware = AuthenticationMiddleware(app=app)
app.before_request(lambda: auth.authenticate(request=request, flask_session=session))


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


def setup_logging(debug: bool, log_folder_path: str) -> None:
    """
    Setup logging format and place - console for debug mode and rotating files for production
    """
    logger: logging.Logger = logging.getLogger()
    logger.propagate = False
    formatter = logging.Formatter(
        fmt="[%(asctime)s][%(user)s][%(levelname)s] %(message)s"
    )

    # Set console handler
    console_handler: logging.StreamHandler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    # File handler
    log_storage_path: pathlib.Path = pathlib.Path(log_folder_path)
    log_storage_path.mkdir(exist_ok=True)
    file_rollover_interval: datetime.time = datetime.time(hour=0, minute=0, second=0)
    file_log_handler: logging.handlers.TimedRotatingFileHandler = (
        logging.handlers.TimedRotatingFileHandler(
            filename=log_storage_path.joinpath("relval.log"),
            when="midnight",
            encoding="utf-8",
            atTime=file_rollover_interval,
            backupCount=60,
        )
    )
    file_log_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    # Set formatter
    console_handler.setFormatter(fmt=formatter)
    file_log_handler.setFormatter(fmt=formatter)

    # Include filters for all loggers
    console_handler.addFilter(filter=UsernameFilter())
    file_log_handler.addFilter(filter=UsernameFilter())

    # Include handlers
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_log_handler)


# Configure Database controller
Database.set_host_port(host=environment.MONGO_DB_HOST, port=environment.MONGO_DB_PORT)
Database.set_credentials(
    username=environment.MONGO_DB_USERNAME, password=environment.MONGO_DB_PASSWORD
)
Database.set_database_name("relval")
Database.add_search_rename("tickets", "created_on", "history.0.time")
Database.add_search_rename("tickets", "created_by", "history.0.user")
Database.add_search_rename("tickets", "workflows", "workflow_ids<float>")
Database.add_search_rename("relvals", "created_on", "history.0.time")
Database.add_search_rename("relvals", "created_by", "history.0.user")
Database.add_search_rename("relvals", "workflows", "workflows.name")
Database.add_search_rename("relvals", "workflow", "workflows.name")
Database.add_search_rename("relvals", "output_dataset", "output_datasets")

# Set logger
setup_logging(debug=environment.DEBUG, log_folder_path=environment.LOG_FOLDER)


def main():
    """
    Main function: start Flask web server
    """
    logger = logging.getLogger()
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # Do only once, before the reloader
        pid = os.getpid()
        logger.info("PID: %s", pid)
        with open("relval.pid", "w", encoding='utf-8') as pid_file:
            pid_file.write(str(pid))

    logger.info(
        "Starting... Debug: %s, Host: %s, Port: %s",
        environment.DEBUG,
        environment.HOST,
        environment.PORT,
    )
    app.run(
        host=environment.HOST,
        port=environment.PORT,
        threaded=True,
        debug=environment.DEBUG,
    )


if __name__ == "__main__":
    main()
