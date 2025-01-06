import time
import pygame
from pyfirmata import Arduino, util

from ObjectTracker import ObjectTracker 
from memory_store import store 

class GloveServoController:

    def __init__(self, robot, port="COM8", servo_num=5 ):
        self.robot = robot
        self.port = port
        self.board = Arduino(self.port)
        self.servo_num = servo_num

        self.positionKuka = []

        self.isCameraRun = False
        self.tracker = ObjectTracker(robot, self.setIsCameraRun)
        # Set up pins
        self.pins = [self.board.get_pin(f'a:{i}:i') for i in range(self.servo_num)]

        self.it = util.Iterator(self.board)
        self.it.start()
        
        self.startRecord = False

        self.queue = []
        self.delay = 2

        self.grip = 0


    #? USE QUEUE
    def useQueue(self): 
       while (len(self.queue) != 0):
        time.sleep(int(3))
        
        fingers_signals = self.queue.pop(0)
  
        thumbFinger, indexFinger, middleFinger, ringFinger  = fingers_signals.values()

        print('QUEUE')
        print(f'{thumbFinger:.3f} thumbFinger, {indexFinger:.3f} indexFinger, {middleFinger:.3f} middleFinger, {ringFinger:.3f} ringFinger')

        self.robot.move_arm(m1=ringFinger, m2=middleFinger, m3=indexFinger, m4=thumbFinger, grip=0)

       self.setRecordStart(False)
    
    #? APPEND QUEUE
    def appendInQueue(self): 
        
        time.sleep(int(self.delay))

        print('Append in Queue')
        print(f'{self.thumbFinger:.3f} thumbFinger, {self.indexFinger:.3f} indexFinger, {self.middleFinger:.3f} middleFinger, {self.ringFinger:.3f} ringFinger')

        self.queue.append({
          'thumbFinger': self.thumbFinger,
          'indexFinger': self.indexFinger,
          'middleFinger': self.middleFinger,
          'ringFinger': self.ringFinger,
        })

        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {'queue_changed': True}))

        print(self.lengthQueue(), 'queue')

        time.sleep(1)
       
    
    def lengthQueue(self):
       return len(self.queue)
      
    def setIsCameraRun(self, boolean):
       self.isCameraRun = boolean
  
    def setRecordStart(self, boolean):
        if boolean:
          print('Record Start:')
        else: 
          print('Record stop setRecordStart')
        self.startRecord = boolean

    def getRecordStart(self):
       return self.startRecord
    

    def control_servos(self):
        
        time.sleep(0.1)
   
        thumbFingerSignal = self.pins[0].read()
        indexFingerSignal = self.pins[1].read()
        middleFingerSignal = self.pins[2].read()
        ringFingerSignal = self.pins[3].read()

        self.thumbFinger = min(0.5, thumbFingerSignal) * 2 * 90
        self.indexFinger = min(0.5, indexFingerSignal) * 2 * 180
        self.middleFinger = min(0.5, middleFingerSignal) * 2 * 180 
        self.ringFinger= min(0.5, ringFingerSignal) * 2 * 180

        if self.startRecord == False:
          
          if (self.isCameraRun): 
              print('Init')

              self.positionKuka = [self.thumbFinger]

              self.tracker.setCameraRun(True)
              self.tracker.run(self.positionKuka)
           
          else: 
            valueFingers = [int(signal) for signal in [self.thumbFinger, self.indexFinger, self.middleFinger, self.ringFinger]]
            sumFingers =  sum(valueFingers)

            # Check whether such coordinates already exist in the dictionary.
            if sumFingers not in store:
                store[sumFingers] = valueFingers  # Adding new data to the dictionary

            # Saving the updated store to memory_store.py
            with open('memory_store.py', 'w') as file:
                file.write('store = {\n') 
                for key, value in store.items():
                    file.write(f'    {key}: {value},\n') 
                file.write('}\n')  
                file.close()  

            print(f'{self.thumbFinger:.3f} thumbFinger, {self.indexFinger:.3f} indexFinger, {self.middleFinger:.3f} middleFinger, {self.ringFinger:.3f} ringFinger')
          
            if (self.thumbFinger > 50):
               self.grip = 1
            else:
               self.grip = 0
        
            self.robot.move_arm(m1=self.ringFinger, m2=self.middleFinger, m3=self.indexFinger, m4=self.thumbFinger, grip=2)
      
            if (len(self.queue)):
              self.useQueue()    
           
        else:
         self.appendInQueue()

         
         

          

       

       

    
       

    







