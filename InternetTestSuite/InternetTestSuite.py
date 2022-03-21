import time, smtplib, configparser, _thread, speedtest
from pythonping import ping
from email.message import EmailMessage

# If a ping to facebook or google make it though you have internet, otherwise you 
# either don't have internet or something very unusual is happening.
def checkConnection():
    if ((ping('facebook.com').success != False) or (ping('google.com').success != False)):
        return True
    else:
        return False

#Execute a speedTest and return the results in Mbit/s as a tuple (Download, Upload)
def speedTest():
    speedTest = speedtest.Speedtest()
    
    return (speedTest.download()/1000000, speedTest.upload()/1000000)




