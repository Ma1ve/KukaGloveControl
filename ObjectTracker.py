import cv2
import numpy as np

import time


class ObjectTracker:
    def __init__(self, robot, setIsCameraRun):
        self.robot = robot
        self.setIsCameraRun = setIsCameraRun
        self.width = 640
        self.height = 480
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        self.circle_radius = 50

        self.isCameraInitial = True 


        self.lower_blue = np.array([0, 100, 135])
        self.upper_blue = np.array([255 ,255, 255])

        self.isCameraRun = False

     

        self.posY = 0
        self.posX = 130

    def process_frame(self):
        
       
        img = self.robot.camera()

        # Перевод изображения в цветовое пространство HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Маска для выделения диапазона цветов
        mask = cv2.inRange(hsv, self.lower_blue, self.upper_blue)
        # Наложение маски, нахождение контуров объектов на изображении
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)



        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 200:  # Исключаем маленькие контуры
                x, y, w, h = cv2.boundingRect(contour)
                if w > 150 and h > 150: 
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    fx, fy = x + w // 2, y + h // 2
                    pos = [fx, fy]

                    

                    distance_to_center_x = fx - self.center_x  # Расстояние до центра по оси x
                    distance_to_center_y = fy - self.center_y  # Расстояние до центра по оси y


                    direction_text = f"{distance_to_center_x} --- {distance_to_center_y}"

                    distance_to_center = np.sqrt((fx - self.center_x) ** 2 + (fy - self.center_y) ** 2)
                    if distance_to_center <= self.circle_radius:
                        cv2.circle(img, (self.center_x, self.center_y), self.circle_radius, (0, 255, 0), 2)  # Зеленый круг
                        direction_text = "CENTER"
                    else:
                        cv2.circle(img, (self.center_x, self.center_y), self.circle_radius, (0, 0, 255), 2)  # Красный круг


                        if fx < self.center_x - 50:
                            direction_text += "LEFT "
    
                            self.posX += 1
                            self.robot.move_arm(m1=self.posX)
                            print('left')
                   
                     
                        elif fx > self.center_x + 50:
                            direction_text += "RIGHT "

                            self.posX -= 1
                            self.robot.move_arm(m1=self.posX)
                            print(self.posX)
                            print('right')
                       
                        else: 
                     
                          
                          if fy < self.center_y:
                              direction_text += "UP"
                              
                              self.posY -= 2
                              self.robot.move_arm(m4=self.posY)
                          elif fy > self.center_y:
                              direction_text += "DOWN"
                              self.posY += 2
                              self.robot.move_arm(m4=self.posY)

                        
                      
                    cv2.putText(img, str(pos), (fx+15, fy-15), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2 )
                    cv2.putText(img, direction_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
     

        return img

    def setCameraRun(self, boolean):
        self.isCameraRun = boolean

    def run(self):
        
        if (self.isCameraInitial):
            self.robot.move_arm(m1=195, m2=60, m3=40, m4=20, grip=2)
            self.isCameraInitial = False
            time.sleep(2)
      

        frame = self.process_frame()
  
        if (self.isCameraRun):

            cv2.imshow("Image", frame)

            if cv2.waitKey(100) & 0xFF == ord('q'):
       
              self.setCameraRun(False)
              self.setIsCameraRun(False)
              cv2.destroyAllWindows()

        else:        
          cv2.destroyAllWindows()



