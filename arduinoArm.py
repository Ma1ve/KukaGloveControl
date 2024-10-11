
from pyfirmata import Arduino, util
import time

class ServoController:

    def __init__(self, robot, port="COM8", servo_num=5 ):
        self.robot = robot
        self.port = port
        self.board = Arduino(self.port)
        self.servo_num = servo_num
    

        # Set up pins
        self.pins = [self.board.get_pin(f'a:{i}:i') for i in range(self.servo_num)]
        self.it = util.Iterator(self.board)
        self.it.start()

        # self.pause = 5

    def read_potentiometer(self, pin_index):
        pin = self.pins[pin_index]
        return pin.read()

    def convert_to_servo_value(self, value):
        return value 
    # int((value - self.adc_min) / (self.adc_max - self.adc_min) * (self.pwm_max - self.pwm_min) + self.pwm_min) 

    def control_servos(self):
       


        while True:
          time.sleep(2)

          thumbFingerSignal = self.pins[0].read()
          indexFingerSignal = self.pins[1].read()
          middleFingerSignal = self.pins[2].read()
          ringFingerSignal = self.pins[3].read()
          testFingerSignal = self.pins[4].read()

          if thumbFingerSignal is None or indexFingerSignal is None or middleFingerSignal is None or ringFingerSignal is None:
            continue
  
          thumbFinger = min(0.5, thumbFingerSignal) * 2 * 90
          indexFinger = min(0.5, indexFingerSignal) * 2 * 180
          middleFinger = min(0.5, middleFingerSignal) * 2 * 180 
          ringFinger= min(0.5, ringFingerSignal) * 2 * 180


          testFinger = min(0.5, testFingerSignal) * 2 * 180


          print(f'{thumbFinger:.3f} thumbFinger, {indexFinger:.3f} indexFinger, {middleFinger:.3f} middleFinger, {ringFinger:.3f} ringFinger')


          

          # if middleFinger < 1 and ringFinger < 1: 
          #     self.robot.move_arm(grip=2)  
          # else: 

          #  if (ringFinger < 1 and )

          self.robot.move_arm(m1=ringFinger, m2=middleFinger, m3=indexFinger, m4=thumbFinger, grip=0)

















          # thumbFinger = min(0.5, thumbFingerSignal) * 2 * 180 - 90
          # indexFinger = min(0.5, indexFingerSignal) * 2 * 360 - 180 
          # middleFinger = min(0.5, middleFingerSignal) * 2 * 360 - 180 
          # ringFinfer= min(0.5, ringFinferSignal) * 2 * 360 - 180 
