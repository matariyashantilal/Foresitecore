import imaplib
import email
import excel2json
import os
import sys
import shopify
#import shopify_helper
import json
import logging
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

class ImportEmailFromGmail:

	def __init__(self):
		#config = loadConfig.config()
		#self.temp_directory_path = config.data["temp_directory_path"]
		#self.email_subject = config.data["email_subject"]

		self.username = os.environ.get("gmailUsername")
		self.password = os.environ.get("gmailPassword")
		self.temp_directory_path = tempfile.gettempdir()
		self.email_subject = os.environ.get("emailsubject_inventorycountsuttermost")

	def ImportEmailDownloadAttachement(self):
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
					typ, data = mail.fetch(num, '(RFC822)' )
					raw_email = data[0][1]
					
				# converts byte literal to string removing b''
				raw_email_string = raw_email.decode('utf-8')
				email_message = email.message_from_string(raw_email_string)
				# downloading attachments
				for part in email_message.walk():
					fileName = part.get_filename()
					if bool(fileName):
						#check valid subject
						subject = str(email_message).split("Subject: ", 1)[1].split("\nTo:", 1)[0].split("\nFrom:", 1)[0]
						if subject == self.email_subject:
							#set directory name when json file do you want to upload
							attachment_dir = self.temp_directory_path
							if os.path.exists(attachment_dir):
								filePath = os.path.join(attachment_dir, fileName)
								if not os.path.isfile(filePath) :
									fp = open(filePath, 'wb')
									fp.write(part.get_payload(decode=True))
									fp.close()
									
								#check valid excel file
								fileExtension = fileName.split(".")[1]
								if fileExtension == "xls" or fileExtension == "xlsx" or fileExtension == "XLS" or fileExtension == "XLSX":
									excel2json.convert_from_file(filePath)
									if os.path.exists(attachment_dir+"/Uttermost Item Availability.json"):
										os.remove(filePath)
										logger.info("Get shopify products")
										sps = shopify_helper.ShopifyProducts()
										
										AvailabilityProduct	=	{}
										with open(attachment_dir+"/Uttermost Item Availability.json") as file_handle:
											AvailabilityProduct = json.load(file_handle)
										
										tempAvailabilityProductSKU	=	[]
										tempAvailabilityProductSKUList	=	dict()
										
										for p in AvailabilityProduct:	
											tempAvailabilityProductSKU.append(p["SKU"])
											# This will need some custom logic to get the ETA. 
											# Did India already implement the custom action?
											tempAvailabilityProductSKUList[p["SKU"]]	=	p["EC Qty"]
										
										sps.uploadProduct(tempAvailabilityProductSKU,tempAvailabilityProductSKUList)
										logger.info("Products has been updated successfully on shopify.")
									else:
										os.remove(filePath)
										logger.info("Json has not created.")
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

