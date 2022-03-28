import time, smtplib, os, configparser, ssl, csv, speedtest, matplotlib
from turtle import speed
from tokenize import Double
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

class connection_status:
    def __init__(self, time: Double, connection_up: bool) -> None:
        self._time = time
        self._connection_up = connection_up

    @property
    def time(self):
        return self._time

    @property
    def connection_up(self):
        return self._connection_up

class speedtest_result:
    def __init__(self, time: Double, download: Double, upload: Double) -> None:
        self._time = time
        self._download = download
        self._upload = upload

    @property
    def time(self):
        return self._time

    @property
    def download(self):
        return self._download

    @property
    def upload(self):
        return self._upload
        
# If a ping to facebook or google make it though you have internet, otherwise you 
# either don't have internet or something very unusual is happening.
def checkConnection() -> connection_status:
    timeStamp = time.time()
    try:
        if ((ping('facebook.com').success != False) or (ping('google.com').success != False)):
            return connection_status(timeStamp, True)
        else:
            return (timeStamp, False)
    except RuntimeError as e:
        return connection_status(timeStamp, False)

#Execute a speedTest and return the results in Mbit/s as a tuple (Download, Upload)
def speedTest() -> speedtest_result:
    timeStamp = time.time()
    if checkConnection().connection_up:
        speedTest = speedtest.Speedtest()
        return speedtest_result(timeStamp, speedTest.download()/1000000, speedTest.upload()/1000000)
    else:
        return speedtest_result(timeStamp, 0, 0)

#Pass in the file to be written to, the headers for the first line of the file and the adat to be written.
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
def writeConnectionStatus(status: connection_status):
    writeToCSV('connection_status.csv', ['Timestamp','Live'], (status.time, status.connection_up))

#Run a speedtest and write the results to a CSV
def writeSpeedtestResults(results: speedtest_result):
    writeToCSV('speedtest_results.csv',['Timestamp', 'Download', 'Upload'], (results.time, results.download, results.upload))

#Construc the and return a MIMEMultipart email message.
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

    message_body = f'''
    <center><h2>{settings.deployment_id} Connection Update</h2></center>
    <p>Connection health update.</p>
    '''
    
    message.attach(MIMEText(message_body, 'html'))

    return message

#Send a passed MIMEMultipart email message.
def sendEmail(settings: Settings, message: MIMEMultipart):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(settings.email_address, settings.email_password)

        server.sendmail(settings.email_address, settings.receiving_email, message.as_string())

if __name__=="__main__":

    settings = Settings(config_folder)

    for i in range(1):
        Thread(target=writeConnectionStatus, args=[checkConnection()]).start()
        Thread(target=writeSpeedtestResults, args=[speedTest()]).start()
        
    sendEmail(settings, constructMessage(settings))
