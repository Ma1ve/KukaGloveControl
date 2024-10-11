import math
import time

import cv2
import numpy as np

from Objects import *
from Screen import Screen

deb = True


def debug(inf):
    if deb:
        print(inf)


class GuiControl:
    def __init__(self, width, height, robot):

        # robot class
        self.robot = robot

        # window properties
        self.width = width
        self.height = height

        # arm window settings
        self.cylindrical_scale = 1.5
        self.start_point_x = int(width // 2 - 175 * self.cylindrical_scale)
        self.start_point_y = int(height // 2 + 10 * self.cylindrical_scale)
        self.move_body_scale = 30
        self.economy_mode = False

        # canvases
        self.arm_background = np.array([[[20, 70, 190]] * 600] * 480, dtype=np.uint8)
        self.arm_screen = np.copy(self.arm_background)

        self.body_pos_background = np.array([[[20, 70, 190]] * 300] * 300, dtype=np.uint8)
        self.body_pos_screen = np.copy(self.body_pos_background)

        # arm parameters
        self.m2_ang_offset = - math.pi
        self.m3_ang_offset = 2 * math.pi
        self.m4_ang_offset = 0
        self.m2_len = 155
        self.m3_len = 135
        self.m4_len = 200
        self.m2_range = [-65, 90]
        self.m3_range = [-150, 146]

        # operable data
        self.target = [[100, 100], math.pi / 2]
        self.target_cartesian = [[50, 50, 50], math.pi / 2]
        self.move_speed = [0.0, 0.0, 0.0]
        self.move_speed_val = 0.5
        self.target_body_pos = [0, 0, 0]

        # flags, counters, service
        self.old_lidar = None
        self.old_body_pos = [0, 0, 0]
        self.last_checked_pressed_keys = None
        self.robot.going_to_pos_sent = False
        self.current_cam_mode = False

    def init_pygame(self):
        """
        Initialises PyGame and precreated pygame objects:
        two buttons to change camera mode and six sliders to control arm
        """
        if self.robot.connected:
            while not self.robot.arm:
                time.sleep(0.05)
            m1_ang, m2_ang, m3_ang, m4_ang, m5_ang, grip = *self.robot.arm, 0
        else:
            m1_ang, m2_ang, m3_ang, m4_ang, m5_ang, grip = 0, 0, 0, 0, 0, 0
        self.screen = Screen(1240, 780)
        Button(self.screen, x=750, y=700, width=100, height=50, color=(150, 255, 170), func=self.change_cam_mode)
        Button(self.screen, x=900, y=700, width=100, height=50, color=(150, 255, 170))
        self.m1_slider = Slider(self.screen,
                                min=-134, max=157, val=m1_ang,
                                x=690, y=500,
                                width=500, height=20,
                                color=(150, 160, 170),
                                func=self.change_m1_angle)
        self.m2_slider = Slider(self.screen,
                                min=-84, max=63, val=m2_ang,
                                x=690, y=530,
                                width=500, height=20,
                                color=(150, 160, 170),
                                func=self.change_m2_angle)
        self.m3_slider = Slider(self.screen, min=-135, max=110, val=m3_ang,
                                x=690, y=560,
                                width=500, height=20,
                                color=(150, 160, 170),
                                func=self.change_m3_angle)
        self.m4_slider = Slider(self.screen, min=-90, max=95, val=m4_ang,
                                x=690, y=590,
                                width=500, height=20,
                                color=(150, 160, 170),
                                func=self.change_m4_angle)
        self.m5_slider = Slider(self.screen, min=-145, max=96, val=m5_ang,
                                x=690, y=620,
                                width=500, height=20,
                                color=(150, 160, 170),
                                func=self.change_m5_angle)
        self.grip_slider = Slider(self.screen, min=0, max=2, val=grip,
                                  x=690, y=650,
                                  width=500, height=20,
                                  color=(150, 160, 170),
                                  func=self.change_grip)

        self.robot_cam_pygame = Mat(self.screen, x=0, y=0, cv_mat_stream=self.robot.camera_BGR)
        self.body_pos_pygame = Mat(self.screen, x=0, y=480, cv_mat_stream=self.body_pos_stream,
                                   func=self.update_body_pos)
        self.arm_pygame = Mat(self.screen, x=640, y=0, cv_mat_stream=self.arm_stream, func=self.mouse_on_arm)
        self.pos_text_x = Text(self.screen,
                               x=30, y=740,
                               inp_text=self.output_pos_text_x,
                               font='serif',
                               font_size=30)
        self.pos_text_y = Text(self.screen,
                               x=130, y=740,
                               inp_text=self.output_pos_text_y,
                               font='serif',
                               font_size=30)

    def change_cam_mode(self, *args):
        """
        When called changes camera mode to different from current
        """
        if self.current_cam_mode:
            self.robot_cam_pygame.cv_mat_stream = self.robot.camera_BGR
        else:
            self.robot_cam_pygame.cv_mat_stream = self.robot.depth_camera
        self.current_cam_mode = not self.current_cam_mode

    def body_pos_stream(self):
        """
        service function for correct work with CvMat
        :return: map CvMat
        """
        return self.body_pos_screen

    def arm_stream(self):
        """
        service function for correct work with CvMat
        :return: manipulator control CvMat
        """
        return self.arm_screen

    def run(self):
        """
        main cycle
        initialises PyGame, updates all data, check pressed keys, updates screen
        :return:
        """
        self.init_pygame()
        while self.screen.running:
            if not self.economy_mode:
                self.update_arm(self.cylindrical_scale)
            self.update_keys()
            self.screen.step()
        self.robot.disconnect()

    def change_m1_angle(self, val):
        """
        service function for changing manipulator's joint angle
        :param val: angle of joint 1
        :return:
        """
        self.robot.move_arm(m1=val)

    def change_m2_angle(self, val):
        """
        service function for changing manipulator's joint angle
        :param val: angle of joint 2
        :return:
        """
        self.robot.move_arm(m2=val)

    def change_m3_angle(self, val):
        """
        service function for changing manipulator's joint angle
        :param val: angle of joint 3
        :return:
        """
        self.robot.move_arm(m3=val)

    def change_m4_angle(self, val):
        """
        service function for changing manipulator's joint angle
        :param val: angle of joint 4
        :return:
        """
        self.robot.move_arm(m4=val)

    def change_m5_angle(self, val):
        """
        service function for changing manipulator's joint angle
        :param val: angle of joint 5
        :return:
        """
        self.robot.move_arm(m5=val)

    def change_grip(self, val):
        """
        service function for changing manipulator's joint angle
        :param val: grip position
        :return:
        """
        self.robot.move_arm(grip=val)

    def output_pos_text_x(self):
        odom = self.robot.increment_data
        if odom:
            return "x:{}".format(round(odom[0], 2))
        else:
            return "No Data"
    def output_pos_text_y(self):
        odom = self.robot.increment_data
        if odom:
            return "y:{}".format(round(odom[1], 2))
        else:
            return ""

    # def change_height(self, val):
    #    self.robot.move_arm(m5=val)

    def update_keys(self):
        """
        checks pressed keys and configure commands to send according to pressed keys
        :return:
        """
        pressed_keys = self.screen.pressed_keys
        fov = 0
        if pg.K_w in pressed_keys:
            fov += 1
        if pg.K_s in pressed_keys:
            fov -= 1
        self.move_speed[0] = fov * self.move_speed_val

        rot = 0
        if pg.K_a in pressed_keys:
            rot += 1
        if pg.K_d in pressed_keys:
            rot -= 1
        self.move_speed[2] = rot * self.move_speed_val

        side = 0
        if pg.K_q in pressed_keys:
            side += 1
        if pg.K_e in pressed_keys:
            side -= 1
        self.move_speed[1] = side * self.move_speed_val
        if self.last_checked_pressed_keys != pressed_keys:
            self.robot.move_base(*self.move_speed)
            self.robot.going_to_target_pos = False
            self.last_checked_pressed_keys = pressed_keys[:]

        # arm_rot = 0
        # if pg.K_z in pressed_keys:
        #    arm_rot += 0.5
        # if pg.K_x in pressed_keys:
        #    arm_rot -= 0.5

        # if arm_rot != 0:
        #    self.robot.move_arm(m1=max(min(self.robot.arm_pos[0] + arm_rot, 134), -157))

    def update_lidar(self):
        """
        draws lidar data on body_pos_screen
        :return:
        """
        buff, lidar = self.robot.lidar
        if buff and len(buff) == 3:
            x, y, ang = buff
            if lidar:
                if self.old_lidar == lidar:
                    x, y, ang = self.old_body_pos
                else:
                    self.old_body_pos = buff
                    self.old_lidar = lidar
                cent_y, cent_x = y * self.move_body_scale + 150, -x * self.move_body_scale + 150
                cent_y = int(cent_y - 0.3 * self.move_body_scale * math.cos(ang + math.pi / 2))
                cent_x = int(cent_x - 0.3 * self.move_body_scale * math.sin(ang + math.pi / 2))
                for l in range(0, len(lidar), 5):
                    if not 0.01 < lidar[l] < 5.5:
                        continue
                    color = (0, max(255, 255 - int(45.5 * l)), min(255, int(45.5 * l)))
                    cv2.ellipse(self.body_pos_screen, (cent_y, cent_x),
                                (int(lidar[l] * self.move_body_scale), int(lidar[l] * self.move_body_scale)),
                                math.degrees(ang), 30 + int(-240 / len(lidar) * l),
                                30 + int(-240 / len(lidar) * (l + 1)), color,
                                max(1, int(0.1 * self.move_body_scale)))

    def update_body_pos(self, *args):
        """
        draws body rectangle on body_pos_screen and sends robot to set position if mouse pressed
        :param args: set: relative mouse position and is mouse pressed
        :return:
        """
        if self.economy_mode:
            return
        pos = args[0]
        state = args[1]
        if state:
            if not self.robot.going_to_pos_sent:
                self.go_to_pos(*pos)
                self.robot.going_to_pos_sent = True
        else:
            self.robot.going_to_pos_sent = False
        self.body_pos_screen = np.copy(self.body_pos_background)
        buff = self.robot.increment
        if buff:
            x, y, ang = self.target_body_pos
            cv2.circle(self.body_pos_screen, (x, y), 3, (100, 255, 100), -1)
            x, y, ang = self.robot.increment
            cv2.circle(self.body_pos_screen,
                       (int(y * self.move_body_scale + 150), int(-x * self.move_body_scale + 150)),
                       max(1, int(0.05 * self.move_body_scale)), (255, 255, 255), -1)
            size = 30 * self.move_body_scale // 100
            xl1 = int(size * math.cos(ang + math.pi / 2))
            yl1 = int(size * math.sin(ang + math.pi / 2))
            xl2 = int(size * math.cos(ang + math.pi / 2))
            yl2 = int(size * math.sin(ang + math.pi / 2))
            size = 20 * self.move_body_scale // 100
            xw1 = int(size * math.cos(ang))
            yw1 = int(size * math.sin(ang))
            xw2 = int(size * math.cos(ang))
            yw2 = int(size * math.sin(ang))

            x1 = int(y * self.move_body_scale + xl1 + xw1 + 150)
            y1 = int(-x * self.move_body_scale + yl1 + yw1 + 150)
            x2 = int(y * self.move_body_scale - xl2 + xw2 + 150)
            y2 = int(-x * self.move_body_scale - yl2 + yw2 + 150)
            cv2.line(self.body_pos_screen, (x1, y1), (x2, y2), (255, 255, 255), 2)
            x1 = int(y * self.move_body_scale + xl1 - xw1 + 150)
            y1 = int(-x * self.move_body_scale + yl1 - yw1 + 150)
            x2 = int(y * self.move_body_scale - xl2 - xw2 + 150)
            y2 = int(-x * self.move_body_scale - yl2 - yw2 + 150)
            cv2.line(self.body_pos_screen, (x1, y1), (x2, y2), (255, 255, 255), 2)

            x1 = int(y * self.move_body_scale + xw1 + xl1 + 150)
            y1 = int(-x * self.move_body_scale + yw1 + yl1 + 150)
            x2 = int(y * self.move_body_scale - xw2 + xl2 + 150)
            y2 = int(-x * self.move_body_scale - yw2 + yl2 + 150)
            cv2.line(self.body_pos_screen, (x1, y1), (x2, y2), (255, 255, 255), 2)
            x1 = int(y * self.move_body_scale + xw1 - xl1 + 150)
            y1 = int(-x * self.move_body_scale + yw1 - yl1 + 150)
            x2 = int(y * self.move_body_scale - xw2 - xl2 + 150)
            y2 = int(-x * self.move_body_scale - yw2 - yl2 + 150)
            cv2.line(self.body_pos_screen, (x1, y1), (x2, y2), (255, 255, 255),
                     max(1, int(0.02 * self.move_body_scale)))
            self.update_lidar()

    def go_to_pos(self, x, y):
        """
        configures and sends "go to position" command for robot
        :param x: x position
        :param y: y position
        :return:
        """
        self.target_body_pos = [int(x), int(y), 0]
        x, y = (x - 150) / self.move_body_scale, (-y + 150) / self.move_body_scale
        self.robot.go_to(y, x)

    def update_arm(self, scale=1.0):
        """
        updates and draws manipulator data on arm_screen
        :param scale: drawing scale
        :return:
        """
        self.arm_screen = np.copy(self.arm_background)
        m1_ang, m2_ang, m3_ang, m4_ang, m5_ang, grip = *map(math.radians, self.robot.arm_pos[0][:-1]), self.robot.arm_pos[0][
            -1]
        color = (100, 100, 255)

        for i in range(2):
            m2_ang += self.m2_ang_offset
            m3_ang += self.m3_ang_offset
            m4_ang += self.m4_ang_offset

            m3_ang += m2_ang
            m4_ang += m3_ang
            m2x = self.start_point_x
            m2y = self.height - self.start_point_y
            m3x = int(m2x + self.m2_len * math.sin(m2_ang) / scale)
            m3y = int(m2y + self.m2_len * math.cos(m2_ang) / scale)
            m4x = int(m3x + self.m3_len * math.sin(m3_ang) / scale)
            m4y = int(m3y + self.m3_len * math.cos(m3_ang) / scale)
            m5x = int(m4x + self.m4_len * math.sin(m4_ang) / scale)
            m5y = int(m4y + self.m4_len * math.cos(m4_ang) / scale)

            cv2.line(self.arm_screen, (m2x, m2y), (m3x, m3y), color, 2)
            cv2.line(self.arm_screen, (m3x, m3y), (m4x, m4y), color, 2)
            cv2.line(self.arm_screen, (m4x, m4y), (m5x, m5y), color, 2)
            try:
                m1_ang, m2_ang, m3_ang, m4_ang, m5_ang = map(math.radians, self.robot.arm)
            except:
                break
            color = (255, 255, 255)

    def mouse_on_arm(self, *args):
        """
        service function. Called when mouse is on arm work area.
        Draws target. If mouse pressed changes manipulator target position
        :param args: set: relative mouse position, is mouse pressed
        :return:
        """
        if self.economy_mode:
            return
        pos = args[0]
        pressed = args[1]
        self.target[1] = (self.screen.mouse_wheel_pos / 10 + math.pi / 2) % (2 * math.pi)
        target = [[(pos[0] - self.start_point_x) * self.cylindrical_scale,
                   (-pos[1] + self.height - self.start_point_y) * self.cylindrical_scale], self.target[1]]
        _, _, _, available = self.robot.solve_arm(target)
        if pressed:
            color = ((0, 230, 0) if available else (230, 0, 0))
            self.target[0] = [(pos[0] - self.start_point_x) * self.cylindrical_scale,
                              (-pos[1] + self.height - self.start_point_y) * self.cylindrical_scale]
            self.robot.move_arm(target=self.target)
        else:
            color = ((100, 255, 100) if available else (240, 100, 100))
        m1_ang, m2_ang, m3_ang, m4_ang, m5_ang, grip = self.robot.arm_pos[0]
        self.m1_slider.set_val(m1_ang)
        self.m2_slider.set_val(m2_ang)
        self.m3_slider.set_val(m3_ang)
        self.m4_slider.set_val(m4_ang)
        self.m5_slider.set_val(m5_ang)
        self.grip_slider.set_val(grip)
        cv2.circle(self.arm_screen, (int(pos[0]), int(pos[1])), 10, color, 4)
        size = 20
        xs = int(pos[0] + size * 0.6 * math.cos(-self.target[1] - math.pi / 2))
        ys = int(pos[1] + size * 0.6 * math.sin(-self.target[1] - math.pi / 2))
        xe = int(pos[0] - size * 1.4 * math.cos(-self.target[1] - math.pi / 2))
        ye = int(pos[1] - size * 1.4 * math.sin(-self.target[1] - math.pi / 2))
        cv2.line(self.arm_screen, (xs, ys), (xe, ye), color, 2)

