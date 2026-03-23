
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD


from time import sleep, strftime
from datetime import datetime

import RPi.GPIO as GPIO
import Freenove_DHT as DHT
import threading
import requests
import json
from datetime import date



#initialize GPIO
# #pin numbers
DHTPin = 26
DoorPin = 13
LightsPin =22
acLED = 18
HeatLED = 23
LightsLED = 24
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)


GPIO.setup(DoorPin, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(LightsPin, GPIO.IN, )
GPIO.setup(acLED, GPIO.OUT)
GPIO.setup(HeatLED, GPIO.OUT)
GPIO.setup(LightsLED, GPIO.OUT)


#threading stuff
screenlock = threading.Lock()
statelock = threading.Lock()


#constants
desired_temp = 80
tempupdown =3
FIRETEMP = 95


prev_HVAC = 0
curr_temp = desired_temp
humidity = 0
weather_index = 0
hvac = 0 # 0 = off, 1 = ac, 2 = heat
HVACmsg = ""
door = 0 # 0 = closed, 1 = open
lights = 0 #0 = off, 1 = on
fireExists = 0 # 0 = no fire, 1 = fire


#screen stuff
screen_type = 0 # 0 = main menu, 1 = interrupt
last_interrupt = 0
last_state = 0
intr_message = "test"
screenline1 = ""
screenline2 = ""

def updateScreen():
    global screen_type, last_state, intr_message, desired_temp, curr_temp, door, screenline1, screenline2
    global lcd, hvac, HVACmsg, last_interrupt, statelock, lights,LightsLED, HeatLED, acLED
    print("LCDthread started")
    screenline1 = "" + str(desired_temp) + "/" + str(int(curr_temp)) + "      Dr:"
    if (door == 1):
        screenline1 += "O"
    else:
        screenline1 += "C"
    HVACmsg = "H:OFF "
    screenline2 = HVACmsg + "     L:OFF"
    screenline1 = screenline1  +"\n" + screenline2
    
    #print("LCD:\n" + screenline1) #DEGUB

    screenlock.acquire()
    lcd.begin(16,2)
    #lcd.clear()
    lcd.setCursor(0,0)  # set cursor position
    lcd.message(screenline1)# display CPU temperature
    screenlock.release()


    while( True):
        statelock.acquire()
        print("updateScreen(): screen_type: %d"%(screen_type))
        #=======screen update section==================
        if (screen_type == 0): #USUAL SCREEN
            
            print("b")
            """ if (last_state == screen_type):
                continue """

            screenline1 = "" + str(desired_temp) + "/" + str(int(curr_temp)) + "      Dr:"
            if (door == 1):
                screenline1 += "O"
            else:
                screenline1 += "C"
            screenline2 = HVACmsg + "     L"
            if (lights == 0):
                screenline2 += ":OFF"
            else:
                screenline2 += ":ON "

            statelock.release()

            screenline1 = screenline1  +"\n" + screenline2
            
            print( screenline1) #DEGUB

            screenlock.acquire()
            #lcd.clear()
            lcd.setCursor(0,0)  # set cursor position
            lcd.message(screenline1)# display CPU temperature
            screenlock.release()

            sleep(0.5)

        #interrupt 
        elif (screen_type == 1):

            print("c")
            #print("updateScreen1 hvac: %d"%(hvac))            

            screenlock.acquire()
            last_interrupt = 1
            lcd.clear()
            lcd.setCursor(0,0)  # set cursor position
            lcd.message( intr_message)
            if (hvac == 1):
                #turn on acLED (blue)
                print("ac LED on")
                GPIO.output(acLED, GPIO.HIGH)
            elif(hvac == 2):
                #turn on HeatLED (red)
                print("heat LED on")
                GPIO.output(HeatLED, GPIO.HIGH)
            elif(hvac == 0):
                last_interrupt = 0
            screen_type = 0
            statelock.release()
            sleep (3)
            screenlock.release()
            

        #door
        elif(screen_type == 2):
            print("d")
            #turn off hvac
            print("updateScreen() door message" + intr_message)
            screenlock.acquire()
            last_interrupt = 2
            lcd.clear()
            lcd.setCursor(0,0)
            lcd.message(intr_message)
            #lcd.message("door")
            screen_type = 0
            statelock.release()
            sleep(3)
            screenlock.release()
        
        elif(screen_type == 3):
            #fire
            print("e")
            screenlock.acquire()
            last_interrupt = 3
            lcd.clear()
            lcd.setCursor(0,0)
            lcd.message(intr_message)
            statelock.release()
            sleep(0.5)
            screenlock.release()
        


        #statelock.release()
        #print("updatescreen release statelock")
            
        if (DHT.shutdown == True):
            print("lcdshutdown is true")
            break

        
        statelock.acquire()
        if (hvac == 0):
            #turn off heat and ac leds
            GPIO.output(acLED, GPIO.LOW)
            GPIO.output(HeatLED, GPIO.LOW)
        statelock.release()
        



def door_button(channel):
    global screen_type, hvac, door, intr_message, statelock, prev_HVAC
    statelock.acquire()
    print("\n\n\nbutton pressed\n\n\n")
    print("doorbuttonHVAC: %d"%(hvac))
    screen_type = 2
    if (door == 0): 
        door = 1
        prev_HVAC = hvac
        if (hvac > 0):
            intr_message = " Window/Door O\n HVAC HALTED"
            if (hvac == 1):
                GPIO.output(acLED, GPIO.LOW)
            if (hvac == 2):
                GPIO.output(HeatLED, GPIO.LOW)
        else:
            intr_message = " Window/Door O\n"
        #hvac = 0
        print("opening door")
    else: #door is open
        door = 0
        hvac = prev_HVAC
        #prev_HVAC = 0
        if prev_HVAC > 0:
            intr_message = " Window/Door C\n HVAC ON"
            if (prev_HVAC == 1):
                GPIO.output(acLED, GPIO.HIGH)
            if (prev_HVAC == 2):
                GPIO.output(HeatLED, GPIO.HIGH)
        else:
            intr_message = " Window/Door C"
        print("closing door")
    #sleep(0.2)
    statelock.release()

def lights_sensor(channel):
    global shutdown, LightsPin, LightsLED, lights, statelock
    idle_timeout = 10
    idle_interval = 0.1
    timer_count = 0
    print("Motionthread started")
    while (True):
        if GPIO.input(LightsPin) == GPIO.HIGH:
            GPIO.output(LightsLED, GPIO.HIGH)
            timer_count = 0
            statelock.acquire()
            lights = 1
            statelock.release()
            while(timer_count < idle_timeout/idle_interval):
                if (GPIO.input(LightsPin) == GPIO.HIGH):
                    timer_count = 0
                    if (DHT.shutdown == True):
                        print("lightsshutdown is true")
                        break
                    continue
                timer_count += 1
                sleep(idle_interval)
                if (DHT.shutdown == True):
                    print("lightsshutdown is true")
                    break

        if (DHT.shutdown == True):
            print("lightsshutdown is true")
            break
        #once out of loop, lights are idling
        GPIO.output(LightsLED, GPIO.LOW)
        statelock.acquire()
        lights = 0
        statelock.release()
        
        
        


def loop(): 
    global screen_type, curr_temp, dht, desired_temp, HVACmsg, intr_message,last_state
    global door, last_interrupt, hvac, base_url, humidity, fireExists, p
    #global DHThum, DHTtemp
    mcp.output(3,1)     # turn on LCD backlight
    lcd.begin(16,2)     # set number of LCD lines and columns

    hvac = 0
    HVACmsg = "H:OFF " 
    intr_message = "      HVAC\n      OFF"
    
    before_temp = desired_temp 

    while(True):  
        
        #last_state = screen_type 
        #DHT.lock.acquire()
        if (dht.DHT_avgtemp != 0):
            before_temp = dht.DHT_avgtemp
        #DHT.lock.release() #end reading data
        #now perform calculations on data
        curr_temp = before_temp + (0.05 * humidity)
        #print(before_temp)
        #print(curr_temp)
    
        firstiterFire = 1
        #-----------------------------------------------------------
        
        if (curr_temp >= FIRETEMP):
            statelock.acquire()
            screen_type = 3
            hvac = 0
            door = 1 # open doors
            fireExists = 1
            statelock.release()
            #flash the light at 1 second period
            if (firstiterFire == 1):
                p.start(50)
                firstiterFire = 0
            intr_message = "  FIRE DANGER\n Window/Door: O"
        elif(fireExists == 1): #turn off the fire
            statelock.acquire()
            #fireExists = 0
            door = 0
            #p.stop()
            statelock.release()
            intr_message = "  No Fire  \n Window/Door: C"
            sleep(1.5)
            statelock.acquire()
            screen_type = 0
            statelock.release()
            sleep(1)
            continue



        #if too hot
        statelock.acquire()
        #print("hvac: %d"%(hvac))
        #print("last_interrupt: %d"%(last_interrupt))
        if screen_type == 0:
            if (curr_temp >= desired_temp + tempupdown and door == 0  ):
                if (fireExists == 1):
                    fireExists = 0
                    intr_message = "  No Fire  \n Window/Door: C"
                    hvac = 1
                    HVACmsg = "H:AC  "
                    screen_type = 1
                    p.stop()
                    continue

                #print("too hot, ac on")
                #turn on hvac AC
                """ if (hvac == 1):
                    continue """
                hvac = 1
                HVACmsg = "H:AC  "
                intr_message = "      HVAC\n      AC"
                if (last_interrupt != 2 and last_interrupt != 1):
                    #interrupt!
                    screen_type = 1
            #if too cold
            elif (curr_temp <= desired_temp - tempupdown and door ==0 ):
                #turn on hvac HEAT
                #print("too cold, heat on")
                """ if (hvac == 2):
                    continue """
                hvac = 2
                HVACmsg = "H:HEAT"
                intr_message = "      HVAC\n      HEAT"
                if (last_interrupt != 2 and last_interrupt != 1):
                    #interrupt!
                    screen_type = 1
            elif( hvac != 0) : # and last_interrupt >= 1 changing from bad temp to good temp!
                #print("just right")
                hvac = 0
                HVACmsg = "H:OFF " 
                intr_message = "      HVAC\n      OFF"
                if(last_interrupt == 1):
                    screen_type = 1
                last_interrupt = 0
            else:
                #hvac == 0, nothing changes
                hvac = hvac

            
        #print("hvac loop releases")
        statelock.release()
        
        if (DHT.shutdown == True):
            return
        
        sleep(0.1)



        
def destroy():
    lcd.clear()
    mcp.output(3,0)
    



PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
# Create PCF8574 GPIO adapter.
try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print ('I2C Address Error !')
        exit(1)



# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)



#button process functions
GPIO.add_event_detect(DoorPin, GPIO.FALLING, callback=door_button, bouncetime=200)


#for humidity CIMIS
most_recent_value = 0 
today = str(date.today())
base_url = 'http://et.water.ca.gov/api/data?appKey=c862e0b6-3107-4484-90da-ecee38bb0228&targets=75&startDate=' + today + '&endDate=' + today + '&dataItems=hly-rel-hum'

GPIO.output(acLED, GPIO.LOW)
GPIO.output(HeatLED, GPIO.LOW)
GPIO.output(LightsLED, GPIO.LOW)

p = GPIO.PWM(LightsLED, 1)
#p.ChangeDutyCycle(50)

if __name__ == '__main__':
    global shutdown

    #dht = DHT.DHT(DHTPin)

    print ('Program is starting ... ')
    #sleep(0.25)
    dht = DHT.DHT(DHTPin)
    #start the DHT thread
    #DHTthread = threading.Thread(target = dht.readDHT11, args = ())
    DHTthread = threading.Thread(target = dht.readDHT11, args = ())
    DHTthread.start()
    LCDthread = threading.Thread(target = updateScreen, args = ())
    LCDthread.start()
    Motionthread = threading.Thread(target = lights_sensor, args = [LightsPin])
    Motionthread.start()

    
 

    
    #response = requests.get(base_url)
    #CIMIS stuff
    response = requests.get(base_url)
    if response.status_code == 200:
        posts = response.json()
        humidities = posts['Data']['Providers']
        for person in humidities:
            records = person['Records']
            for record in records:
                hlyhumidities = record['HlyRelHum']
                #print(hlyhumidities['Value'])
                if (hlyhumidities['Value'] == None ):
                    break
                else:
                    most_recent_value = hlyhumidities['Value']
            break     
    else:
        print("Failed to retrieve data. %d"%(response.status_code))
    humidity = int(most_recent_value)
    print("humidity: %d"%(humidity))
    
    if humidity == 0:
        humidity = 75


    try:
        loop()
    except KeyboardInterrupt:

        if (statelock.locked()):
            statelock.release()
        DHT.shutdown = True
        sleep(0.25)
        DHTthread.join()
        LCDthread.join()
        Motionthread.join()
        GPIO.cleanup()
        #sleep(1)
        destroy()


