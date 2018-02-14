from picamera import PiCamera
from time import sleep

camera = PiCamera()

print 'Say cheese!'
camera.start_preview()
sleep(2)
camera.capture('/home/pi/Serena/tests/test_from_camera.jpg')
sleep(2)
print 'Saving picture'
camera.stop_preview()
