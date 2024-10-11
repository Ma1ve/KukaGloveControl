# Краткий обзор класса KUKA (Python)/(User manual):
____
Класс KUKA написан для удобной работы с роботом KUKA youbot с помощью языка программирования Python. В классе есть несколько основных методов для управления роботом.

source: https://github.com/MarkT5/KUKAyoubot_lib
____
## Параметры при создании элемента класса
___ip___ _(str)_: robot ip

___pwd___ _(str)_: password for ssh connection

___ssh___ _(bool)_: whether to connect to SSH or not

___ros___ _(bool)_: force restart of youbot_tl_test on KUKA if true

___offline___ _(bool)_: toggles offline mode (doesn't try to connect to robot)

___read_depth___ _(bool)_: if false doesn't start depth client

___camera_enable___ _(bool)_: enables mjpeg client if True

___advanced___ _(bool)_: disables all safety checks in the sake of time saving

___log___ _[(str), (int)]_: [path, freq] logs odometry and lidar data to set path with set frequency

___read_from_log___ _[(str), (int)]_: [path, freq] streams odometry and lidar data from set log path with set frequency
___
## Основные Методы

___move_arm(...)___ — Sets arm position

ways to set arm position:

array of values:
- (joint 1, joint 2, joint 3, joint 4, joint 5, grip) - degrees from upright position
        
by keywords:
- ___m1, m2, m3, m4, m5___ - for joints __(all joint parameters are relative and in degrees from upright position)__
- ___grip___ - (0 - 2) for grip
     

___move_base(f, s, ang)___ — принимает:

1. ___f___ — скорость движения вдоль оси по которой направлен робот, если положительное — движение вперёд, если отрицательное — назад,
2. ___s___ — скорость движения поперёк оси по которой направлен робот
3. ___ang___ — угловая скорость
если вызвать этот метод без указания аргументов, то будет отправлена команда остановки

___go_to(x, y, ang)___ — отправляет робота по координатам x, y и задаёт угол от оси x до направления робота (в метрах)

___post_to_send_data(ind, msg)___ — Записывает сообщение msg в ячейку отправки ind (используется другими методами для общения с роботом, но также может использоваться для отправки пользовательских команд, если вызвана с индексом 3. 0 — скорости платформы, 1 — положения манипулятора, 2 — положение захвата)


___camera/camera_BGR()___ _returns: (cv2.Mat)_- возвращает изображение в специальном сжатом формате

___depth_camera()___ _returns: (cv2.Mat)_ — возвращает изображение с depth камеры

### Properties:
___arm___ _returns: float[6]_ — arm_id, joint 1 - joint 5 

___wheels___ _returns: float[4]_ — wheel 1 - wheel 4

___lidar___ _returns: ([float[3], float[lidar_resolution]])_— возвращает массив длиной 623 с расстояниями до точек равномерно распределённых от 0 до 240 градусов и данные одометрии скрепленные с этим измерением

___increment___ _(returns: float[3])_ — возвращает массив с положениями по оси x, y и угла от оси x до направления робота


## SSH:
___
___send(msg)___ msg (string) - отправить команду через SSH

___send_recv(msg)___ msg (string) - отправить команду через SSH и дождаться её завершения
___send_wait(msg_send, wait_msg, timeout=None, timeout_msg=None, verbose=0, max_time=20):___
- msg_send (string)- сообщение на отправку
- wait_msg (string)- ответ, которое будет ожидаться
- timeout (int)- максимальное время ожидания следующего ответа
- timeout_msg (string)-сообщение, которое будет напечатано в командную строку при привышении времени ожидания
- verbose (int)- 0-не печатать информацию, 1-печататать только важное, 2-печатать все полученные ответы
___
### подробнее - читай dock-string