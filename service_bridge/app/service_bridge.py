"""
Author: Ashyam
Created Date: 20-02-2019
"""
import json
import requests
import traceback
import subprocess

from flask import Flask, request, jsonify, flash
from urllib.parse import urlparse

from app import app
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

@app.route('/test', methods=['POST', 'GET'])
def test():
    try:
        data = request.json

        if data['data']:
            return jsonify({'flag': True, 'data': data})
        else:
            return jsonify({'flag': False, 'message': 'Failed to execute the function.'})
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/<route>', defaults={'argument': None}, methods=['POST', 'GET'])
@app.route('/<route>/<argument>', methods=['POST', 'GET'])
def connect(route, argument=None):
    """
    This is the only route called from the UI along with the name of the route in
    the URL and the data to be POSTed. This app will reroute to the corresponding
    route sent from the UI.
    The final URL will be generated using the bridge_config.json file. The route
    and its corresponding host and port will be stored in this file.

    Args:
        route (str): The route it should call this app should reroute to.
        data (dict): The data that needs to be sent to the URL.

    Returns:
        flag (bool): True if success otherwise False.
        message (str): Message for the user.

    Note:
        Along with the mentioned keys, there will be other keys that the called
        route will return. (See the docstring of the app)
    """
    try:
        logging.info('Serving a request')
        logging.info(f'Route: {route}')
        logging.info(f'Argument: {argument}')

        logging.debug('Reading bridge config')
        with open('/var/www/service_bridge/app/bridge_config.json') as f:
            connector_config = json.loads(f.read())

        if route not in connector_config:
            message = f'Route `{route}` is not configured in bridge_config.json.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        route_config = connector_config[route]
        host = route_config['host']
        port = route_config['port']

        logging.debug(f'Host: {host}')
        logging.debug(f'Port: {port}')

        if request.method == 'POST':
            logging.debug('POST method.')
            try:

                try:
                    data = request.json
                    logging.info(f'Data recieved: {data}')
                except:
                    logging.warning('No data recieved.')
                    data = {}

                tenant_id = None
                try:
                    if 'tenant_id' not in data:    
                        if 'host_url' in data:
                            ui_url=data['host_url']
                            logging.info(f'Got host URL as parameter: {ui_url}')
                        else:
                            ui_url = request.headers.get('Origin')
                        url = urlparse(ui_url).netloc

                        logging.info(f'Request header origin: {ui_url}')
                        logging.info(f'URL: {url}')

                        with open('/var/www/service_bridge/app/tenants.json') as t:
                            tenants = json.loads(t.read())
                            logging.debug(f'Tenant data: {tenants}')

                        for key, val in tenants['tenants'].items():
                            if key == url:
                                tenant_id = val
                                break
                        
                        if tenant_id is None or not tenant_id:
                            logging.warning('Could not find tenant url in tenants.json')
                        
                        logging.info(f'Tenant ID: {tenant_id}')
                    else:
                        logging.warning('Tenant ID already in request data!')
                        tenant_id = data['tenant_id']
                except:
                    logging.exception('Could not get tenant ID from request. Setting tenant ID to None.')
                    tenant_id = None
                try:
                    if tenant_id.lower() not in ['deloitte','karvy']:
                        tenant_id = None
                except:
                    pass
                data['tenant_id'] = tenant_id
                logging.info(f'Data after adding tenant ID: {data}')

                if argument is not None:
                    response = requests.post(f'http://{host}:{port}/{route}/{argument}', json=data)
                else:
                    response = requests.post(f'http://{host}:{port}/{route}', json=data)

                logging.debug(f'Response: {response.content}')
                try:
                    return jsonify(response.json())
                except:
                    return response.content
            except requests.exceptions.ConnectionError as e:
                message = f'ConnectionError: {e}'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})
            except Exception as e:
                message = f'Could not serve request.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})
        elif request.method == 'GET':
            logging.debug('GET method.')
            try:
                response = requests.get(f'http://{host}:{port}/{route}')
                logging.debug(f'Response: {response.content}')
                return jsonify(json.loads(response.content))
            except requests.exceptions.ConnectionError as e:
                message = f'ConnectionError: {e}'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})
            except Exception as e:
                message = f'Unknown error calling `{route}`. Maybe should use POST instead of GET. Check logs.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})
    except Exception as e:
        logging.exception('Something went wrong in service bridge. Check trace.')
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})


@app.route('/zipkin', methods=['POST', 'GET'])
def zipkin():
    body = request.data
    requests.post(
            'http://zipkin:9411/api/v1/spans',
            data=body,
            headers={'Content-Type': 'application/x-thrift'},
        )
    return jsonify({'flag': True})
