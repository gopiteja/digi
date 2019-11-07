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

def check_dyanmic_value_type(value, value_type):
    try:
        if isinstance(value, eval(value_type)):
            return True
        else:
            logging.error(f'Expected type `{value_type}` got type `{type(value)}`')
    except:
        logging.exception('Could not evaluate data type.')
        return False

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

    api_type = list(api_config['api_type'])[0]
    base_url = list(api_config['base_url'])[0]
    method = list(api_config['method'])[0].upper()
    parameters = list(api_config['parameters'])[0]
    auth_type = list(api_config['auth_type'])[0]
    auth_params = list(api_config['auth_params'])[0]

    logging.debug(f'API Type: {api_type}')
    logging.debug(f'Base URL: {base_url}')
    logging.debug(f'Method: {method}')
    logging.debug(f'Paramters: {parameters}')
    logging.debug(f'Auth Type: {auth_type}')
    logging.debug(f'Auth Params: {auth_params}')

    # Parse the parameters
    try:
        static_params, url_params, dynamic_params = parse_params(parameters)
    except:
        message = 'Could not parse parameters.'
        logging.exception(message)
        return {'flag': False, 'message': message}

    # Get the authentication data
    try:
        auth = get_auth(auth_type, auth_params)
    except:
        message = 'Error getting authentication data.'
        logging.exception(message)
        return {'flag': False, 'message': message}

    # Check if dynamic params keys are there in the data received
    dynamic_values = {}
    for param, conf in dynamic_params.items():
        param_type = conf.get('type', None)
        
        if param not in data:
            message = f'All dynamic parameter keys not found in data. (dynamic params: {dynamic_params})'
            logging.error(message)
            return {'flag': False, 'message': message}
        
        # Check if value of dynamic params are correct datatype
        if check_dyanmic_value_type(data[param], param_type):
            dynamic_values[param] = data[param]
        else:
            return {'flag': False, 'message': f'Expected type `{param_type}` for `{param}` got type `{type(data[param]).__name__}`'}
    
    # Create the final JSON to send
    final_data = {**static_params, **dynamic_values}

    if method == 'POST':
        logging.debug(f'POST method.')
        requests.post(base_url, json=final_data, params=url_params, auth=auth)
    elif method == 'GET':
        logging.debug(f'GET method.')
        requests.get(base_url, json=final_data, params=url_params, auth=auth)
    else:
        message = f'Unknown method `{method}`'
        logging.error(message)
        return {'flag': False, 'message': message}

    return