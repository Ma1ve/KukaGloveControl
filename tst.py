

# import cv2
# import numpy as np

# # robot
# center_x = 640 // 2
# center_y = 480 // 2
# circle_radius = 50

# cap = cv2.VideoCapture(0)
# while True:


#   flag, img = cap.read()

#   cv2.waitKey(1)

#   hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
#   lower_blue = np.array([0, 69, 114])
#   upper_blue = np.array([31 ,255, 255])

#   # Создание маски для изображения, на которой белым выделены области синего цвета
#   mask = cv2.inRange(hsv, lower_blue, upper_blue)
  
#   # Нахождение контуров объектов на маске
#   contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  
#   # Отрисовка контуров вокруг объектов синего цвета на оригинальном изображении
#   for contour in contours:
#       area = cv2.contourArea(contour)
#       if area > 200:  # Исключаем маленькие контуры

#           # Находим координаты ограничивающего прямоугольника
#           x, y, w, h = cv2.boundingRect(contour)
#           # Рисуем прямоугольник вокруг контура
#           if w > 150 and h > 150: 

#             cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)

#             # Вычисляем координаты центра
#             fx, fy = x + w // 2, y + h // 2
#             pos = [fx, fy]

#             cv2.putText(img, str(pos), (fx+15, fy-15), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2 )


#             direction_text = ""
            
#             # Проверяем, находится ли центр объекта внутри круга
#             distance_to_center = np.sqrt((fx - center_x) ** 2 + (fy - center_y) ** 2)
#             if distance_to_center <= circle_radius:
#                 # Если центр объекта внутри круга, меняем цвет круга
#                 cv2.circle(img, (center_x, center_y), circle_radius, (0, 255, 0), 2)  # Зеленый круг
#                 direction_text = "CENTER"
#             else:
#                 cv2.circle(img, (center_x, center_y), circle_radius, (0, 0, 255), 2)  # Красный круг
            
#                 if fx < center_x:
#                   direction_text += "LEFT "
#                 elif fx > center_x:
#                   direction_text += "RIGHT "
                    
#                 if fy < center_y:
#                   direction_text += "UP"
#                 elif fy > center_y:
#                   direction_text += "DOWN"

#             # Выводим текст с координатами объекта
#             cv2.putText(img, str(pos), (fx+15, fy-15), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2 )

#             cv2.putText(img, direction_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

#   cv2.imshow("Image", img)
  
#   if cv2.waitKey(100) & 0xFF == ord('q'):
#     break

import cv2

# Загрузка предварительно обученной модели для обнаружения нижней части тела
legs_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_lowerbody.xml')

# Подключение к камере
cap = cv2.VideoCapture(0)

while True:
    # Считывание кадра с камеры
    ret, frame = cap.read()
    
    if not ret:
        break

    # Преобразование кадра в оттенки серого
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Обнаружение нижней части тела (ног) на кадре
    legs = legs_cascade.detectMultiScale(gray, 1.1, 4)

    # Обведение ног в прямоугольник
    for (x, y, w, h) in legs:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Отображение результата
    cv2.imshow('Detected Legs', frame)

    # Для выхода из цикла по нажатию клавиши 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Освобождение ресурсов
cap.release()
cv2.destroyAllWindows()


# import numpy as np
# import cv2

# cap = cv2.VideoCapture(0)
# face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
# eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# while True:
#     ret, frame = cap.read()

#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     faces = face_cascade.detectMultiScale(gray, 1.3, 5)
#     for (x, y, w, h) in faces:
#         cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 5)
#         roi_gray = gray[y:y+w, x:x+w]
#         roi_color = frame[y:y+h, x:x+w]
#         eyes = eye_cascade.detectMultiScale(roi_gray, 1.3, 5)
#         for (ex, ey, ew, eh) in eyes:
#             cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 5)

#     cv2.imshow('frame', frame)

#     if cv2.waitKey(1) == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()
