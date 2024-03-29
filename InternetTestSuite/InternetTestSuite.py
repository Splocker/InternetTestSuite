import time, smtplib, os, configparser, ssl, csv, speedtest, re, logging, base64
from turtle import speed
from matplotlib import pyplot as plot
from io import BytesIO
from filelock import FileLock
from threading import *
from pythonping import ping
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

config_folder = os.path.dirname(os.path.realpath(__file__))

# Setting class to handle the read and management of the config.ini file
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

# Simple class for conneciton status result storage
class connection_status:
    def __init__(self, time: float, connection_up: bool) -> None:
        self._time = time
        self._connection_up = connection_up

    @property
    def time(self):
        return self._time

    @property
    def connection_up(self):
        return self._connection_up

    def toString(self) -> str:
        return f'(connection_status: {{timestamp:{self.time}, connection_up: {self.connection_up}}})'

# Simple class for speedtest result storage
class speedtest_result:
    def __init__(self, time: float, download: float, upload: float) -> None:
        self.__time = time
        self.__download = download
        self.__upload = upload

    @property
    def time(self):
        return self.__time

    @property
    def download(self):
        return self.__download

    @property
    def upload(self):
        return self.__upload

    def toString(self) -> str:
        return f'(speedtest_result: {{timestamp:{self.time}, download: {self.download}, upload: {self.upload}}})'

        
# If a ping to facebook or google make it though you have internet, otherwise you 
# either don't have internet or something very unusual is happening.
def checkConnection() -> connection_status:
    timeStamp = time.time()
    try:
        if ((ping('facebook.com').success) or (ping('google.com').success)):
            return connection_status(timeStamp, True)
        else:
            return (timeStamp, False)
    except RuntimeError as e:
        if (re.search("^Cannot resolve address \".*\", try verify your DNS or host file$", str(e))):
            return connection_status(timeStamp, False)
        # Log the error here.
        return connection_status(timeStamp, False)

# Execute a speedTest and return the results in Mbit/s as a tuple (Download, Upload)
def speedTest() -> speedtest_result:
    timeStamp = time.time()
    if checkConnection().connection_up:
        speedTest = speedtest.Speedtest()
        return speedtest_result(timeStamp, speedTest.download()/1000000, speedTest.upload()/1000000)
    else:
        return speedtest_result(timeStamp, 0, 0)

# Pass in the file to be written to, the headers for the first line of the file and the adat to be written.
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

# Write the status of a connection check to the file
def writeConnectionStatus(status: connection_status):
    writeToCSV('connection_status.csv', ['Timestamp','Live'], (status.time, status.connection_up))

# Run a speedtest and write the results to a CSV
def writeSpeedtestResults(results: speedtest_result):
    writeToCSV('speedtest_results.csv',['Timestamp', 'Download', 'Upload'], (results.time, results.download, results.upload))

# Construct a list 
def constructObjectListFromCSV(file, constrution_function):
    lock = FileLock(file + '.lock')
    lock.acquire()
    first_itr_flag = True

    with lock:
        if os.path.exists(file) and os.path.isfile(file):
            with open(file, 'r', newline='') as f:
                reader = csv.reader(f)
                return_objects = []
                
                for i in reader :
                    if not first_itr_flag: 
                        return_objects.append(constrution_function(i))
                    else: first_itr_flag = not first_itr_flag
                return return_objects

    lock.release()

# Construction function for a connectionStatus object from a csv file line.
def constructConnectionStatus(data: list) -> connection_status:
    return connection_status(data[0], data[1])

# Construction function for a speedtest_result object from a csv file line.
def constructSpeedtestResult(data: list) -> speedtest_result:
    return speedtest_result(data[0], data[1], data[2])

# Construct a list of connecitonStatus objects from the stored csv file.
def retrieveConnectionStatusData() -> list[connection_status]:
    return constructObjectListFromCSV('connection_status.csv', constructConnectionStatus)

# Construct a list of speedtest objects from the stored csv file.
def retrieveSpeedtestData() -> list[speedtest_result]:
    return constructObjectListFromCSV('speedtest_results.csv', constructSpeedtestResult)

# Take in the file
def imageFileToAttachment(filename: str):
    p = MIMEBase('application', 'octet-stream')

    p.set_payload(open(filename, 'rb').read())

    encoders.encode_base64(p)
    p.add_header('Content-Disposition', f'attachment; filename= {filename}.png')
    p.add_header('Content-ID', f'<{filename}>')

    return p

# Save the plot as a file and return the file name minus the extension.
def save_fig_to_file(plot, filename: str) -> str:
    plot.savefig(f'{filename}.png')
    return filename

# Construct the and return a MIMEMultipart email message.
def constructMessage(settings: Settings):
    
    connectionStatusData = retrieveConnectionStatusData()
    speedtestData = retrieveSpeedtestData()

    connectionStatusTimestamps = []
    connectionStatusResults = []

    speedtestResultTimestamps = []
    speedtestResultDownloads = []
    speedtestResultUploads = []

    for c in connectionStatusData:
        connectionStatusTimestamps.append(c.time)
        connectionStatusResults.append(c.connection_up)

    for s in speedtestData:
        speedtestResultTimestamps.append(s.time)
        speedtestResultDownloads.append(s.download)
        speedtestResultUploads.append(s.upload)
    
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
    <body>
        <div>
        <img src="cid:speed_test" alt="Speed test graph" />
        </div>
    </body>
    '''
    
    message.attach(MIMEText(message_body, 'html'))

    plot.plot(speedtestResultTimestamps, speedtestResultDownloads, label='Download Speed')
    plot.plot(speedtestResultTimestamps, speedtestResultUploads, label='Upload Speed')

    speedtestPlotImageFile = save_fig_to_file(plot, 'speed_test')
    message.attach(imageFileToAttachment(speedtestPlotImageFile))

    return message

# Send a passed MIMEMultipart email message.
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
