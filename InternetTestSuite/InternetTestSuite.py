from tabnanny import check
import time, smtplib, os, configparser, _thread, speedtest, ssl, csv
from pythonping import ping
from email.message import EmailMessage

config_folder = os.path.dirname(os.path.realpath(__file__))

#Setting class to handle the read and management of the config.ini file
class Settings:
    def __init__(self, folder_path):
        self.path = os.path.join(folder_path, 'config.ini').replace('\\','/')
        
        config = configparser.ConfigParser()
        with open(self.path, 'r', encoding='utf-8') as f:
            config.read_file(f)
            self.address = config['Email']['Address']
            self.password = config['Email']['Password']
            self.ping_frequency = config['Application Config'].getfloat('Pint Frequency')
            self.speedtest_frequency = config['Application Config'].getfloat('Speedtest Frequency')
            self.email_frequency = config['Application Config']['Log Frequency']
            self.email_day = config['Application Config']['Log Day']
            self.email_time = config['Application Config']['Log Time']
            
        
# If a ping to facebook or google make it though you have internet, otherwise you 
# either don't have internet or something very unusual is happening.
def checkConnection():
    timeStamp = time.time()
    if ((ping('facebook.com').success != False) or (ping('google.com').success != False)):
        return (timeStamp, True)
    else:
        return (timeStamp, False)

#Execute a speedTest and return the results in Mbit/s as a tuple (Download, Upload)
def speedTest():
    speedTest = speedtest.Speedtest()
    
    return (speedTest.download()/1000000, speedTest.upload()/1000000)

#Write the status of a connection check to the file
def writeConnectionStatus(status):
    created = False
    if (not os.path.exists('connection_status.csv')):
        created = True
    with open('connection_status', 'w+',newline='') as file:
        writer = csv.writer(file)
        if created is True: 
            writer.writerow(['Timestamp','Status'])
        writer.writerow(status)

def checkAndStoreConnectionStatus():
    writeConnectionStatus(checkConnection())
    

settings = Settings(config_folder)

context = ssl.create_default_context()

with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(settings.address, settings.password)

    server.sendmail(settings.address, 'test@testemail.com' , 'This is a test')
