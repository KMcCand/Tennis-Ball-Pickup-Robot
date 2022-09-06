from collections import deque
from imutils.video import VideoStream
import numpy as np
import argparse
import cv2
import imutils
import time
import RPi.GPIO as G


# define the lower and upper boundaries of the "green"
# ball in the HSV color space, then initialize the
# list of tracked points
greenLower = (29, 86, 6)
greenUpper = (64, 255, 255) 

# number of frames to grab at beginning
SAVE_FRAME_LIMIT = 100000
# program saves  one frame in every frame_divider frames, ie the larger frame divider is the more time between frames
FRAMES_BETWEEN_SNAPSHOTS = 10000

# limiting the bot fps to keep pi from overheating
RATE_LIMIT_FPS = 10

# time in seconds between when the ball goes off the near end of the camera to when it gets scooped up
BALL_SCOOP_TIME_SECS = 3

# A is bot left motor controller pins, B is bot right motor controller pins. Pins are numbered 1 through 4 increasing left to right.
A1 = 35
A2 = 37
B1 = 24
B2 = 32
B3 = 12
B4 = 18


def setup_pins():
    G.setmode(G.BOARD)
    G.setup(A1, G.OUT)
    G.setup(A2, G.OUT)
    G.setup(B1, G.OUT)
    G.setup(B2, G.OUT)
    G.setup(B3, G.OUT)
    G.setup(B4, G.OUT)
    
def left_forward():
    G.output(B4, G.HIGH)
    G.output(B3, G.LOW)

def right_forward():
    G.output(A1, G.LOW)
    G.output(A2, G.HIGH)

def left_stop():
    G.output(B4, G.LOW)
    G.output(B3, G.LOW)

def right_stop():
    G.output(A2, G.HIGH)
    G.output(A1, G.HIGH)
    
def left_backward():
    G.output(B3, G.HIGH)
    G.output(B4, G.LOW)

def right_backward():
    G.output(A2, G.LOW)
    G.output(A1, G.HIGH)

def bot_forward():
    left_forward()
    right_forward()

def bot_stop():
    left_stop()
    right_stop()

def turn_left():
    right_forward()
    left_stop()

def turn_right():
    left_forward()
    right_stop()

def left_circle():
    left_backward()
    right_forward()

def belt_intake():
    G.output(B1, G.LOW)
    G.output(B2, G.HIGH)

def belt_outake():
    G.output(B2, G.LOW)
    G.output(B1, G.HIGH)

def belt_stop():
    G.output(B1, G.HIGH)
    G.output(B2, G.HIGH)

def int_time():
    return int(time.time())

def check_for_ball(cnts, radius):
    # not a ball if there are no contours
    if len(cnts) ==  0:
        return False
    
    # not a ball if radius too large
    if radius > 100:
        return False

    # not a ball if not a circle
    if cv2.minEnclosingCircle(max(cnts, key=cv2.contourArea))[1]  - cv2.minEnclosingCircle(min(cnts, key=cv2.contourArea))[1] > 10:
        print("Kyle's sketchy circle algorithm says this is not a circle")
        return False

    return True


def run_video_loop(vs):
    ball_in_view = False
    ball_is_close = False
    force_bot_forward_secs = None
    
    radius = 0
    frame_count = 0

    # number of frames in the last second
    fps_count = 0
    old_time_int = int_time()

    last_frame_time = time.time()
    
    # keep looping
    while True:
        current_time = time.time()

        # rate limit for fps
        sleep_time_secs = 1 / RATE_LIMIT_FPS - (current_time - last_frame_time)
        if sleep_time_secs > 0:
            time.sleep(sleep_time_secs)
            last_frame_time = time.time()
        
        frame_count += 1
        fps_count += 1

        current_int_time = int_time()

        # counting fps
        if current_int_time != old_time_int:
            print(f"fps is: {fps_count}")
            old_time_int = current_int_time    
            fps_count = 0
    
        if force_bot_forward_secs is not None:
            # a ball must have disappeared off the near end of the camera within the last BALL_SCOOP_TIME_SECS
            if time.time() > force_bot_forward_secs:
                force_bot_forward_secs = None        
        
	# grab the current frame
        frame = vs.read()

        # save the first 5 frames as .jpg
        if frame_count < SAVE_FRAME_LIMIT and frame_count % FRAMES_BETWEEN_SNAPSHOTS == 0:
            cv2.imwrite("Frame%d.jpg" % frame_count, frame)
        
        # resize the frame, blur it, and convert it to the HSV
        # color space
        frame = imutils.resize(frame, width=600)
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # construct a mask for the color "green", then perform
        # a series of dilations and erosions to remove any small
        # blobs left in the mask
        mask = cv2.inRange(hsv, greenLower, greenUpper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        center = None

        if check_for_ball(cnts, radius) == True:
            ball_in_view = True

            # find the largest contour in the mask, then use
            # it to compute the minimum enclosing circle and
            # centroid
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            if center[0] < 100:
                ball_is_close = True
            
            if center[1] < 150:
                turn_left()
            elif center[1] > 300:
                turn_right()
            else:
                bot_forward()
                
            # only proceed if the radius meets a minimum size
            if radius > 30:
                belt_intake()
                
                # draw the circle and centroid on the frame,
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)

                
        elif ball_in_view and ball_is_close:
            ball_in_view = False
            ball_is_close = False
            
            bot_forward()
            belt_intake()
            force_bot_forward_secs = time.time() + BALL_SCOOP_TIME_SECS
                    
        elif force_bot_forward_secs is None:
            ball_in_view = False
            belt_stop()
            left_circle()

        # show the frame to our screen
        # cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF


def main():
    setup_pins()

    bot_stop()
    belt_stop()

    # grab the reference to the webcam
    vs = VideoStream(src=0).start()

    # allow the camera or video file to warm up
    time.sleep(2.0)

    try:
        run_video_loop(vs)
    finally:
        bot_stop()
        belt_stop()
        vs.stop()

        # close all windows
        cv2.destroyAllWindows()

    
if __name__ == '__main__':    
    main()
