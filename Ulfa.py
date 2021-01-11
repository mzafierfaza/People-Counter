import numpy as np 
import imutils
import cv2
import math
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os.path
import time, threading
avg = None

email = 'XXXXXXXXXXXXXXXX@gmail.com'
password = 'XXXXXXXXXXX'
send_to_email = 'XXXXXXXXXXXXX@gmail.com'
subject = 'People Counter Report!'
messageIn = 'Hai XXX, Seseorang telah memasuki ruangan'
messageOut = 'Hai XXX, Seseorang telah keluar dari ruangan'
file_location = 'object.jpg'

video = cv2.VideoCapture("rtsp://192.168.XXX.XXX:554/unicast")

width = 0
height = 0
EntranceCounter = 0
ExitCounter = 0
MinCountourArea = 3000  #Adjust ths value according to your usage
BinarizationThreshold = 100   #70  #Adjust ths value according to your usage
OffsetRefLines = 120  #Adjust ths value according to your usage

#Check if an object in entering in monitored zone
def CheckEntranceLineCrossing(y, CoorYEntranceLine, CoorYExitLine):
    AbsDistance = abs(y - CoorYEntranceLine)	
    if ((AbsDistance <= 2) and (y < CoorYExitLine)):
        return 1
    else:
    	return 0

#Check if an object in exitting from monitored zone
def CheckExitLineCrossing(y, CoorYEntranceLine, CoorYExitLine):
    AbsDistance = abs(y - CoorYExitLine)	
    if ((AbsDistance <= 2) and (y > CoorYEntranceLine)):
        return 1
    else:
        return 0

def setup_email():
    global msg
    global msg2
    global filename
    global attachment
    global part
    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = send_to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(messageIn, 'plain'))

    msg2 = MIMEMultipart()
    msg2['From'] = email
    msg2['To'] = send_to_email
    msg2['Subject'] = subject
    msg2.attach(MIMEText(messageOut, 'plain'))

    #Setup the attachment
    filename = os.path.basename(file_location)
    attachment = open(file_location, "rb")
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    # Attach the attachment to the MIMEMultipart object
    msg.attach(part)
    msg2.attach(part)


def kirim_email(param):
    global server
    global text
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email, password)
    if param == "masuk":
        text = msg.as_string()
        server.sendmail(email, send_to_email, text)
    elif param == "keluar":
        text = msg2.as_string()
        server.sendmail(email, send_to_email, text)

    server.quit()

    
while True:
    QttyOfContours = 0
    ret, frame = video.read()
    height = np.size(frame,0)
    width = np.size(frame,1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    if avg is None:
        print ("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        continue
    
    cv2.accumulateWeighted(gray, avg, 0.5)  #Memperbarui rata-rata berjalan. Fungsi menghitung jumlah tertimbang dari gambar input src dan akumulator dst sehingga dst menjadi rata-rata berjalan dari urutan bingkai
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))  #Menghitung perbedaan absolut per-elemen antara dua array atau antara array dan skalar.  
    thresh = cv2.threshold(frameDelta, 5, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    (_, cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


    #plot reference lines (entrance and exit lines) 
    CoorYEntranceLine = (height / 2)-OffsetRefLines
    CoorYExitLine = (height / 2)+OffsetRefLines
    cv2.line(frame, (0,int(CoorYEntranceLine)), (int(width),int(CoorYEntranceLine)), (255, 0, 0), 2)
    cv2.line(frame, (0,int(CoorYExitLine)), (int(width),int(CoorYExitLine)), (0, 0, 255), 2)
    cv2.putText(frame, "Entrances: {}".format(str(EntranceCounter)), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (250, 0, 1), 2)
    cv2.putText(frame, "Exits: {}".format(str(ExitCounter)), (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    for c in cnts:
        if cv2.contourArea(c) < 5000:
            continue
        (x, y, w, h) = cv2.boundingRect(c)
        QttyOfContours = QttyOfContours+1   
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 250, 25), 2)
        CoordXCentroid = (x+x+w)/2
        CoordYCentroid = (y+y+h)/2
        ObjectCentroid = (CoordXCentroid,CoordYCentroid)
        cv2.circle(frame, (int(CoordXCentroid), int(CoordYCentroid)), 3, (255, 255, 255), 5)
        cv2.line(frame, (0,240), (int(CoordXCentroid), int(CoordYCentroid)), (0, 255, 0), 1)

        if (CheckEntranceLineCrossing(CoordYCentroid,CoorYEntranceLine,CoorYExitLine)):
            EntranceCounter += 1
            cv2.imwrite('object.jpg',frame)
            print('People In')
            setup_email()
            kirim_email("masuk")
            
        if (CheckExitLineCrossing(CoordYCentroid,CoorYEntranceLine,CoorYExitLine)):  
            ExitCounter += 1
            cv2.imwrite('object.jpg',frame)
            print('People Out')
            setup_email()
            kirim_email("keluar")

    cv2.imshow("Frame",frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    
video.release()
cv2.destroyAllWindows()
