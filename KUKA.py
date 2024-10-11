import io
import math
import socket
import threading as thr
import time

import cv2
import numpy as np
import paramiko
from PIL import Image
from mjpeg.client import MJPEGClient

deb = True


def debug(inf, /, end="\n"):
    """
    Prints info if variable deb is True
    :param inf: info to print
    """
    if deb:
        print(inf, end=end)


def range_cut(mi, ma, val):
    """
    Cuts value from min to max
    :param mi: minimum value
    :param ma: maximum value
    :param val: value
    :return: cut value
    """
    return min(ma, max(mi, val))


class KUKA:
    """
    KUKA youbot controller
    """

    def __init__(self, ip, /,
                 ros=False,
                 offline=False,
                 read_depth=True,
                 camera_enable=True,
                 advanced=False,
                 log=None,
                 read_from_log=None,
                 **kwargs):
        """
        Initializes robot KUKA youbot\n
        Establishes connection with depth and RGB video server\n
        Establishes connection with control and sensor socket\n
        Starts sending commands thread\n
        Starts reading sensors data thread
        :param ip: robot ip
        :param ros: force restart of youbot_tl_test on KUKA if true
        :param offline: toggles offline mode (doesn't try to connect to robot)
        :param read_depth: if false doesn't start depth client
        :param camera_enable: enables mjpeg client if True
        :param advanced: disables all safety checks in the sake of time saving
        :param log: if [path, freq] logs odometry and lidar data to set path with set frequency
        :param read_from_log: if [path, freq] streams odometry and lidar data from set log path with set frequency
        """
        if advanced:
            debug("WARNING!!! ADVANCED MODE ENABLED, ALL SAFETY CHECKS ARE SUSPENDED")

        self.ssh_client = paramiko.SSHClient()
        self.threads_number = 0
        self.main_thr = thr.main_thread()
        self.camera_enable = camera_enable
        self.read_depth = read_depth
        self.ip = ip
        self.frequency = 50  # operating frequency
        self.data_lock = thr.Lock()
        self.connected = True

        # data from this variable one by one to avoid data loss (order: base, arm, grip)
        self.send_queue = [None, None, None]
        self.send_time = 0  # last time data was sent (service)

        # camera receive buffer
        self.data_buff = b''
        self.max_buff_len = 1500

        # filling camera variables with color
        self.cam_image = np.array([[[190, 70, 20]] * 640] * 480, dtype=np.uint8)
        self.cam_image_BGR = np.array([[[20, 70, 190]] * 640] * 480, dtype=np.uint8)
        self.cam_depth = np.array([[[190, 70, 20]] * 640] * 480, dtype=np.uint8)

        # control
        self.arm_ID = 0
        self.arm_pos = [[0, 56, -80, -90, 0, 1.98], [0, 56, -80, -90, 0, 1.98]]  # last sent arm position
        self.arm_vel = [[0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]
        self.body_target_pos = [0, 0, 0]  # current body target position
        self.going_to_target_pos = False
        self.move_speed = (0, 0, 0)  # last sent move speed
        self.move_to_target_max_speed = 0.2  # max move to target speed
        self.move_to_target_k = 1  # move to target proportional coefficient

        # dimensions (lengths of joints)
        self.m2_len = 155
        self.m3_len = 135
        self.m4_len = 200

        # sensor data
        self.lidar_data = None
        self.increment_data_lidar = None  # the closest to lidar read increment value
        self.increment_data = None
        self.corr_arm_pos = [None, None]
        self.wheels_data = None
        self.wheels_data_lidar = None
        self.trace = 0

        # for position correction
        self.wheels_old = None
        self.calculation_pos = False
        self.calculated_pos = [0, 0, 0]
        self.calculated_pos_lidar = [0, 0, 0]

        if read_from_log:
            self.connected = False
            self.log_stream_thr = thr.Thread(target=self.stream_from_log, args=read_from_log)
            self.log_stream_thr.start()
            return
        if offline:
            self.connected = False
            return

        # connection
        debug(f"connecting to {ip}")


        if not advanced or ros:
            self.check_active_nodes_via_ssh(force_restart=ros)

        if self.connected:
            debug("connecting to control channel")
            # init socket
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.settimeout(2)
            self.conn.connect((self.ip, 7777))
            # init reading thread
            self.data_thr = thr.Thread(target=self._receive_data, args=())
            self.send_thr = thr.Thread(target=self.send_data, args=())
            time.sleep(1)
            self.data_thr.start()
            self.send_thr.start()
            self.threads_number += 2
            debug("connected to 7777 (data stream)")

        # connecting to video server
        if self.connected and self.camera_enable:
            if self.read_depth:
                self.init_depth_client()
            self.init_rgb_client()

        # waiting for initial arm position
        if self.connected:
            # debug("waiting for initial arm position")
            self.corr_arm_pos = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
            self.arm_pos[0][:-1] = self.corr_arm_pos[0]
            self.arm_pos[1][:-1] = self.corr_arm_pos[1]
            while not self.corr_arm_pos and not advanced:
                time.sleep(0.1)
        if log:
            self.logger_thr = thr.Thread(target=self.logger, args=log)
            self.logger_thr.start()

    def init_rgb_client(self):
        """
        Starts video client thread that reads RGB video
        """
        debug("connecting to video channel")
        self.client_rgb = MJPEGClient(
            f"http://{self.ip}:8080/stream?topic=/camera/rgb/image_rect_color&width=640&height=480&quality=20")
        bufs = self.client_rgb.request_buffers(65536, 5)
        for b in bufs:
            self.client_rgb.enqueue_buffer(b)
        self.client_rgb.start()
        self.cam_rgb_lock = thr.Lock()
        self.cam_rgb_thr = thr.Thread(target=self.get_frame_color, args=())
        self.threads_number += 1
        self.cam_rgb_thr.start()

    def init_depth_client(self):
        """
        Starts video client thread that reads depth video
        """
        self.client_depth = MJPEGClient(f"http://{self.ip}:8080/stream?topic=/camera/depth/image_rect")
        bufsd = self.client_depth.request_buffers(65536, 5)
        for b in bufsd:
            self.client_depth.enqueue_buffer(b)
        self.client_depth.start()
        self.cam_depth_lock = thr.Lock()
        self.cam_depth_thr = thr.Thread(target=self.get_frame_depth, args=())
        self.threads_number += 1
        self.cam_depth_thr.start()

    def check_active_nodes_via_ssh(self, /, user='youbot', password='111111', force_restart=False):
        """
        Connects to KUKA youbot via SSH client and checks rostopics

        :param user: youbot by default
        :param password: 111111 by default
        """
        port = 22
        rostopic = ''
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.ip[-1] == "1":
            password = "111111"
        elif self.ip[-1] == "2":
            password = "111111"
        elif self.ip[-1] == "3":
            password = "0987654321"
            # 0987654321
        elif self.ip[-1] == "4":
            password = "111111"
            # 112233
        elif self.ip[-1] == "5":
            password = "111111"
        debug("ROS status check...")
        try:
            client.connect(hostname=self.ip, username=user, password=password, port=port)
        except Exception as err:
            debug(err)
            self.connected = False
            self.camera_enable = False
            self.read_depth = False
            return

        ssh = client.invoke_shell()
        time.sleep(0.1)
        ssh.send(b"sudo -s\n")
        time.sleep(0.1)
        ssh.send(password.encode("utf-8") + b"\n")
        if force_restart:
            debug("ROS force restart")
            self.connect_ssh()
        else:
            time.sleep(0.1)
            msg = ssh.recv(10000).decode("utf-8")
            while not msg.count("root@youbot:"):
                msg += ssh.recv(1).decode("utf-8")
            ssh.send(b"rostopic list\n")
            rostopic = ssh.recv(10000).decode("utf-8")
            while not rostopic.count("root@youbot:"):
                rostopic += ssh.recv(1).decode("utf-8")
            if rostopic.count("ERROR: Unable"):
                debug("ROS not running")
                rostopic = ''
                self.connect_ssh()

        if rostopic == '':
            ssh.send(b"rostopic list\n")
        while not rostopic.count("root@youbot:"):
            rostopic += ssh.recv(1).decode("utf-8")
        if self.camera_enable:
            if rostopic.count("camera/rgb/image_raw"):
                debug("RGB camera is active")
            else:
                debug("WARN: RGB camera is inactive")
                self.camera_enable = False
            if self.read_depth:
                if rostopic.count("camera/depth/image"):
                    debug("depth camera is active")
                else:
                    debug("WARN: depth camera is inactive")
                    self.read_depth = False

    def connect_ssh(self, /, user='youbot', password='111111'):
        """
        Connects to KUKA youbot via SSH client and starts ROS

        :param user: youbot by default
        :param password: 111111 by default
        """
        port = 22

        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.ip[-1] == "1":
            password = "111111"
        elif self.ip[-1] == "3":
            password = "0987654321"
        elif self.ip[-1] == "4":
            password = "111111"
        elif self.ip[-1] == "5":
            password = "111111"
        elif self.ip[-1] == "2":
            password = "111111"
        try:
            self.ssh_client.connect(hostname=self.ip, username=user, password=password, port=port)
        except Exception as err:
            debug(err)
            self.connected = False
            return
        ssh = self.ssh_client.invoke_shell()
        time.sleep(0.5)
        debug("log as root")
        ssh.send(b"sudo -s\n")
        time.sleep(0.5)
        ssh.send(password.encode("utf-8") + b"\n")
        debug("cleaning screen...")
        time.sleep(1)
        ssh.send(b"pkill screen\n")
        time.sleep(0.5)
        ssh.send(b"screen -S roslaunch\n")
        debug("roslaunch screen created")
        time.sleep(0.5)
        ssh.send(b"roslaunch youbot_tl_test ytl_2arm.launch\n")
        ssh_msg = ""

        debug("waiting ros to start...")
        for i in range(10000):
            ssh_msg += ssh.recv(1).decode("utf-8")
            if ssh_msg.count("System has"):
                debug("ros started")
                ssh_msg += ssh.recv(20).decode("utf-8")
                if ssh_msg.count("System has 0"):
                    debug("WARN: no arms connected")
                time.sleep(1)
                self.ssh_client.close()
                break

        self.ssh_client.close()
        time.sleep(0.5)

    # receiving and parsing sensor data

    def post_to_send_data(self, ind, data):
        """
        Updates send queue

        :param ind: data type: 0-base, 1-arm, 2-grip
        :param data: message contents
        """
        if self.connected:
            # self.send_lock.acquire()
            self.send_queue[ind] = data
            # self.send_lock.release()
        else:
            self.send_queue[ind] = data

    def send_data(self):
        """
        Sends all available commands (thread)
        """

        send_ind = 0
        while self.main_thr.is_alive():
            to_send = None
            while not to_send and self.main_thr.is_alive():
                # self.send_lock.acquire()
                to_send = self.send_queue[send_ind]
                self.send_queue[send_ind] = None
                # self.send_lock.release()
                send_ind += 1
                self.send_time = time.time_ns()
                if send_ind == 3:
                    send_ind = 0
                time.sleep(1 / self.frequency)
            if self.connected:
                try:
                    if to_send:
                        self.conn.send(to_send)
                except BrokenPipeError:
                    debug("send_data thread died due to broken pipe")
                    break

            else:
                debug(f"message:{to_send}")
                pass

        self.threads_number -= 1
        debug(f"send_data thread terminated, {self.threads_number} threads remain")

    def wheelPositionsToCartesianPosition(self):
        '''
        Converts wheels transition to cartesian position
        :return: None
        '''
        wheels = self.wheels
        if wheels and not self.wheels_old:
            self.wheels_old = wheels
        elif not wheels:
            return

        last_wheel_positions = self.wheels_old
        wheel_positions = wheels

        wheel_radius_per4 = 0.0475 / 4.0

        geom_factor = (0.47 / 2.0) + (0.3 / 2.0)
        ang = self.calculated_pos[2]

        delta_positionW1 = (wheel_positions[0] - last_wheel_positions[0])
        delta_positionW2 = (wheel_positions[1] - last_wheel_positions[1])
        delta_positionW3 = (wheel_positions[2] - last_wheel_positions[2])
        delta_positionW4 = (wheel_positions[3] - last_wheel_positions[3])
        self.trace += abs(delta_positionW1)+abs(delta_positionW2)+abs(delta_positionW3)+abs(delta_positionW4)
        deltaLongitudinalPos = (
                                           delta_positionW1 + delta_positionW2 + delta_positionW3 + delta_positionW4) * wheel_radius_per4
        deltaTransversalPos = (
                                          -delta_positionW1 + delta_positionW2 + delta_positionW3 - delta_positionW4) * wheel_radius_per4
        ang -= (-delta_positionW1 + delta_positionW2 - delta_positionW3 + delta_positionW4) * (
                    wheel_radius_per4 / geom_factor)

        ang = (abs(ang + 2 * math.pi)) % (2 * math.pi)

        self.calculated_pos[0] += deltaLongitudinalPos * math.cos(ang) + deltaTransversalPos * math.sin(ang)
        self.calculated_pos[1] += deltaLongitudinalPos * math.sin(ang) - deltaTransversalPos * math.cos(ang)
        self.calculated_pos[2] = ang

        self.wheels_old = wheels

    def _parse_data(self, data):
        """
        Parses all received data and write values to variables\n
        keys available: ".laser#", ".odom#", ".manip#"

        :param data: received data
        """
        write_lidar = None
        write_increment = None
        write_arm1 = None
        write_arm2 = None
        wheels = None
        if data[:7] == ".laser#":
            raw = list(data[7:].split(';'))
            if len(raw) < 200:
                write_lidar = None
            else:
                write_lidar = []
                for i in raw:
                    try:
                        write_lidar.append(float(i))
                    except:
                        if i != "":
                            write_lidar.append(5)

        elif data[:6] == ".odom#":
            try:
                write_increment = list(map(float, data[6:].split(';')))
            except:
                write_increment = None
        elif data[:8] == ".manip0#":
            try:
                write_arm1 = list(map(float, data[8:].split(';')))

            except:
                write_arm1 = None
        elif data[:8] == ".manip1#":
            try:
                write_arm2 = list(map(float, data[8:].split(';')))
            except:
                write_arm2 = None
        elif data[:8] == ".wheels#":
            try:
                wheels = list(map(float, data[8:].split(';')))
            except:
                wheels = None
        # update data
        if write_lidar or write_increment or write_arm1 or write_arm2 or wheels:

            self.data_lock.acquire()
            if write_lidar:
                self.lidar_data = write_lidar
                self.increment_data_lidar = self.increment_data
                self.calculated_pos_lidar = self.calculated_pos[:]
                self.wheels_data_lidar = self.wheels_data
            if write_increment:
                self.increment_data = write_increment
            if wheels:
                self.wheels_data = wheels

            if write_arm1:
                # arm_ID = 0  # затычка
                m1 = -write_arm1[0] + 168
                m2 = -write_arm1[1] + 66
                m3 = -write_arm1[2] - 150
                m4 = -write_arm1[3] + 105
                m5 = write_arm1[4] - 166
                self.corr_arm_pos[0] = [m1, m2, m3, m4, m5]
            if write_arm2:
                # arm_ID = 0  # затычка
                m1 = -write_arm2[0] + 168
                m2 = -write_arm2[1] + 66
                m3 = -write_arm2[2] - 150
                m4 = -write_arm2[3] + 105
                m5 = write_arm2[4] - 166
                self.corr_arm_pos[1] = [m1, m2, m3, m4, m5]
            self.data_lock.release()
            if wheels and not self.calculation_pos:
                self.calculation_pos = True
                self.wheelPositionsToCartesianPosition()
                self.calculation_pos = False

    def _receive_data(self):
        """
        Reads data from sensors data port (thread)
        """

        data_buff_len = 0
        self.data_buff = b''
        while self.main_thr.is_alive():
            if data_buff_len > 5000:
                self.data_buff = b''
                data_buff_len = 0
            try:
                el = self.conn.recv(1)
            except TimeoutError:
                debug("_receive_data thread died due to timeout")
                break
            except Exception as exc:
                debug(f"_receive_data thread died due to {exc}")
                break

            if el != b'':
                self.data_buff += el
                data_buff_len += 1
            if data_buff_len > 0 and self.data_buff[-1] == 13:
                self.conn.recv(1)

                try:
                    str_data = str(self.data_buff[:-1], encoding='utf-8')
                    self.data_parser_tht = thr.Thread(target=self._parse_data, args=(str_data,))
                    self.data_parser_tht.start()
                except:
                    pass
                self.data_buff = b''
                data_buff_len = 0
        self.threads_number -= 1
        debug(f"_receive_data thread terminated, {self.threads_number} threads remain")

    def logger(self, path, freq):
        '''
        Logs odometry and lidar data to path with set frequency
        :param path: name and path to log file
        :param freq: logging frequency
        :return: None
        '''
        self.threads_number += 1
        while not (self.increment_data_lidar and self.lidar):
            time.sleep(0.2)
        debug(f"writing log to {path} with 1/{freq}Hz")
        self.log_file = open(path, "a")
        while self.main_thr.is_alive():
            self.log_file.write(", ".join(map(str, self.increment_data_lidar)) + "; " + ", ".join(map(str, self.lidar[-1])) + "\n")
            time.sleep(1 / freq)
        self.log_file.close()
        self.threads_number -= 1
        debug(f"logger thread terminated, {self.threads_number} threads remain")

    def stream_from_log(self, path, freq):
        '''
        streams odometry and lidar data from path with set frequency
        :param path: name and path to log file
        :param freq: logging frequency
        :return: None
        '''
        self.threads_number += 1
        debug(f"streaming log from {path} with 1/{freq}Hz")
        log_file = open(path, "r")
        log_data = []
        for i in log_file:
            sp_log_data = i.split(';')
            if sp_log_data[-1] == '':
                break
            odom = sp_log_data[0].split(',')
            lidar = sp_log_data[1].split(',')
            odom = list(map(float, odom))
            lidar = list(map(float, lidar))
            log_data.append([odom, lidar])
        self.log_data = log_data[:]
        i = 0
        while self.main_thr.is_alive() and i < len(self.log_data):
            self.data_lock.acquire()
            self.wheels_data, self.lidar_data = self.log_data[i]
            self.wheels_data_lidar = self.wheels_data
            i += 1
            self.data_lock.release()
            self.wheelPositionsToCartesianPosition()
            time.sleep(1 / freq)
        log_file.close()
        self.threads_number -= 1
        debug(f"logger thread terminated, {self.threads_number} threads remain")

    # get functions

    @property
    def lidar(self):
        """
        Acquires variable data lock and reads lidar data

        :return: lidar data
        """
        self.data_lock.acquire()
        out = self.lidar_data
        inc = self.calculated_pos_lidar
        self.data_lock.release()
        return inc, out

    @property
    def arm(self, /, arm_ID=0):
        """
        Acquires variable data lock and reads arm position

        :return: arm position
        """
        if self.connected:
            self.data_lock.acquire()

            out = self.corr_arm_pos[arm_ID]
            self.data_lock.release()
            return out
        else:
            return None, None, None, None, None

    @property
    def increment_by_wheels(self):
        """
        Acquires variable data lock and reads increment values

        :return: increment values
        """
        self.data_lock.acquire()
        out = self.calculated_pos[:]
        self.data_lock.release()
        return out

    @property
    def wheels(self):
        """
        Acquires variable data lock and reads increment values

        :return: increment values
        """
        self.data_lock.acquire()
        out = self.wheels_data[:]
        self.data_lock.release()
        return out


    @property
    def increment(self):
        """
        Acquires variable data lock and reads increment values

        :return: increment values
        """
        if self.connected:
            self.data_lock.acquire()
            out = self.increment_data
            self.data_lock.release()
            return out
        else:
            return [0,0,0]

    def camera(self):
        """
        Acquires variable camera lock and reads camera in RGB

        :return: MJPEG RGB image
        """
        if self.connected:
            self.cam_rgb_lock.acquire()
            out = self.cam_image
            self.cam_rgb_lock.release()
            return out
        else:
            return self.cam_image

    def camera_BGR(self):
        """
        Acquires variable camera lock and reads camera in BGR

        :return: MJPEG BGR image
        """
        if self.connected and self.camera_enable:
            self.cam_rgb_lock.acquire()
            out = self.cam_image_BGR
            self.cam_rgb_lock.release()
            return out
        else:
            return self.cam_image_BGR

    def depth_camera(self):
        """
        Acquires variable camera lock and reads depth camera

        :return: MJPEG depth image
        """
        if self.connected and self.read_depth:
            self.cam_depth_lock.acquire()
            out = self.cam_depth
            self.cam_depth_lock.release()
            return out
        else:
            return self.cam_depth

    # control base and arm
    # go with set speed
    def move_base(self, f=0.0, s=0.0, r=0.0):
        """
        Sets moving speed

        :param f: forward speed
        :param s: sideways speed
        :param r: rotation speed
        """
        f = range_cut(-1, 1, f)
        s = range_cut(-1, 1, s)
        r = range_cut(-1, 1, r)
        self.post_to_send_data(0, bytes(f'/base:{f};{s};{r}^^^', encoding='utf-8'))
        self.move_speed = (f, s, r)

    # go to set coordinates
    def go_to(self, x, y, ang=0, /, prec=0.005, k=1, initial_speed=None):
        """
        Sends robot to given coordinates
        :param x: x position in relative coordinates
        :param y: y position in relative coordinates
        :param ang: angle from x axes
        """
        if not initial_speed:
            initial_speed = self.move_to_target_max_speed
        if self.main_thr.is_alive():
            if self.going_to_target_pos:
                self.body_target_pos_lock.acquire()
                self.body_target_pos = [x, y, ang]
                self.body_target_pos_lock.release()
            else:
                self.body_target_pos_lock = thr.Lock()
                self.going_to_target_pos = True
                self.body_target_pos = [x, y, ang]
                self.go_to_tr = thr.Thread(target=self.move_base_to_pos, args=([prec, k, initial_speed]))
                self.threads_number += 1
                self.go_to_tr.start()

    def move_base_to_pos(self, prec=0.005, k=None, initial_speed=0.05):
        """
        Moving to point thread
        """
        if not k:
            k = self.move_to_target_k
        while self.main_thr.is_alive() and self.going_to_target_pos:
            self.body_target_pos_lock.acquire()
            x, y, ang = self.body_target_pos
            self.body_target_pos_lock.release()
            inc = self.increment
            loc_x = x - inc[0]
            loc_y = y - inc[1]
            rob_ang = inc[2]
            dist = math.sqrt(loc_x ** 2 + loc_y ** 2)
            speed = min(initial_speed, dist * k)

            targ_ang = math.atan2(loc_y, loc_x)
            loc_ang = targ_ang - rob_ang
            if dist < prec and (ang - rob_ang) < prec:
                break
            fov_speed = speed * math.cos(loc_ang)
            side_speed = -speed * math.sin(loc_ang)
            total_speed = math.sqrt(fov_speed ** 2 + side_speed ** 2)
            ang_speed = -(ang - rob_ang) / (dist / total_speed)
            self.move_base(fov_speed, side_speed, ang_speed)
            time.sleep(1 / self.frequency)
        self.move_base(0, 0, 0)
        time.sleep(0.01)
        self.move_base(0, 0, 0)
        self.going_to_target_pos = False
        self.threads_number -= 1
        debug(f"move_base_to_pos thread terminated, {self.threads_number} threads remain")

    # move arm forward or inverse kinetic
    def move_arm(self, *args, **kwargs):
     
        """
        Sets arm position\n
        ways to set arm position:\n
        array of values: (joint 1, joint 2, joint 3, joint 4, joint 5, grip)\n
        by keywords:
            m1, m2, m3, m4, m5 - for joints\n
            grip - (0 - 2) for grip\n
            target - ((x, y), ang) to set arm position in cylindrical coordinates (ang - angle from last joint to horizon)\n
        (all joint parameters are in degrees from upright position)
        """
        grip = False

        if list(kwargs.keys()).count("arm_ID") > 0:
            self.arm_ID = kwargs["arm_ID"]
        else:
            self.arm_ID = 0
        if args:
            self.arm_pos[self.arm_ID][:len(args)] = args
            if len(args) == 6:
                grip = True
        if list(kwargs.keys()).count("m1") > 0:
            self.arm_pos[self.arm_ID][0] = kwargs["m1"]
        if list(kwargs.keys()).count("m2") > 0:
            self.arm_pos[self.arm_ID][1] = kwargs["m2"]
        if list(kwargs.keys()).count("m3") > 0:
            self.arm_pos[self.arm_ID][2] = kwargs["m3"]
        if list(kwargs.keys()).count("m4") > 0:
            self.arm_pos[self.arm_ID][3] = kwargs["m4"]
        if list(kwargs.keys()).count("m5") > 0:
            self.arm_pos[self.arm_ID][4] = kwargs["m5"]
        if list(kwargs.keys()).count("grip") > 0:
            self.arm_pos[self.arm_ID][5] = kwargs["grip"]
            self.post_to_send_data(2, bytes(f'/grip:{self.arm_ID};{self.arm_pos[self.arm_ID][5]}^^^', encoding='utf-8'))
        if grip:
            self.arm_pos[self.arm_ID][5] = args[-1]
            self.post_to_send_data(2, bytes(f'/grip:{self.arm_ID};{self.arm_pos[self.arm_ID][5]}^^^', encoding='utf-8'))

        if list(kwargs.keys()).count("target") > 0:
            if len(kwargs["target"][0]) == 2:
                m2, m3, m4, _ = self.solve_arm(kwargs["target"])
                self.arm_pos[self.arm_ID][1:4] = m2, m3, m4

        m1 = range_cut(11, 302, -self.arm_pos[self.arm_ID][0] + 168)
        m2 = range_cut(3, 150, -self.arm_pos[self.arm_ID][1] + 66)
        m3 = range_cut(-260, -15, -self.arm_pos[self.arm_ID][2] - 150)
        m4 = range_cut(10, 195, -self.arm_pos[self.arm_ID][3] + 105)
        m5 = range_cut(21, 292, self.arm_pos[self.arm_ID][4] + 166)
        self.post_to_send_data(1, bytes(f'/arm:{self.arm_ID};{m1};{m2};{m3};{m4};{m5}^^^', encoding='utf-8'))

    def set_arm_vel(self, *args, **kwargs):
        """
        Sets arm velocities\n
        ways to set arm velocities:\n
        array of values: (joint 1, joint 2, joint 3, joint 4, joint 5)\n
        by keywords:
            m1, m2, m3, m4, m5 - for joints\n
        (all joint parameters are in degrees/second)
        """

        if list(kwargs.keys()).count("arm_ID") > 0:
            self.arm_ID = kwargs["arm_ID"]

        if args:
            self.arm_vel[self.arm_ID][:len(args)] = args

        else:
            self.arm_ID = 0
        if list(kwargs.keys()).count("m1") > 0:
            self.arm_vel[self.arm_ID][0] = kwargs["m1"]
        if list(kwargs.keys()).count("m2") > 0:
            self.arm_vel[self.arm_ID][1] = kwargs["m2"]
        if list(kwargs.keys()).count("m3") > 0:
            self.arm_vel[self.arm_ID][2] = kwargs["m3"]
        if list(kwargs.keys()).count("m4") > 0:
            self.arm_vel[self.arm_ID][3] = kwargs["m4"]
        if list(kwargs.keys()).count("m5") > 0:
            self.arm_vel[self.arm_ID][4] = kwargs["m5"]

        m1 = range_cut(-90, 90, self.arm_vel[self.arm_ID][0])
        m2 = range_cut(-90, 90, self.arm_vel[self.arm_ID][1])
        m3 = range_cut(-90, 90, self.arm_vel[self.arm_ID][2])
        m4 = range_cut(-90, 90, self.arm_vel[self.arm_ID][3])
        m5 = range_cut(-90, 90, self.arm_vel[self.arm_ID][4])
        self.post_to_send_data(1, bytes(f'/arm_vel:{self.arm_ID};{m1};{m2};{m3};{m4};{m5}^^^', encoding='utf-8'))

    # solve inverse kinetic
    def solve_arm(self, target, cartesian=False):
        """
        Solves inverse kinematics

        :param target: ((x, y), ang) to set arm position in cylindrical coordinates (ang - angle from last joint to horizon)
        :param cartesian: if true solves in cartesian else solves in cylindrical
        """
        if not cartesian:
            x = target[0][0]
            y = target[0][1]
            ang = target[1]
            try:
                x -= self.m4_len * math.sin(ang)
                y += self.m4_len * math.cos(ang)
                fi = math.atan2(y, x)
                b = math.acos((self.m2_len ** 2 + self.m3_len ** 2 - x ** 2 - y ** 2) / (2 * self.m2_len * self.m3_len))
                a = math.acos((self.m2_len ** 2 - self.m3_len ** 2 + x ** 2 + y ** 2) / (
                        2 * self.m2_len * math.sqrt(x ** 2 + y ** 2)))
                m2_ang = fi + a - math.pi / 2
                m3_ang = b - math.pi
                m4_ang = (ang - m2_ang - m3_ang - math.pi)
                m2_ang_neg = fi - a - 3 * math.pi / 2 + math.pi
                m3_ang_neg = -b + math.pi
                m4_ang_neg = (ang + a + b - fi - 3 * math.pi / 2)
                m2_ang, m3_ang, m4_ang = map(math.degrees, (m2_ang, m3_ang, m4_ang))
                m2_ang_neg, m3_ang_neg, m4_ang_neg = map(math.degrees, (m2_ang_neg, m3_ang_neg, m4_ang_neg))
                if -84 < m2_ang < 63 and -135 < m3_ang < 110 and -90 < m4_ang < 95:
                    return m2_ang, m3_ang, m4_ang, True
                elif -84 < m2_ang_neg < 63 and -135 < m3_ang_neg < 110 and -90 < m4_ang_neg < 95:
                    return m2_ang_neg, m3_ang_neg, m4_ang_neg, True
                else:
                    return *self.arm_pos[self.arm_ID][1:4], False
                # m2_ang = range_cut(-84, 63, m2_ang)
                # m3_ang = range_cut(-135, 110, m3_ang)
                # m4_ang = range_cut(-120, 90, m4_ang)
            except:
                # debug("math error, out of range")
                return *self.arm_pos[self.arm_ID][1:4], False
        else:  # (not tested, probably not working)
            x = target[0][0]
            y = target[0][1]
            z = target[0][2]
            ang = target[1]
            xy = math.sqrt(x ** 2 + y ** 2)
            try:
                self.arm_pos[self.arm_ID][0] = math.degrees(math.asin(x / xy))
                z -= self.m4_len * math.sin(ang)
                xy += self.m4_len * math.cos(ang)
                fi = math.atan2(z, xy)
                b = math.acos(
                    (self.m2_len ** 2 + self.m3_len ** 2 - xy ** 2 - z ** 2) / (2 * self.m2_len * self.m3_len))
                a = math.acos((self.m2_len ** 2 - self.m3_len ** 2 + xy ** 2 + z ** 2) / (
                        2 * self.m2_len * math.sqrt(xy ** 2 + z ** 2)))
                m2_ang = fi + a - 3 * math.pi / 2 + math.pi
                m3_ang = b - math.pi
                return list(map(math.degrees, (m2_ang, m3_ang, ang - a - b - fi + math.pi / 2)))
            except:
                debug("math error, out of range")
                return self.arm_pos[self.arm_ID][1:4]

    # video capture

    def get_frame_color(self):
        """
        Reads from color video server and writes to RGB and BGR camera variables (thread)
        """
        while self.main_thr.is_alive():
            try:
                buf_rgb = self.client_rgb.dequeue_buffer()
                image = Image.open(io.BytesIO(buf_rgb.data))
                imageBGR = np.array(image)

                imageRGB = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
                self.client_rgb.enqueue_buffer(buf_rgb)

                self.cam_rgb_lock.acquire()
                self.cam_image = imageRGB
                self.cam_image_BGR = imageBGR
                self.cam_rgb_lock.release()
            except Exception as err:
                debug(err)
                return
        self.threads_number -= 1
        debug(f"get_frame_color thread terminated, {self.threads_number} threads remain")

    def get_frame_depth(self):
        """
        Reads from depth video server and writes to depth camera variable (thread)
        """
        try:
            while self.main_thr.is_alive():
                buf_depth = self.client_depth.dequeue_buffer()
                image_depth = np.array(Image.open(io.BytesIO(buf_depth.data)))
                image_depth = np.stack([image_depth,image_depth,image_depth], axis=2)
                # image_depth = cv2.cvtColor(np.array(image_depth), cv2.COLOR_BGR2GRAY)
                self.client_depth.enqueue_buffer(buf_depth)

                self.cam_depth_lock.acquire()
                self.cam_depth = image_depth
                self.cam_depth_lock.release()
        except Exception as err:
            debug(err)
        self.threads_number -= 1
        debug(f"get_frame_depth thread terminated, {self.threads_number} threads remain")
        return

    def __del__(self):
        """
        When deleted automatically disconnects from KUKA
        """
        self.disconnect()

    def disconnect(self):
        """
        Kills all reading and sending threads\n
        Moves arm to folded position\n
        Disconnects from robot
        """
        if self.connected:
            self.connected = False
            self.move_base()
            self.move_arm(0, 56, -80, -90, 0, 2)
            time.sleep(1)
            self.conn.shutdown(socket.SHUT_RDWR)
            self.conn.close()
            debug(f"robot {self.ip} disconnected")
