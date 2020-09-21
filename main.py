def left_forward():
    G.output(18, G.HIGH)

def right_forward():
    G.output(35, G.LOW)

def left_stop():
    G.output(18, G.LOW)
    G.output(12, G.LOW)

def right_stop():
    G.output(37, G.HIGH)
    G.output(35, G.HIGH)
    
def left_backward():
    G.output(12, G.HIGH)

def right_backward():
    G.output(37, G.LOW)

def bot_forward():
    left_forward()
    right_forward()

def turn_left():
    right_forward()
    left_stop()

def turn_right():
    left_forward()
    right_stop()

def belt_intake():
    G.output(24, G.LOW)

def belt_outake():
    G.output(32, G.LOW)

def stop_belt():
    G.output(24, G.HIGH)
    G.output(32, G.HIGH)
