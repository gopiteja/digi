"""
Author: Ashyam
Created Date: 18-02-2019
"""
import argparse
import requests
import json
import uuid

from db_utils import DB

from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path

try:
    from app import app
    from app.ace_logger import Logging
    from app.producer import produce
except:
    from ace_logger import Logging
    from producer import produce
    app = Flask(__name__)
    CORS(app)

logging = Logging()

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

@app.route('/send_email', methods=['POST', 'GET'])
def send_email():
    try:
        data = request.json
        logging.debug(data)
        
        logging.debug('Sending email')
        logging.debug('*******************************************************************')
        
        '''
        case_id_data_dict = {'case_id': 'Fixed lump sum billing', 'created_date': Timestamp('2019-09-02 09:05:39'),
        'Customer_ID': '700002', 'Contact_Person': 'Chris Jacob', 'Billing_Address': '9 Richmond Road', 
        'City': 'NEWPORT', 'City_Postal_Code': 'NP15 5AN', 'Telephone_Number': '+44 1632 960792', 
        'PO Number': '450003213', 'Customer name': 'Imagemagick', 'Contract Value (excl. tax)': '500000', 
        'Tax rate': '12.0', 'Contract start date': '2019-04-01', 'Contract end date': '2019-12-31', 
        'Contract_Reference': '422322', 'Type_of_Invoice': 'Single Lumpsum', 'Billing_Amount': 500000,
        'Hotel_Charges': None}
        
        '''

        db_config = {
                'host': '3.208.195.34',
                'port': '3306',
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
            }

        db = DB('karvy_email',**db_config)

        email_template = db.get_all('email_template')
        karvy_email_dict = email_template.loc[email_template['for_email'] == 'karvy'].to_dict(orient = 'records')[0]

        vendor_email = karvy_email_dict['to_email']
        contact_person = karvy_email_dict['sender_name']
        to_emails = [vendor_email]
        from_email = karvy_email_dict['from_email']
        trans = karvy_email_dict['transaction']
        receiver_name = karvy_email_dict['sender_name']
        subject = f'Invoice/Request/Claim processed, for Contract reference `{trans}`'
        body = f"""
        Dear {receiver_name},

        Hope you are doing good.

        We have recieved the attached email for processing/payment.

        The invoice has been generated upon approval.

        Please refer to below details for your further perusal:

        Contract reference  : {Contract_Reference}
        Invoice number      : {invoice_number}
        Contract type       : {Contract_type}
        Customer ID         : {Customer_ID}
        Invoice date        : {invoice_date}
        Invoice value       : {invoice_value}
        

        For any further clarification, please contact Algonox Technologies:

        verifier: '{contact_person}'


        Regards,
        Jayasilan
        Algonox Technologies
        """

        'Email to - ramesht@drreddys.com / kumarm@drreddys.com'
        # Payment Due Date: {payment_due_date}
        # Additional Comments: {comments}

        email_config = db.get_all('email_config')
        email_config_dict = email_config.loc[email_config['for_email'] == 'karvy'].to_dict(orient ='records')[0]
        smtp_config = email_config_dict['SMTP server address']
        passw = email_config_dict['password']
        port = email_config_dict['port']

        try:
            try:
                attachment_dir = Path('./attachments')
            except Exception as e:
                logging.debug('No attachments ',e)
            msg = MIMEMultipart() # Create a message
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            # msg['Cc'] = ', '.join(cc)
            msg['Subject'] = subject
            msg.attach(MIMEText(body))

            try:
                logging.debug('Attaching Attachments')
                for file_path in attachment_dir.glob('**/*'):
                    # if case_id not in str(file_path):
                    #     continue


                    logging.debug('file path ',file_path)
                    if file_path.is_file():
                        file_name = file_path.name
                        logging.debug('file_name', file_name)
                        p = MIMEBase('application', 'octet-stream')
                        with open(file_path, 'rb') as attachment:
                            p.set_payload((attachment).read())

                            encoders.encode_base64(p)
                            p.add_header('Content-Disposition', 'attachment; filename={}'.format(file_name))
                            msg.attach(p)
            except Exception as e:
                logging.debug('No error ',e)
                
            p = MIMEBase('application', 'octet-stream')
            # s = smtplib.SMTP('smtp.gmail.com', 587)
            s = smtplib.SMTP(f"{smtp_config}",port)

            # Start TLS for security
            s.starttls()
            logging.debug('reached Authentification stage')
            # Authentication
            s.login(from_email, f'{passw}')

            # Converts the Multipart msg into a string
            text = msg.as_string()
            logging.debug('sending mail stage')
            # Send the mail
            # s.sendmail(from_email, to_emails + cc, text)
            s.sendmail(from_email, to_emails, text)
            logging.debug('mail sent')
            # Terminate session
            s.quit()
        except Exception as e:
            message = f'Error sending mail: {e}'
            logging.debug(f'{Fore.RED}{message}')
            return jsonify({'flag': False, 'message': message})


        message = f'Succesfully sent mail.'
        logging.debug(f'{Fore.GREEN}{message}')
        return jsonify({'flag': True, 'message': message})
    except:
        logging.exception(f"Unexpected error in sending mail")
 
    logging.info(f'Data returned: {data}')
    return jsonify(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5000)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
