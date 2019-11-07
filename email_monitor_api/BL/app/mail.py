import base64
import datetime
import email
import email.mime.multipart
import imaplib
import os
import re
import shutil
import time

try:
    from app.db_utils import DB 
    from app.ace_logger import Logging
    from app.mail import Email
    from app import app
    from app.producer import produce
except:
    from db_utils import DB
    from ace_logger import Logging

logging = Logging()


from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from zipfile import ZipFile

class Email():
    def __init__(self, imap_server='imap.gmail.com', max_login_attempts=3):
        mydate = datetime.datetime.now() - datetime.timedelta(1)
        self.today = mydate.strftime("%d-%b-%Y")
        self.imap_server = imap_server
        self.max_login_attempts = max_login_attempts
        # self.imap = imaplib.IMAP4_SSL('imap-mail.outlook.com')
        # self.smtp = smtplib.SMTP('smtp-mail.outlook.com')

    def login(self, username, password):
        self.username = username
        self.password = password
        login_attempts = 0
        while True:
            try:
                time.sleep(1)
                self.imap = imaplib.IMAP4_SSL(self.imap_server, 993)
                r, d = self.imap.login(username, password)
                assert r == 'OK', 'login failed'
                print(' > Logged in as {} {}'.format(username, d))
                return True
            except Exception as e:
                if b'AUTHENTICATIONFAILED' in e.args[0]:
                    print(' > Inavlid credentials.')
                    return False
                elif b'Lookup failed' in e.args[0]:
                    print(' > Cant find email.')
                    return False
                print(' > Sign In ... exception {}'.format(e))
                if login_attempts == self.max_login_attempts:
                    return False
                else:
                    login_attempts += 1
                continue
            break

    def list(self):
        return self.imap.list()

    def select(self, str):
        return self.imap.select(str)

    def inbox(self):
        return self.imap.select("Inbox")

    def junk(self):
        return self.imap.select("Junk")

    def logout(self):
        return self.imap.logout()

    def today(self):
        mydate = datetime.datetime.now()
        return mydate.strftime("%d-%b-%Y")

    def unread_ids_today(self):
        r, d = self.imap.search(None, '(SINCE "' + self.today + '")', 'UNSEEN')
        list = d[0].split()
        return list

    def unread_email_ids_from_date(self,from_date):
        from_date = from_date.strftime("%d-%b-%Y")
        r, d = self.imap.search(None, '(SINCE "' + from_date + '")', 'UNSEEN')
        list = d[0].split()
        return list

    def get_ids_with_word(self, ids, word):
        stack = []
        for id in ids:
            self.get_email(id)
            if word in self.mail_body().lower():
                stack.append(id)
        return stack

    def unread_ids(self):
        r, d = self.imap.search(None, "UNSEEN")
        list = d[0].split()
        return list

    def has_unread(self):
        list = self.unread_ids()
        return False if not list else True

    def read_ids_today(self):
        r, d = self.imap.search(None, '(SINCE "' + self.today + '")', 'SEEN')
        list = d[0].split()
        return list

    def all_ids(self):
        r, d = self.imap.search(None, "ALL")
        list = d[0].split()
        return list

    def read_ids(self):
        r, d = self.imap.search(None, "SEEN")
        list = d[0].split()
        return list

    def get_email(self, id):
        r, d = self.imap.fetch(id, "(RFC822)")
        self.raw_email = d[0][1]
        msg = None
        for response_part in d:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

        self.email_message = msg
        return self.email_message

    def get_unread(self, today=None):
        if today:
            list = self.unread_ids_today()
        else:
            list = self.unread_ids()
        latest_id = list[-1]
        return self.get_email(latest_id)

    def read(self):
        list = self.read_ids()
        latest_id = list[-1]
        return self.get_email(latest_id)

    def read_today(self):
        list = self.read_ids_today()
        latest_id = list[-1]
        return self.get_email(latest_id)

    def unread_today(self):
        list = self.unread_ids_today()
        latest_id = list[-1]
        return self.get_email(latest_id)

    def read_only(self, folder):
        return self.imap.select(folder, readonly=True)

    def raw_read(self):
        list = self.read_ids()
        latest_id = list[-1]
        r, d = self.imap.fetch(latest_id, "(RFC822)")
        self.raw_email = d[0][1]
        return self.raw_email

    def get_attachments(self):
        attachments_dict = {}
        self.dload_folder = None
        for part in self.email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            data = part.get_payload(decode=True)
            attachments_dict[filename] = data
        
        return attachments_dict

    def has_attachments(self):
        attachment_flag = False
        attach_file_paths = []
        self.dload_folder = None
        for part in self.email_message.walk():
            filename = part.get_filename()
            data = part.get_payload(decode=True)
            if not data:
                continue
            self.dload_folder = "{}-{}".format(self.mail_subject(), self.today)
            self.dload_folder = re.sub(r'[:/?*|\s"]', r'_', self.dload_folder)
            dload_path = "./{}/{}".format(self.dload_folder, filename)
            attach_file_paths.append(dload_path)

        if len(attach_file_paths) > 2:
            attachment_flag = True

        return attachment_flag

    def zip_attachments(self, file_paths):
        with ZipFile("{}.zip".format(self.mail_subject()), 'w') as zip:
            # Writing each file one by one
            for file in file_paths:
                zip.write(file)
            if self.dload_folder:
                shutil.rmtree(self.dload_folder)

    def write_to_file(self, body):
        sub = self.mail_subject()
        if self.mail_subject()[0] == "=":
            sub = "New Subject"
        try:
            file = open("{}.txt".format(sub), "w+")
            file.write(body)
        except Exception as e:
            print(e)
        finally:
            file.close()

    def get_body(self, msg):
        if msg.is_multipart():
            return self.get_body(msg.get_payload(0))
        else:
            return msg.get_payload(None, True)

    def mail_body(self):
        body = self.get_body(self.email_message)
        return body.decode("utf-8")

    def mail_subject(self):
        return self.email_message['subject']

    def mail_from(self):
        return self.email_message['from']

    def mail_to(self):
        return self.email_message['to']

    def mail_cc(self):
        return self.email_message['cc']

    def mail_time(self):
        return self.email_message['date']

    def mail_return_path(self):
        return self.email_message['Return-Path']

    def mail_reply_to(self):
        return self.email_message['Reply-To']

    def mail_all(self):
        return self.email_message

    def mail_body_decoded(self):
        return base64.urlsafe_b64decode(self.mail_body())
