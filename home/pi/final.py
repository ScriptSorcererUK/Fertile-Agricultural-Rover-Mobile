#Create a file for logging of the data
#This could be output to a web-page or onto a USB drive on the final version.
file = open("robotlog.txt", "w")
print("Starting the robot up")


#Makes writing to the file easier and makes each bit on it's own line
def writeToFile(text):
  file.write(str(text) + "\n")
  file.flush()


 #Imports needed to read/write to the pins
import RPi.GPIO as GPIO
import time

# import needed to pause
import board

#Needed to read the moisture and temperature
from adafruit_seesaw.seesaw import Seesaw

#needed to read from the GPD
import pynmea2, serial, time, io

#needed to read the light levels
import adafruit_bh1750


#How long to drive forwards for before taking a reading
move_time = 5
#How long to turn for to make it 90 degrees.
#For the real thing, it could use a compass to make sure it's not different on different surfaces.
turn_time = 1.5


###  SETUP  ###
GPIO.setwarnings(False)


#How fast the motors spin at (100% is FAST)
speed = 50


#setup the motor connections (using GPIO numbers, not board)
#Based on code from https://forums.raspberrypi.com/viewtopic.php?t=337421
motora = 13
motorb = 19
motorc = 18
motord = 12
GPIO.setmode(GPIO.BCM)
GPIO.setup(motora, GPIO.OUT)
pa = GPIO.PWM(motora, 1000)
GPIO.setup(motorb, GPIO.OUT)
pb = GPIO.PWM(motorb, 1000)
GPIO.setmode (GPIO.BCM)
GPIO.setup(motorc,GPIO.OUT)
pc = GPIO.PWM(motorc, 1000)
GPIO.setup(motord,GPIO.OUT)
pd = GPIO.PWM(motord, 1000)


#used to talk to the servo
#Using code from https://reefwingrobotics.blogspot.com/2017/02/raspberry-pi-and-towerpro-sg90-micro.html
servo_pin = 25
duty_cycle = 7.5
GPIO.setup(servo_pin, GPIO.OUT)
pwm_servo = GPIO.PWM(servo_pin, 50)
pwm_servo.start(duty_cycle)


#Setup the i2C to get data on moisture, temp and light
i2c = board.I2C()


#Setup to read the temp and moisture
#Based on code from https://cdn-learn.adafruit.com/downloads/pdf/adafruit-stemma-soil-sensor-i2c-capacitive-moisture-sensor.pdf
ss = Seesaw(i2c, addr=0x36)


#Setup to read the light
#Based on code from https://learn.adafruit.com/adafruit-bh1750-ambient-light-sensor/python-circuitpython
sensor = adafruit_bh1750.BH1750(i2c)


#Setup connection to read the GPS
#Based on code from https://github.com/Knio/pynmea2
serialPort = None
try:
  serialPort = serial.Serial("/dev/ttyAMA0", 9600, timeout=0.5)
  serialPort.close()
  serialPort.open()
except:
  print("Error when starting serial port")
  writeToFile("Error when starting serial port")


###  FUNCTIONS  ###

#Easily make the servo switch between different positions to put the moisture sensor in the ground.
#In the final version a linear actuator would be better, but they are very expensive.
def setServo(duty_cycle):
  # left = 5 and right = 10
  pwm_servo.ChangeDutyCycle(duty_cycle)


#Get data from the moisure and temperature sensor board using i2c
#In the final version a PH sensor would also be good to use, but they are expensive.
def getTempAndMoisture():
  touch = ss.moisture_read()
  temp = ss.get_temp()
  temp = round(temp, 2)
  print("temp: " + str(temp) + " moisture: " + str(touch))
  writeToFile("temp: " + str(temp) + " moisture: " + str(touch))


#Get data from the light sensor to see if there is good light for farming
def readLight():
  print("%.2f Lux" % sensor.lux)
  writeToFile("%.2f Lux".format(sensor.lux))


#Read the GPS location using the serial port GPIO pins
def getLocation():
  #Try 10 times to get the location, then give up
  counter = 0
  while counter < 10:
    try:
      #Read a line from the GPS via serial 
      line = serialPort.readline().strip().decode().strip()
      #Try to get the GPS data from the text (it might fail)
      msg = pynmea2.parse(str(line))
      #If it was able to get the location from the text...
      if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
        #Output the data to the terminal and the file
        print("Latitude:", msg.latitude)
        writeToFile("Latitude: " + str(msg.latitude))
        print("Longitude:", msg.longitude)
        writeToFile("Longitude: " + str(msg.longitude))
        #Leave the function as we got the data we need
        return
      #Used to give up after 10 attempts
      counter = counter + 1
    except serial.SerialException as e:
      #Try to fix the serial port if it's not working
      serialPort.close()
      serialPort.open()
      #Used to give up after 10 attempts
      counter = counter + 1
      continue
    except:
      #If anything else crashes we just try again
      #Used to give up after 10 attempts
      counter = counter + 1
  #This code will only run if it's tried 10 times and not succeeded
  print("Could not get location after 10 attempts")
  writeToFile("Could not get location after 10 attempts")


def moveForward():
  #telling both motors to move forwards
  print("Moving forwards")
  writeToFile("Moving forwards")
  pa.start(speed)
  pc.start(speed)


def stopMoving():
  #Stop all the motor signals in forward or back.
  pa.stop()
  pb.stop()
  pc.stop()
  pd.stop()


def turnLeft():
  #telling one motor to move forwards and the other backwards
  print("Turning left")
  writeToFile("Turning left")
  pa.start(speed)
  pd.start(speed)

def turnRight():
  print("Turning right")
  writeToFile("Turning right")
  #telling one motor to move backwards and the other forwards
  pb.start(speed)
  pc.start(speed)


#Call each of the functions to get location and moisture etc.
def get_data():
  getLocation()
  readLight()
  #Make the servo go down into the ground
  setServo(4)
  #Wait for the servo to go down
  time.sleep(2)
  getTempAndMoisture()
  #Make the servo go back up again before we drive off again
  setServo(10)
  time.sleep(1)



###  MAIN PROGRAM  ###


#set the servo to the up position before moving (10)
setServo(10)
#make sure the motors are not moving
stopMoving()
#delay before starting
time.sleep(30)

#It does part of the pattern five times to cover a whole grid
for i in range (5):
  #This moves forward and samples five times
  for i in range (5):
    moveForward()
    time.sleep(move_time)
    stopMoving()
    get_data()

  #Now turn right and move forward away from the start before sampling again
  turnRight()
  time.sleep(turn_time)
  stopMoving()

  moveForward()
  time.sleep(move_time)
  stopMoving()
  get_data()

  #Now turn right again to point back the way we came for the next part of the grid
  turnRight()
  time.sleep(turn_time)
  stopMoving()

  #This moves forward and samples five times driving back towards the start point, but along by 1 position
  for i in range (5):
    moveForward()
    time.sleep(move_time)
    stopMoving()
    get_data()
    #sample

  #Turn left instead of right to move along one more position before repeating part of the pattern
  turnLeft()
  time.sleep(turn_time)
  stopMoving()

  #Move forward one space away from the start and sample
  moveForward()
  time.sleep(move_time)
  stopMoving()
  get_data()
  #sample

  #Turn left again to make sure repeating the pattern will cover teh whole grid
  turnLeft()
  time.sleep(turn_time)
  stopMoving()

#Turn rigth twice to point back towards the start
turnRight()
time.sleep(turn_time)
turnRight()
time.sleep(turn_time)
stopMoving()

#Move back to the starting point
moveForward()
time.sleep(move_time * 5)
stopMoving()
print("Finished")
writeToFile("Finished")
file.close()

#FInished
GPIO.cleanup()