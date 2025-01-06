""" 
This code sets up a color filter to process the image from the robot's camera. 
It allows for adjusting the color range dynamically to more accurately detect objects based on their color. 
I used this to find a more precise color range for my objects, improving their recognition and enabling more accurate actions based on the detected colors.
"""
from KUKA import KUKA

import cv2
import numpy as np

robot = KUKA('192.168.88.25', camera_enable=True)

import cv2

if __name__ == '__main__':
    def nothing(*arg):
        pass

cv2.namedWindow( "result" ) # creating the main window
cv2.namedWindow( "settings" ) # creating a settings window

cap = cv2.VideoCapture(0)
# creating 6 sliders to adjust the initial and final color of the filter
cv2.createTrackbar('h1', 'settings', 0, 255, nothing)
cv2.createTrackbar('s1', 'settings', 0, 255, nothing)
cv2.createTrackbar('v1', 'settings', 0, 255, nothing)
cv2.createTrackbar('h2', 'settings', 255, 255, nothing)
cv2.createTrackbar('s2', 'settings', 255, 255, nothing)
cv2.createTrackbar('v2', 'settings', 255, 255, nothing)
crange = [0,0,0, 0,0,0]

while True:
    
    img = robot.camera()

    # flag, img = cap.read()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV )
 
    # reading the values of the sliders
    h1 = cv2.getTrackbarPos('h1', 'settings')
    s1 = cv2.getTrackbarPos('s1', 'settings')
    v1 = cv2.getTrackbarPos('v1', 'settings')
    h2 = cv2.getTrackbarPos('h2', 'settings')
    s2 = cv2.getTrackbarPos('s2', 'settings')
    v2 = cv2.getTrackbarPos('v2', 'settings')

    # form the initial and final color of the filter
    h_min = np.array((h1, s1, v1), np.uint8)
    h_max = np.array((h2, s2, v2), np.uint8)

    # apply a filter to the frame in the HSV model
    thresh = cv2.inRange(hsv, h_min, h_max)

    cv2.imshow('result', thresh) 
 
    ch = cv2.waitKey(5)
    if ch == 27:
        break

cap.release()
cv2.destroyAllWindows()
