#!/usr/bin/python

import serial, time
from curses import ascii

modem=serial.Serial('/dev/ttyUSB0', 115200, timeout=4)
modem.write("AT\r\r\n")
time.sleep(2)
print modem.readline()
time.sleep(2)
modem.write("AT+CMGF=1\r\r\n")
time.sleep(2)
print modem.readline()
time.sleep(2)
modem.write("AT+CMGS='+18082341234'\r")
modem.write("Hi Ian\r")
modem.write(ascii.ctrl('z'))
time.sleep(2)
print modem.readline()
