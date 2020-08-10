"""
Main module that starts flask web server
"""
import logging
import argparse
from flask_restful import Api
from flask_cors import CORS
from flask import Flask, render_template
from core_lib.database.database import Database
from core_lib.utils.global_config import Config
from api.system_api import (LockerStatusAPI,
                            UserInfoAPI,
                            SubmissionWorkerStatusAPI,
                            SubmissionQueueAPI,)
from api.search_api import SearchAPI, SuggestionsAPI
from api.ticket_api import (CreateTicketAPI,
                            DeleteTicketAPI,
                            UpdateTicketAPI,
                            GetTicketAPI,
                            GetEditableTicketAPI,
                            CreateRelValsForTicketAPI)
from api.relval_api import (CreateRelValAPI,
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
                            UpdateRelValWorkflowsAPI)
from api.campaign_api import (CreateCampaignAPI,
                              DeleteCampaignAPI,
                              UpdateCampaignAPI,
                              GetCampaignAPI,
                              GetEditableCampaignAPI)
from api.settings_api import SettingsAPI

log_format = '[%(asctime)s][%(levelname)s] %(message)s'
logging.basicConfig(format=log_format, level=logging.DEBUG)

app = Flask(__name__,
            static_folder='./vue_frontend/dist/static',
            template_folder='./vue_frontend/dist')
# Set flask logging to warning
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app.url_map.strict_slashes = False
api = Api(app)
CORS(app,
     allow_headers=['Content-Type',
                    'Authorization',
                    'Access-Control-Allow-Credentials'],
     supports_credentials=True)


@app.route('/', defaults={'_path': ''})
@app.route('/<path:_path>')
def catch_all(_path):
    """
    Return index.html for all paths except API
    """
    return render_template('index.html')


@app.route('/api', defaults={'_path': ''})
@app.route('/api/<path:_path>')
def api_documentation(_path):
    """
    Endpoint for API documentation HTML
    """
    docs = {}
    for endpoint, view in app.view_functions.items():
        view_class = dict(view.__dict__).get('view_class')
        if view_class is None:
            continue

        class_name = view_class.__name__
        class_doc = view_class.__doc__.strip()
        #pylint: disable=protected-access
        urls = sorted([r.rule for r in app.url_map._rules_by_endpoint[endpoint]])
        #pylint: enable=protected-access
        category = [x for x in urls[0].split('/') if x][1]
        if category not in docs:
            docs[category] = {}

        docs[category][class_name] = {'doc': class_doc, 'urls': urls, 'methods': {}}
        for method_name in view_class.methods:
            method = view_class.__dict__.get(method_name.lower())
            method_dict = {'doc': method.__doc__.strip()}
            docs[category][class_name]['methods'][method_name] = method_dict
            if hasattr(method, '__role__'):
                method_dict['role'] = getattr(method, '__role__')

    return render_template('api_documentation.html', docs=docs)


api.add_resource(LockerStatusAPI, '/api/system/locks')
api.add_resource(UserInfoAPI, '/api/system/user_info')
api.add_resource(SubmissionWorkerStatusAPI, '/api/system/workers')
api.add_resource(SubmissionQueueAPI, '/api/system/queue')

api.add_resource(SettingsAPI,
                 '/api/settings/get',
                 '/api/settings/get/<string:name>')

api.add_resource(SearchAPI, '/api/search')
api.add_resource(SuggestionsAPI, '/api/suggestions')

api.add_resource(CreateTicketAPI, '/api/tickets/create')
api.add_resource(DeleteTicketAPI, '/api/tickets/delete')
api.add_resource(UpdateTicketAPI, '/api/tickets/update')
api.add_resource(GetTicketAPI, '/api/tickets/get/<string:prepid>')
api.add_resource(GetEditableTicketAPI,
                 '/api/tickets/get_editable',
                 '/api/tickets/get_editable/<string:prepid>')
api.add_resource(CreateRelValsForTicketAPI, '/api/tickets/create_relvals')

api.add_resource(CreateRelValAPI, '/api/relvals/create')
api.add_resource(DeleteRelValAPI, '/api/relvals/delete')
api.add_resource(UpdateRelValAPI, '/api/relvals/update')
api.add_resource(GetRelValAPI, '/api/relvals/get/<string:prepid>')
api.add_resource(GetEditableRelValAPI,
                 '/api/relvals/get_editable',
                 '/api/relvals/get_editable/<string:prepid>')
api.add_resource(GetCMSDriverAPI, '/api/relvals/get_cmsdriver/<string:prepid>')
api.add_resource(GetConfigUploadAPI, '/api/relvals/get_config_upload/<string:prepid>')
api.add_resource(GetRelValJobDictAPI, '/api/relvals/get_dict/<string:prepid>')
api.add_resource(GetDefaultRelValStepAPI, '/api/relvals/get_default_step')
api.add_resource(RelValNextStatus, '/api/relvals/next_status')
api.add_resource(RelValPreviousStatus, '/api/relvals/previous_status')
api.add_resource(UpdateRelValWorkflowsAPI, '/api/relvals/update_workflows')

api.add_resource(CreateCampaignAPI, '/api/campaigns/create')
api.add_resource(DeleteCampaignAPI, '/api/campaigns/delete')
api.add_resource(UpdateCampaignAPI, '/api/campaigns/update')
api.add_resource(GetCampaignAPI, '/api/campaigns/get/<string:prepid>')
api.add_resource(GetEditableCampaignAPI,
                 '/api/campaigns/get_editable',
                 '/api/campaigns/get_editable/<string:prepid>')


def main():
    """
    Main function: start Flask web server
    """
    parser = argparse.ArgumentParser(description='RelVal Machine')
    parser.add_argument('--mode',
                        help='Use production (prod) or development (dev) section of config',
                        choices=['prod', 'dev'],
                        required=True)
    parser.add_argument('--config',
                        default='config.cfg',
                        help='Specify non standard config file name')
    parser.add_argument('--debug',
                        help='Run Flask in debug mode',
                        action='store_true')
    args = vars(parser.parse_args())
    config = Config.load(args.get('config'), args.get('mode'))
    database_auth = config.get('database_auth')

    Database.set_database_name('relval')
    if database_auth:
        Database.set_credentials_file(database_auth)

    debug = args.get('debug', False)
    port = int(config.get('port', 8005))
    host = config.get('host', '0.0.0.0')
    app.run(host=host,
            port=port,
            threaded=True,
            debug=debug)

if __name__ == '__main__':
    main()
