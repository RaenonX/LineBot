# -*- coding: utf-8 -*-
import httplib2
import os, sys

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import googleapiclient

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64

_PATH = os.path.dirname(__file__) + '/'

class gmail_api(object):
    # Credential file need to be regenerated if scopes is modified.
    SCOPES = 'https://www.googleapis.com/auth/gmail.send'  # https://developers.google.com/gmail/api/auth/scopes
    
    CLIENT_SECRET_FILE = _PATH + 'gmail_api_client.json'
    CREDENTIAL_FILE = _PATH + 'gmail-api-credential.json'
    APPLICATION_NAME = 'Gmail API - for sending error report from JELLYBOT'

    def __init__(self, default_subject_prefix):
        self._sender_email_addr = os.getenv('GMAIL_SENDER_ADDRESS', None)
        if self._sender_email_addr is None:
            print 'Define GMAIL_SENDER_ADDRESS in environment variable.'
            sys.exit(1)

        self._receiver_email_addr = os.getenv('GMAIL_RECEIVER_ADDRESS', None)
        if  self._receiver_email_addr is None:
            print 'Define GMAIL_RECEIVER_ADDRESS in environment variable.'
            sys.exit(1)

        _client_json_content = os.getenv('GMAIL_CLIENT_JSON', None)
        if _client_json_content is None:
            print 'Define GMAIL_CLIENT_JSON in environment variable.'
            sys.exit(1)
        else:
            with open(gmail_api.CLIENT_SECRET_FILE,'w') as f:
                f.write(_client_json_content)

        _credential_json_content = os.getenv('GMAIL_CREDENTIAL_JSON', None)
        if _client_json_content is None:
            print 'Define GMAIL_CLIENT_JSON in environment variable.'
            sys.exit(1)
        else:
            with open(gmail_api.CREDENTIAL_FILE,'w') as f:
                f.write(_credential_json_content)

        self._default_subject_prefix = default_subject_prefix
        self._credentials = gmail_api.get_credentials()
        self._http = self._credentials.authorize(httplib2.Http())
        self._service = discovery.build('gmail', 'v1', http=self._http)

    @staticmethod
    def get_credentials():
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        import argparse

        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
        flags.noauth_local_webserver = True

        store = Storage(gmail_api.CREDENTIAL_FILE)
        credentials = store.get()

        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(gmail_api.CLIENT_SECRET_FILE, gmail_api.SCOPES)
            flow.user_agent = gmail_api.APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            print 'Storing credentials to ' + gmail_api.CREDENTIAL_FILE

        return credentials
    
    def send_message(self, subject, content):
        """Send an email message.
    
        Args:
            subject: The subject of the email message. Will apply default subject suffix, format: {SUFFIX}{SUBJECT}
            message_text: The text of the email message.
    
        Returns:
            Result of sent message in unicode string.
        """
        try:
            if isinstance(content, unicode):
                content = str(content.encode('utf-8'))

            mime_multi = MIMEMultipart('alternative')
            mime_multi['from'] = self._sender_email_addr
            mime_multi['to'] = self._receiver_email_addr
            mime_multi['subject'] = self._default_subject_prefix + subject

            html_template = """\
            <html>
                <head>
                    <style>
                    body {{
                        font-family: monospace;
                        word-wrap: break-word;
                    }}
                    </style>
                </head>
                <body>
                    <p>{}</p>
                </body>
            </html>\
            """
            html = html_template.format(content.replace(' ', '&nbsp;').replace('\n', '<br>'))
            
            mail_plain = MIMEText(content, 'plain')
            mail_html = MIMEText(html, 'html')

            mime_multi.attach(mail_plain)
            mime_multi.attach(mail_html)

            mail_message = {'raw': base64.urlsafe_b64encode(mime_multi.as_string())}

            message = (self._service.users().messages().send(userId='me', body=mail_message).execute())
            result = u'成功' if 'SENT' in message['labelIds'] else u'失敗'
            return u'錯誤訊息寄送{}。信件ID: {}'.format(result, message['id'])
        except googleapiclient.errors.HttpError as error:
            return u'發生錯誤: {}'.format(error)
        except Exception as e:
            raise e
