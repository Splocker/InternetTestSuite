import time, smtplib, os, configparser, ssl, csv, speedtest
from filelock import FileLock
from threading import *
from pythonping import ping
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

config_folder = os.path.dirname(os.path.realpath(__file__))

#Setting class to handle the read and management of the config.ini file
class Settings:
    def __init__(self, folder_path):
        self.path = os.path.join(folder_path, 'config.ini').replace('\\','/')
        
        config = configparser.ConfigParser()
        with open(self.path, 'r', encoding='utf-8') as f:
            config.read_file(f)
            self.email_address = config['Email']['Address']
            self.email_password = config['Email']['Password']
            self.receiving_email = config['Email']['Receiving Email']
            self.deployment_id = config['Application Config']['Identifier']
            self.ping_frequency = config['Application Config'].getfloat('Pint Frequency')
            self.speedtest_frequency = config['Application Config'].getfloat('Speedtest Frequency')
            self.email_frequency = config['Application Config']['Log Frequency']
            self.email_day = config['Application Config']['Log Day']
            self.email_time = config['Application Config']['Log Time']
            
        
# If a ping to facebook or google make it though you have internet, otherwise you 
# either don't have internet or something very unusual is happening.
def checkConnection():
    timeStamp = time.time()
    try:
        if ((ping('facebook.com').success != False) or (ping('google.com').success != False)):
            return (timeStamp, True)
        else:
            return (timeStamp, False)
    except RuntimeError as e:
        return (timeStamp, False)
        
    

#Execute a speedTest and return the results in Mbit/s as a tuple (Download, Upload)
def speedTest():
    timeStamp = time.time()
    if checkConnection()[1]:
        speedTest = speedtest.Speedtest()
        return (timeStamp, speedTest.download()/1000000, speedTest.upload()/1000000)
    else:
        return (timeStamp, 0, 0)

def writeToCSV(file, headers, data):
    lock = FileLock(file + '.lock')
    lock.acquire()
    with lock:
        if os.path.exists(file) and os.path.isfile(file):
            with open(file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(data)
        else:
            with open(file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow(data)

    lock.release()

#Write the status of a connection check to the file
def writeConnectionStatus(status):
    writeToCSV('connection_status.csv', ['Timestamp','Live'], status)

def writeSpeedtestResults(results):
    writeToCSV('speedtest_results.csv',['Timestamp', 'Download', 'Upload'], results)

def constructMessage(settings: Settings):
    message = MIMEMultipart('alternative')

    if settings.email_frequency == 'M' or settings.email_frequency == 'm':
        message['Subject'] = f'Monthly {settings.deployment_id} Connection Report'
    elif settings.email_frequency == 'W' or settings.email_frequency ==  'w':
        message['Subject'] = f'Weekly {settings.deployment_id} Connection Report'
    elif settings.email_frequency == 'D' or settings.email_frequency ==  'd':
        message['Subject'] = f'Daily {settings.deployment_id} Connection Report'

    message['From'] = settings.email_address
    message['To'] = settings.receiving_email
    
    message.attach(MIMEText('This is a test.', 'plain'))

    return message

def sendEmail(settings: Settings, message: MIMEMultipart):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(settings.email_address, settings.email_password)

        server.sendmail(settings.email_address, settings.receiving_email, message.as_string())


if __name__=="__main__":

    settings = Settings(config_folder)

    for i in range(1):
        #Thread(target=writeConnectionStatus, args=[checkConnection()]).start()
        Thread(target=writeSpeedtestResults, args=[speedTest()]).start()
        
    #sendEmail(settings, constructMessage(settings))
