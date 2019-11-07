import json
import os
import requests

from ace_logger import Logging
from db_utils import DB

from requests.auth import HTTPBasicAuth

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}

def parse_params(parameters):
    logging.info(f'Parsing parameters')

    parameters = json.loads(parameters)

    static_params = parameters.get('static_args', {})
    url_params = parameters.get('url_args', {})
    dynamic_params = parameters.get('dynamic_args', [])

    logging.debug(f'Static: {static_params}')
    logging.debug(f'URL: {url_params}')
    logging.debug(f'Dynamic: {dynamic_params}')

    return static_params, url_params, dynamic_params

def get_auth(auth_type, auth_params):
    logging.info('Getting authentication data.')

    if auth_type is None:
        logging.info('No authentication.')
        return

    if auth_type.lower() == 'basic':
        user = auth_params.get('user', None)
        password = auth_params.get('password', None)

        if None in (user, password):
            message = 'User/Password is not given for authentication.'
            logging.error(message)
            raise ValueError(message)

        auth = HTTPBasicAuth(user, password)
    else:
        message = f'Unknown authentication type `{auth_type}`'
        logging.error(message)
        raise NotImplementedError(message)

    return auth

def hit(api_id, data=None, tenant_id=None):
    logging.info(f'Hitting API')

    logging.debug(f'API ID: {api_id}')
    logging.debug(f'Data: {data}')

    db = DB('api_config', tenant_id=tenant_id, **db_config)

    # Get the API configuration
    api_config = db.get_all('api', condition={'id': api_id})

    if api_config.empty:
        logging.error(f'No configuration found for API ID `{api_id}`')
        return

    logging.debug(f'API config: {api_config}')

    api_type = list(api_config['api_type'])[0]
    base_url = list(api_config['base_url'])[0]
    method = list(api_config['method'])[0].upper()
    parameters = list(api_config['parameters'])[0]
    auth_type = list(api_config['auth_type'])[0]
    auth_params = list(api_config['auth_params'])[0]

    # Parse the parameters
    try:
        static_params, url_params, dynamic_params = parse_params(parameters)
    except:
        logging.exception('Could not parse parameters.')
        return

    # Get the authentication data
    try:
        auth = get_auth(auth_type, auth_params)
    except:
        logging.exception('Error getting authentication data.')
        return

    # Check if dynamic params keys are there in the data received
    if not all(param in data for param in list(dynamic_params.keys())):
        logging.error(f'All dynamic parameter keys not found in data. (dynamic params: {dynamic_params})')
        return

    # Check if value of dynamic params are correct datatype


    if method == 'POST':
        logging.debug(f'POST method.')
        requests.post(base_url)
    elif method == 'GET':
        logging.debug(f'GET method.')
        requests.get(base_url)
    else:
        logging.error(f'Unknown method `{method}`')
        return

    return