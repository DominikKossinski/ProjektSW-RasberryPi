#!/usr/bin/python
from gpiozero import Buzzer
from time import sleep
import Adafruit_DHT
import RPi.GPIO as GPIO
import MFRC522
import signal
import mysql.connector
import threading

sem = threading.Semaphore()
buzzer = Buzzer(17)
sensor=Adafruit_DHT.DHT11
GPIO.setup(2, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(16, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(20, GPIO.OUT, initial=GPIO.LOW)
buzzer.on()
GPIO.output(2, GPIO.HIGH)
GPIO.output(16, GPIO.HIGH)
GPIO.output(20, GPIO.HIGH)
sleep(1)
buzzer.off()
GPIO.output(2, GPIO.LOW)
GPIO.output(16, GPIO.LOW)
GPIO.output(20, GPIO.LOW)
sleep(1)

def f(pin):
    alert()


def alert():
    for i in range(10):
        buzzer.on()
        GPIO.output(2, GPIO.HIGH)
        sleep(1)
        buzzer.off()
        GPIO.output(2, GPIO.LOW)
        sleep(1)
        
def chceckTestAlert(cur, db):
    while True:
        sem.acquire()
        cur.execute("SELECT flaga from flagi where nazwa = 'Próbny Alarm'")
        checkAlert = False
        for row in cur.fetchall():
            if(row[0] == 1):
                checkAlert = True;
        sem.release()
        if(checkAlert):
            print("Test alert");
            alert()
            sem.acquire()
            cur.execute("UPDATE flagi SET flaga = false where nazwa = 'Próbny Alarm'")
            db.commit()
            sem.release()
        sleep(1)

def collectMeasurements(cur, db):



    #Pin czujnika temperatury i wilgotnoścvi
    gpio=27 

    # Hook the SIGINT
    #signal.signal(signal.SIGINT, end_read)
    fireTemp = 30.0
    fireHum = 40.0
    slTime = 20
    while True:
        humidity, temperature = Adafruit_DHT.read_retry(sensor, gpio)
        if humidity is not None and temperature is not None:
            print('Temp={0:0.1f}*C  Humidity={1:0.1f}%\n'.format(temperature, humidity))
            sem.acquire()
            sqlStr = "INSERT INTO POMIARY(temperatura, wilgotność, data) values (%s, %s, NOW());" % (temperature, humidity)
            cur.execute(sqlStr)
            db.commit()
            sem.release()
        else:
            print('Failed to get reading. Try again!')
        if(temperature > fireTemp and humidity < fireHum):
            t = threading.Thread(target=alert)
            t.start()
        sleep(slTime)
       

def checkLogin(cur, db):
    logged = False
    # Create an object of the class MFRC522
    MIFAREReader = MFRC522.MFRC522()
    GPIO.output(16, GPIO.HIGH)
    GPIO.output(20, GPIO.LOW)
    while True:
        # Scan for cards    
        (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

        # If a card is found
        if status == MIFAREReader.MI_OK:
            print("Card detected")
        
        # Get the UID of the card
        (status,uid) = MIFAREReader.MFRC522_Anticoll()

        # If we have the UID, continue
        if status == MIFAREReader.MI_OK:
            sem.acquire()
            cur.execute("SELECT flaga from flagi where nazwa = 'Próbna Karta'")
            checkCart = False
            for row in cur.fetchall():
                if(row[0] == 1):
                    checkCart = True;
            sem.release()
            if(checkCart):
                print ("Card read UID: %s:%s:%s:%s" % (uid[0], uid[1], uid[2], uid[3]))
                sqlStr = "UPDATE FLAGI SET opis = '%s:%s:%s:%s'" % (uid[0], uid[1], uid[2], uid[3])
                sem.acquire()
                cur.execute(sqlStr)
                db.commit()
                sem.release()
            else:   
                logged = not logged
                # Print UID
                print ("Card read UID: %s:%s:%s:%s" % (uid[0], uid[1], uid[2], uid[3]))
                if logged:
                    sem.acquire()
                    sqlStr = "UPDATE UZYTKOWNICY SET ZALOGOWANY = TRUE WHERE RFID = '%s:%s:%s:%s'" % (uid[0], uid[1], uid[2], uid[3])
                    cur.execute(sqlStr)
                    db.commit()
                    sem.release()
                    GPIO.output(16, GPIO.LOW)
                    GPIO.output(20, GPIO.HIGH)
                    print("loggin")
                else:
                    sem.acquire()
                    cur.execute("UPDATE UZYTKOWNICY SET ZALOGOWANY = FALSE")
                    db.commit()
                    sem.release()
                    GPIO.output(16, GPIO.HIGH)
                    GPIO.output(20, GPIO.LOW)
                    print("logout")
        sleep(1)
            # This is the default key for authentication

GPIO.setup(3, GPIO.IN)
GPIO.add_event_detect(3, GPIO.RISING)
GPIO.add_event_callback(3, f)
db = mysql.connector.connect(host="192.168.1.103", user="rasberry",
                     passwd="rasberry123", db="projektSW",
                             auth_plugin='mysql_native_password')

cur = db.cursor()
threads = []
t = threading.Thread(target=checkLogin, args=(cur, db,))
threads.append(t)
t.start()

t = threading.Thread(target=collectMeasurements, args=(cur, db,))
threads.append(t)
t.start()

t = threading.Thread(target=chceckTestAlert, args=(cur, db,))
threads.append(t)
t.start()

sem.acquire()
cur.execute("SELECT * from pomiary")

for row in cur.fetchall():
   print(row)
sem.release()


while True:
    print("Loop")
    sleep(10)


    
        
GPIO.cleanup()