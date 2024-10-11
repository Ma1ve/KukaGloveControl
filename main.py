""" Управление роботом с помощью перчатки Arduino """
from KUKA import KUKA

from testArduinoArm import TestServoController 
from ArmGUI import ButtonWindow

robot = KUKA('192.168.88.25', ros=False, camera_enable=True)
testArm = TestServoController(robot)

button_window = ButtonWindow(testArm, 550, 600)
button_window.run()

testArm.control_servos()


""" Управление роботом с помощью GUI """
# from KUKA import KUKA
# from GUI_pygame import GuiControl
# import time

# from arduinoArm import ServoController 

# robot = KUKA('192.168.88.23', ros=True, camera_enable=False)
# # robot = ['192.168.88.21', '192.168.88.22', '192.168.88.23', '192.168.88.24', '192.168.88.25']
# # sim = GuiControl(1200, 900, robot)
# # sim.run()

# # robot.
# arm = ServoController(robot) 
# arm.control_servos()




# 0
# 1 Поворот вокруг оси от 11 до 302 a
# 2 наклон вперед-назад всей частью от 3 до -150
# 3 наклон вперед только 1 частью, которая выше -15 до -260
# 4 наклон 3 части вправо-влево (как махать ладонью) то 10 до 195
# 5 поворот крана, где прикреплен grip от 21 до 262d
# grip Захват от 0.0 до 2.0



