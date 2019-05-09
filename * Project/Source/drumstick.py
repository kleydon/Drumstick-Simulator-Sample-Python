#Drumstick Simulator
#
# An accelerometer-based drum stick simulator.
# (Work in progress...)
#
#
#
# To do:
#   * Look into interactive graphing.
#
#   * Low latency audio?
#
#   * Explore why volume is weird.
#
#   * Consider making volume a function of area under the curve, or number pegged at max
#		* Consider some filtering, up-front


#Imports
import serial
from pygame import mixer
import datetime
from numpy import *
import math
import matplotlib.pyplot as plt 


#Parameters
ABS_ACCEL_SLOPE_THRESHOLD = 0.18
MIN_CONSECUTIVE_SLOPES_ABOVE_THRESHOLD = 3
MAX_HIT_DURATION_SAMPLE_COUNT = 100
MIN_INTER_HIT_SAMPLE_COUNT= 400


#Buffer
#+++++++++++++++
BUFFER_LENGTH = MAX_HIT_DURATION_SAMPLE_COUNT*2

currentBufferIndex = 0

def prevBufferIndex():
	if (currentBufferIndex==0):
		return BUFFER_LENGTH-1
	return currentBufferIndex-1

def nextBufferIndex():
	if (currentBufferIndex==BUFFER_LENGTH-1):
		return 0
	return currentBufferIndex+1
	
def printBuffer():
	print "buffer:"
	i = nextBufferIndex()
	while True:
		print "\t %i   %0.2f   %0.2f" % (i, a[i], da[i])
		if i==currentBufferIndex:
			break
		i=i+1
		if (i==BUFFER_LENGTH-1):
			i = 0
	print " "
#---------------


#ASCII Hex->Int
#+++++++++++++++
def byteStringToInt(AsciiHexByte):
	u = int(AsciiHexByte, 16)
	if u > 127:
		return (256-u) * (-1)
	else:
		return u
#---------------


#Hit volume
#+++++++++++++++
def calcHitVolume():
	LOWER_LIM = 5.0
	UPPPER_LIM = MAX_ABS_ACCEL-80
	
	x = max(0, hitMaxAbsAccel-LOWER_LIM)
	v = x / (UPPPER_LIM-LOWER_LIM)
	print "LOWER_LIM:%0.2f    hitMaxAbsAccel:%0.2f    UPPER_LIM:%0.2f    Volume:%0.2f" % (LOWER_LIM, hitMaxAbsAccel, UPPPER_LIM, v)
	return v

def showHitVolume(v):
	s=""
	for i in range(0, int(hitMaxAbsAccel)): # ************
		s = s + "|"
	print s
#---------------


#State machine
#+++++++++++++++
STATE_WAITING_FOR_HIT = 0
STATE_FINALIZING = 1
STATE_POST_HIT_DELAY = 2

state = STATE_WAITING_FOR_HIT
#---------------


#Sample counters
#+++++++++++++++
totalSampleCount = 0
hitCount = 0
consecutiveSlopesAboveThresholdCount = 0
consecutiveAbsSlopesAboveThresholdCount = 0
hitDurationSampleCount = 0
interHitSampleCount = 0
#---------------


#Acceleration
#+++++++++++++++
#Constants
MAX_ABS_ACCEL = sqrt(127*127 + 127*127 + 127*127)
ACCEL_G = 62.0	#62.0 for 2G, 8bits - A FUNCTION OF SENSITIVITY

#Arrays
absAccel = array(zeros(BUFFER_LENGTH), dtype=float)
slope = array(zeros(BUFFER_LENGTH), dtype=float)
absSlope = array(zeros(BUFFER_LENGTH), dtype=float)

#Maximums
hitMaxAbsAccel = 0
hitMaxAbsSlope = 0
#---------------



#Set up serial comms
sio = serial.Serial('/dev/tty.usbmodem753371', 57600, timeout=1) #USB is always really 12 Mbit/sec (Teensyduino)
sio.flush()


#Set up audio
mixer.pre_init(22050, -16, 2, 256) #ensure a small buffeer size
mixer.init()
#audioFile = "/Users/krispin/Desktop/Krispins_Stuff/Projects/Hot/CollapsiblePan/Code/DrumTest2/DrumSound/data/snare.wav"
audioFile = "/Users/krispin/Desktop/Krispins_Stuff/Projects/Hot/CollapsiblePan/Code/DrumTest2/DrumSound/data/Steel-Drum-C4.wav"
alert=mixer.Sound(audioFile)
alert.set_volume(1.0)


#Get a start timestamp
tStart = datetime.datetime.now()


while True:
	
	line = sio.readline().strip()   # read a line, strip terminating char(s)
	#print line
			
	if len(line)!=8:
		x=0
		#print "Bad line: %s" % line
		
	else:

		#Samples/sec
		totalSampleCount += 1
		tNow = datetime.datetime.now()
		tDelta = tNow - tStart
		samplesPerSec = totalSampleCount/tDelta.total_seconds()
		#print "s/sec: %0.2f" % samplesPerSec
	
		#Parse line
		axStr = line[0:2]
		ayStr = line[2:4]
		azStr = line[4:6]
		csStr = line[6:8]
		#print "%s %s %s %s" % (axStr, ayStr, azSt, csStr)
		
		axRaw = byteStringToInt(axStr)
		ayRaw = byteStringToInt(ayStr)
		azRaw = byteStringToInt(azStr)
		calculatedChecksum = ((axRaw & 0xFF) + (ayRaw & 0xFF) + (azRaw & 0xFF)) & 0xFF
		receivedChecksum = byteStringToInt(csStr) & 0xFF
		
		if (calculatedChecksum != receivedChecksum):
			dummy=0
			#print "Bad checksum. Rx:%s"
			
		else:
		 
			#Acceleration		
			axRaw = float(axRaw)
			ayRaw = float(ayRaw)
			azRaw = float(azRaw)
			aRaw = sqrt(axRaw*axRaw + ayRaw*ayRaw + azRaw*azRaw)
			
			absAccel[currentBufferIndex] = 0.2*aRaw + 0.8*absAccel[prevBufferIndex()]
			#absAccel[currentBufferIndex] = aRaw
			
			#ACCEL_G = (.1*aRaw + .9*ACCEL_G)
			#absAccel[currentBufferIndex] = abs(aRaw-ACCEL_G)
			
			#print "%0.2f" % absAccel[currentBufferIndex]
			#print "%0.2f" % ACCEL_G
						
			#Slope
			slope[currentBufferIndex] = absAccel[currentBufferIndex] - absAccel[prevBufferIndex()]
			absSlope[currentBufferIndex] = abs(slope[currentBufferIndex])
			#print "%0.2f" % slope[currentBufferIndex]
						
			#State transitions
			if state==STATE_WAITING_FOR_HIT:
			
				#Update number of consecutive slopes above a given threshold
				if (slope[currentBufferIndex]>ABS_ACCEL_SLOPE_THRESHOLD):
					consecutiveSlopesAboveThresholdCount += 1
				else:
					consecutiveSlopesAboveThresholdCount = 0
				
				#Update number of consecutive ABSOLUTE slopes above given threshold
				if (absSlope[currentBufferIndex]>ABS_ACCEL_SLOPE_THRESHOLD):
					consecutiveAbsSlopesAboveThresholdCount += 1
				else:
					consecutiveAbsSlopesAboveThresholdCount = 0

				#If impact found...			
				#if (consecutiveAbsSlopesAboveThresholdCount > MIN_CONSECUTIVE_SLOPES_ABOVE_THRESHOLD):
				if (consecutiveSlopesAboveThresholdCount > MIN_CONSECUTIVE_SLOPES_ABOVE_THRESHOLD):

					#Reset the count
					consecutiveSlopesAboveThresholdCount = 0
					consecutiveAbsSlopesAboveThresholdCount = 0
				
					#Prepare to delay
					hitMaxAbsAccel = nanmax(absAccel) #ignore NaNs
					#print "\t hitMaxAbsAccel = %0.2f" % hitMaxAbsAccel
					hitMaxAbsSlope = absSlope[currentBufferIndex]
					#print "\t hitMaxAbsSlope = %0.2f" % hitMaxAbsSlope
					hitDurationSampleCount = 0
					state = STATE_FINALIZING
					
			elif state==STATE_FINALIZING:
				if (hitMaxAbsAccel < absAccel[currentBufferIndex]):
					hitMaxAbsAccel = absAccel[currentBufferIndex]
					#print "\t hitMaxAbsAccel = %0.2f" % hitMaxAbsAccel
				if (hitMaxAbsSlope < absSlope[currentBufferIndex]):
					hitMaxAbsSlope = absSlope[currentBufferIndex]
					#print "\t hitMaxAbsSlope = %0.2f" % hitMaxAbsSlope
				if hitDurationSampleCount >= MAX_HIT_DURATION_SAMPLE_COUNT:
					hitVolume = calcHitVolume()
					showHitVolume(hitVolume)
					#print "Hit #%d (s/sec: %0.2f)" % (hitCount, samplesPerSec)
					#print "maxAccel: %0.2f  maxSlope: %0.2f vol: %0.2f" % (hitMaxAbsAccel, hitMaxAbsSlope, hitVolume)
					alert.set_volume(hitVolume)
					alert.play()
					#print "\a"
					#printBuffer() 
					'''
					plt.subplot(3, 1, 1)
					plt.plot(absAccel, 'r.-')
					plt.subplot(3, 1, 2)
					plt.plot(slope,'r.-')
					plt.subplot(3, 1, 3)
					plt.plot(absSlope,'r.-')
					plt.show()
					'''
					hitCount += 1
					interHitSampleCount = 0
					state=STATE_POST_HIT_DELAY
				hitDurationSampleCount += 1
				
			elif state==STATE_POST_HIT_DELAY:
				interHitSampleCount +=1
				if (interHitSampleCount>MIN_INTER_HIT_SAMPLE_COUNT):
					state=STATE_WAITING_FOR_HIT
			
			
			#Increment buffer index
			currentBufferIndex = nextBufferIndex()
			
			
ser.close()