#!/usr/bin/python

import argparse,redis,signal,time,ConfigParser,sys,os,ast,subprocess,grovepi,grove_rgb_lcd
from grove_rgb_lcd import *
from config_functions import *

# Define Globals
site_uuid=0


# define colors for LCD Background
lcd_background_color = {
	'red': {'red': 255, 'green': 0, 'blue': 0},
	'green': {'red': 0, 'green':255, 'blue': 0},
	'blue': {'red': 0, 'green': 0, 'blue': 255},
	'white': {'red': 255, 'green': 255, 'blue': 255},
	'yellow': {'red': 255, 'green': 130, 'blue': 0},
	'purple': {'red': 128, 'green': 0, 'blue': 128}}


def do_reboot():
	setText("Rebooting\nPlease Wait")
	from subprocess import call
	call("sudo reboot", shell=True)


def reset(allDone=0):
        setText("Exiting")
        for i in range(0,255):
                setRGB(255-i,0,0)
        setText("")
	if allDone:
	        sys.exit()


def update_screen_color(color='green'):

	set_lcd_background_color(color)




def set_lcd_background_color(color='green'):
	global lcd_background_color
	setRGB(lcd_background_color[color]['red'],lcd_background_color[color]['green'],lcd_background_color[color]['blue'])




def get_args():
	global site_uuid

	# Assign description to the help doc
	parser = argparse.ArgumentParser(
			description='Serena Update Configuration.')
	# Add arguments
	parser.add_argument('-S', '--site_uuid', type=str, help='site_uuid value', required=True)
	# Array for all arguments passed to script
	args = parser.parse_args()
	# Assign args to variables
	site_uuid = args.site_uuid
	# Nothing to return since we switched to globals


def start_up():

	setText("")
	place = 0
	for i in range(0,255):
		setRGB(i,i,i)
		char_pos_float = i / 6.5
		char_pos = "%d" %char_pos_float
		if int(char_pos) > place:
			setText_norefresh(chr(85)*int(char_pos))
			place = int(char_pos)
	setText("Updating\nConfiguration")
	time.sleep(2)


def doLoop():
	while True:
		try:
			is_valid_site=check_valid_site(site_uuid)
			print 'Is valid site? %s'% is_valid_site
			if is_valid_site:
				if not write_config_no_update_required(site_uuid):
					setRGB(0,255,0)
					setText("Written Conf\nOK")
					time.sleep(3)
					setText("Rebooting\nPlease Wait")
					from subprocess import call
					call("sudo reboot", shell=True)
					reset(1)
				else:
					setRGB(255,0,0)
					setText("!ERROR Writing!")
					time.sleep(3)
					reset(1)
			else:
				print 'Not a valid site_uuid! %s'% site_uuid
				setText('Invalid Site!\n%s'% site_uuid)
				time.sleep(5)
				reset(1)
		except IOError:
			print "Error"
		except KeyboardInterrupt:
			print "Exit requested"
			reset(1)
		except SystemExit:
			print "System Exit requested"
			reset(1)
		except TypeError:
			print "Type Error!"

def sigterm_handler(signum, frame):
        print >> sys.stderr, "Exit received"
        sys.exit(0)

# Bind our callback to the SIGTERM signal
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
	get_args()
	start_up()
	doLoop()
