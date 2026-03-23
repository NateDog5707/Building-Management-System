#!/usr/bin/env python3
#############################################################################
# Filename    : Freenove_DHT.py
# Description :	DHT Temperature & Humidity Sensor library for Raspberry
# Author      : freenove
# modification: 2020/10/16
########################################################################
import RPi.GPIO as GPIO
import time
import threading


shutdown = False
awesome = 0
lock = threading.Lock()
first = 1


class DHT(object):
	DHThum = 0
	DHTtemp = 0
	DHT_avgtemp = 0
	DHT_recent_temps = [0]

	DHTLIB_OK = 0
	DHTLIB_ERROR_CHECKSUM = -1
	DHTLIB_ERROR_TIMEOUT = -2
	DHTLIB_INVALID_VALUE = -999
	
	DHTLIB_DHT11_WAKEUP = 0.020#0.018		#18ms
	DHTLIB_TIMEOUT = 0.001			#100us
	
	humidity = 0
	temperature = 0
	
	def __init__(self,pin):
		self.pin = pin
		self.bits = [0,0,0,0,0]
		GPIO.setmode(GPIO.BCM)
	#Read DHT sensor, store the original data in bits[]	
	def readSensor(self,pin,wakeupDelay):
		mask = 0x80
		idx = 0
		self.bits = [0,0,0,0,0]
		# Clear sda
		GPIO.setup(pin,GPIO.OUT)
		GPIO.output(pin,GPIO.HIGH)
		time.sleep(0.5)
		# start signal
		GPIO.output(pin,GPIO.LOW)
		time.sleep(wakeupDelay)
		GPIO.output(pin,GPIO.HIGH)
		# time.sleep(0.000001)
		GPIO.setup(pin,GPIO.IN)
		
		loopCnt = self.DHTLIB_TIMEOUT
		# Waiting echo
		t = time.time()
		""" while True:
			if (GPIO.input(pin) == GPIO.LOW):
				break
			if((time.time() - t) > loopCnt):
				return self.DHTLIB_ERROR_TIMEOUT  """
		# Waiting echo low level end
		t = time.time()
		while(GPIO.input(pin) == GPIO.LOW):
			if((time.time() - t) > loopCnt):
				#print ("Echo LOW")
				return self.DHTLIB_ERROR_TIMEOUT
		# Waiting echo high level end
		t = time.time()
		while(GPIO.input(pin) == GPIO.HIGH):
			if((time.time() - t) > loopCnt):
				#print ("Echo HIGH")
				return self.DHTLIB_ERROR_TIMEOUT
		for i in range(0,40,1):
			t = time.time()
			while(GPIO.input(pin) == GPIO.LOW):
				if((time.time() - t) > loopCnt):
					#print ("Data Low %d"%(i))
					return self.DHTLIB_ERROR_TIMEOUT
			t = time.time()
			while(GPIO.input(pin) == GPIO.HIGH):
				if((time.time() - t) > loopCnt):
					#print ("Data HIGH %d"%(i))
					return self.DHTLIB_ERROR_TIMEOUT		
			if((time.time() - t) > 0.00005):	
				self.bits[idx] |= mask
			#print("t : %f"%(time.time()-t))
			mask >>= 1
			if(mask == 0):
				mask = 0x80
				idx += 1	
		#print (self.bits)
		GPIO.setup(pin,GPIO.OUT)
		GPIO.output(pin,GPIO.HIGH)
		return self.DHTLIB_OK
	#Read DHT sensor, analyze the data of temperature and humidity



	def readDHT11Once(self):
		#lock.acquire()
		#print("%d and %d"%(self.humidity , self.temperature))
		rv = self.readSensor(self.pin,self.DHTLIB_DHT11_WAKEUP)
		#print("%d and %d"%(self.humidity , self.temperature))
		#lock.release()
		#print("rv = %d"%(rv))
		if (rv is not self.DHTLIB_OK):
			self.humidity = self.DHTLIB_INVALID_VALUE
			self.temperature = self.DHTLIB_INVALID_VALUE
			return rv 
		
		self.humidity = self.bits[0]
		self.temperature = self.bits[2] + self.bits[3]*0.1
		sumChk = ((self.bits[0] + self.bits[1] + self.bits[2] + self.bits[3]) & 0xFF)
		if(self.bits[4] is not sumChk):
			return self.DHTLIB_ERROR_CHECKSUM
		
		
		return self.DHTLIB_OK
	


	def readDHT11(self):
		global first
		hi = self
		result = self.DHTLIB_INVALID_VALUE
		#self.runDHT11()
		#celcius_avg 
		print("DHTthread started")
		
		while True:
			result = self.readDHT11Once()
			print("E %f"%(self.temperature))
			if (self.humidity != -999 and self.temperature  != -999):
				if (first == 1):
					self.DHT_recent_temps.append(self.temperature)
					self.DHT_recent_temps.append(self.temperature)
					self.DHT_recent_temps.append(self.temperature)
					self.DHT_recent_temps.append(self.temperature)
					self.DHT_recent_temps.pop(0)
					self.DHT_recent_temps.append(self.temperature)
					first = 0
					celcius_avg = self.temperature
				elif(celcius_avg + 5 > self.temperature and celcius_avg -5 < self.temperature):
					self.DHT_recent_temps.pop(0)
					self.DHT_recent_temps.append(self.temperature)
				else:
					continue
				print("read temp: %f"%(self.temperature))
				lock.acquire()
				self.DHT_avgtemp = ((self.DHT_recent_temps[0] + self.DHT_recent_temps[1] + self.DHT_recent_temps[2] + self.DHT_recent_temps[3]+ self.DHT_recent_temps[4])/ 5)
				celcius_avg = self.DHT_avgtemp
				self.DHT_avgtemp = (self.DHT_avgtemp * 9 / 5) + 32 + 0.5
				#self.DHTtemp = self.temperature
				#self.DHThum = self.humidity
				lock.release()
				#print("\n Humidity: %2f, Temp: %2f \n"%(self.DHThum, self.DHTtemp))
				print("Avgtemp: %f"%(self.DHT_avgtemp))
			#print(result)
			time.sleep(0.01)

			if (shutdown == True):
				print("dhtshutdown is true")
				break
			
			
		
		


		
		
def loop():
	dht = DHT(26)
	sumCnt = 0
	okCnt = 0
	while(True):
		sumCnt += 1
		chk = dht.readDHT11()	
		if (chk == 0):
			okCnt += 1		
		okRate = 100.0*okCnt/sumCnt;
		print("sumCnt : %d, \t okRate : %.2f%% "%(sumCnt,okRate))
		print("chk : %d, \t Humidity : %.2f, \t Temperature : %.2f "%(chk,dht.humidity,dht.temperature))
		time.sleep(3)		
		
if __name__ == '__main__':
	print ('Program is starting ... ')
	try:
		loop()
	except KeyboardInterrupt:
		pass
		exit()		
		
		
