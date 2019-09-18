import json

from datetime import datetime
from pandas import to_timedelta, DataFrame
from pathlib import Path

try:
    from app.ace_logger import Logging
    from app.db_utils import DB
except:
    from ace_logger import Logging
    from db_utils import DB

from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body =encoded_span
    requests.post(
            'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

logging = Logging()

class JSONExport(object):
    def __init__(self, export_type='Case ID', excluded_fields=[], field_mapping=None):
        logging.debug('Intializing JSON Export object.')

        default_exclusions = ['created_date', 'case_id', 'highlight']

        self.export_type = export_type
        self.excluded_fields = [i for i in list(set(default_exclusions + excluded_fields)) if i is not None and i]
        self.field_mapping = field_mapping

        logging.info(f'Export Type: {self.export_type}')
        logging.info(f'Excluded Fields: {self.excluded_fields}')

        self.output_json = {}

    @zipkin_span(service_name='excel_export_api', span_name='export')
    def export(self, metadata, data):
        logging.info('JSON export started')
        
        # Sanity checks
        if not isinstance(metadata, DataFrame):
            logging.warning('Metadata is not a dataframe. Skipping metadata.')
            metadata = None

        if not isinstance(data, DataFrame):
            logging.error('Data is not a dataframe. No data to export.')
            return None        
        
        # Metadata related work
        logging.info('Metadata creation...')
        if metadata is None:
            logging.warning(' - Metadata not exported because its none. Skipping metadata.')
        else:
            self.output_json['metadata'] = metadata.to_dict('records')[0]

            logging.debug(' - Changing `created_date` timezone')
            created_date = self.output_json['metadata']['created_date']
            self.output_json['metadata']['created_date'] = ((created_date + to_timedelta(5.5, unit='h')).strftime(r'%B %d, %Y %I:%M %p'))

            logging.debug(' - Changing `last_updated` timezone')
            last_updated = self.output_json['metadata']['last_updated']
            self.output_json['metadata']['last_updated'] = ((last_updated + to_timedelta(5.5, unit='h')).strftime(r'%B %d, %Y %I:%M %p'))

        # Dropping unnecessary/user defined columns from the data
        logging.info('Dropping columns...')
        logging.debug(f' - Columns: {self.excluded_fields}')
        filtered_data = data.drop(self.excluded_fields, axis=1)
        self.output_json['fields'] = filtered_data.to_dict('records')
        
        # Rename fields if any provided (field mapping)
        logging.info('Renaming keys of data...')
        if self.field_mapping is not None or self.field_mapping:
            for field_name, new_name in self.field_mapping.items():
                for item in self.output_json['fields']:
                    if field_name in item:
                        item[new_name] = item.pop(field_name)
                        logging.debug(f' - `{field_name}` => `{new_name}`')
                    else:
                        logging.debug(f' - `{field_name}` not found.')
        else:
            logging.info(' - No field mapping configured. Skipping.')
        
        save_status, message = self.save_json()
        
        return {'flag': save_status, 'message': message}

    @zipkin_span(service_name='excel_export_api', span_name='save_json')
    def save_json(self):
        logging.info('Saving JSON...')

        logging.debug(f' - Export type: {self.export_type}')
        if self.export_type.lower() == 'case id':
            file_stem = self.output_json['metadata']['case_id']
        elif self.export_type.lower() == 'file name':
            file_stem = self.output_json['metadata']['file_name'].rsplit('.', 1)[0]
        elif self.export_type.lower() == 'datetime':
            current_time = datetime.now()
            file_stem = current_time.strftime(f'%Y%m%d%H%M%S')
        else:
            message = f'Unknown format `{self.export_type}`'
            logging.error(f' - {message}')
            return False, message

        output_path = Path('./output')
        file_name = file_stem + '.json'
        export_path = output_path / file_name

        if output_path.is_dir():
            logging.debug(f'Path exists. [{str(output_path.absolute())}]')
        else:
            logging.debug(f'Path does not exists. [{str(output_path.absolute())}]')

        try:
            with open(export_path, 'w') as f:
                f.write(json.dumps(self.output_json, indent=2))
            message = f'JSON exported successfully. ({export_path})'
            logging.info(f' - {message}')
            return True, message
        except:
            message = 'Error occured while saving the JSON.'
            logging.exception(f' - {message}')
            return False, message
        
