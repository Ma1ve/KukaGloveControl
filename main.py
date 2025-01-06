""" Control the Kuka robot with a glove arduino """

from KUKA import KUKA
from ArduinoArm import GloveServoController 
from ArmGUI import GloveControlGUI

# Initialize the KUKA robot with the specified IP address
robot = KUKA('192.168.88.25', ros=False, camera_enable=True)

# Set up the glove servo controller to control the robot's servos
glove_servo_controller = GloveServoController(robot)

# Create the glove GUI window for controlling the robot
glove_gui = GloveControlGUI(glove_servo_controller, 550, 600)
glove_gui.run()

# Control the servos using data from the glove
glove_servo_controller.control_servos()

# You can also use an alternative GUI panel for robot control.
# Before using the alternate GUI (GUI_pygame), you should remove the glove_servo_controller
# and its associated GUI (ButtonWindow) setup, as they are not compatible with the new GUI.
# Uncomment the following lines to use the alternate GUI (GUI_pygame):

# from GUI_pygame import GuiControl
# sim = GuiControl(1200, 900, robot)
# sim.run()  # Run the GUI for controlling the robot






