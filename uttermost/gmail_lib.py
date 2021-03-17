import email
import imaplib
import json
import logging
import os
import sys
import tempfile

file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('LOGGER_NAME')


class Gmail:

    def __init__(self):

        self.username = os.environ.get("gmailUsername")
        self.password = os.environ.get("gmailPassword")
        self.temp_directory_path = tempfile.gettempdir()
        #self.email_subject = os.environ.get("email_subject")

    def DownloadAttachement(self, email_subject):
        """Download attechment from gmail whose not seen.
        """
        try:
            username = self.username
            password = self.password
            imap_url = 'imap.gmail.com'

            mail = imaplib.IMAP4_SSL(imap_url)
            mail.login(username, password)
            mail.select('Inbox')
            _, data = mail.search(None, 'UnSeen')
            mail_ids = data[0]
            id_list = mail_ids.split()
            if len(id_list) > int(0):
                for num in data[0].split():
                    typ, data = mail.fetch(num, '(RFC822)')
                    raw_email = data[0][1]

                # converts byte literal to string removing b''
                raw_email_string = raw_email.decode('utf-8')
                email_message = email.message_from_string(raw_email_string)
                # downloading attachments
                fileName = ''
                for part in email_message.walk():
                    fileName = part.get_filename()
                    if bool(fileName):
                        # check valid subject
                        subject = str(email_message).split("Subject: ", 1)[
                            1].split("\nTo:", 1)[0].split("\nFrom:", 1)[0]
                        if subject == email_subject:
                            # set directory name when json file do you want to upload
                            attachment_dir = self.temp_directory_path
                            if os.path.exists(attachment_dir):
                                filePath = os.path.join(
                                    attachment_dir, fileName)
                                if not os.path.isfile(filePath):
                                    fp = open(filePath, 'wb')
                                    fp.write(part.get_payload(decode=True))
                                    fp.close()

                                # check valid excel file
                                fileExtension = fileName.split(".")[1]
                                if fileExtension == "xls" or fileExtension == "xlsx" or fileExtension == "XLS" or fileExtension == "XLSX":
                                    return fileName

                                else:
                                    os.remove(filePath)
                                    logger.info("Invalid file extension.")

                            else:
                                logger.info("temp directory not found.")
            else:
                logger.info("Unread email not found.")

        except imaplib.IMAP4.error:
            logger.info("Invalid login credentials.")

        except Exception as e:
            logger.info("Exception import email from gmail server")
            logger.info(e)
