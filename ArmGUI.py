import pygame
import sys
import pygame_gui
import time




class ButtonWindow:
    
    def __init__(self, arm, width, height):
        
        self.arm = arm
        self.width = width
        self.height = height

        # Инициализация Pygame
        pygame.init()

        # Установка размеров окна
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Arduino GUI for KUKAYouBot')


        self.manager = pygame_gui.UIManager((self.width, self.height))

        # Создание текстовых полей и надписей
        # self.create_text_fields()

        # Кнопка
        self.button_start_record = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.width/2 - 75 - 150 / 2, self.height - 100), (150, 50)),
            text='RECORD',
            manager=self.manager)
        
        self.button_stop_record= pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.width/2 + 75 - 150 / 2, self.height - 100), (150, 50)),
            text='STOP RECORD',
            manager=self.manager)

        # Кнопка возвращающая робота в исходное положение 
        self.button_base_position = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((self.width/2 - 125, self.height-200), (250, 50)), text='Camera capture', manager=self.manager)

        self.clock = pygame.time.Clock()


    def handle_record_button_click(self):
      self.arm.setRecordStart(True)

    def handle_stop_record_button_click(self): 
      self.arm.setRecordStart(False)
    
        
    def create_text_fields(self):

         # Удаление предыдущих элементов, если они существуют
        if hasattr(self, 'mainLabelText'):
            self.mainLabelText.kill()
        if hasattr(self, 'labelQueue'):
            self.labelQueue.kill()

        mainText = pygame.font.SysFont("bahnschrift", 24).render('KUKA GUI FOR ARDUINO ARM.', True, (0, 0, 0)) 
        mainTextRect = mainText.get_rect(center=(self.width/2, self.height/4))
        # Установка изображение текста как текст вашего элемента UILabel
        self.mainLabelText = pygame_gui.elements.UILabel(relative_rect=mainTextRect, text='', manager=self.manager)
        self.mainLabelText.set_image(mainText)

        textQueue =  pygame.font.SysFont("bahnschrift", 24).render("Queue:" + " " + f'{self.arm.lengthQueue()}', True, (0, 0, 0)) 
        textQueueRect = textQueue.get_rect(center=(self.width/2, self.height/3))
        self.labelQueue = pygame_gui.elements.UILabel(relative_rect=textQueueRect, text='', manager=self.manager)
        self.labelQueue.set_image(textQueue)
             
  
    def run(self):
        running = True
        while running:
            
            self.screen.fill("white")

            self.create_text_fields()

            #! Инициализация руки
            self.arm.control_servos() 

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False                    
                elif event.type == pygame.USEREVENT and 'queue_changed' in event.dict:
                    # Обновление элементов интерфейса
                    self.create_text_fields()

               # Проверяем, была ли нажата кнопка "RECORD"
                elif event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.button_start_record:
                # Вызываем обработчик события для кнопки "RECORD STOP"
                  self.handle_record_button_click()

                elif event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.button_stop_record: 
                    self.handle_stop_record_button_click()

                elif event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.button_base_position: 
                    self.arm.setIsCameraRun(True)

                self.manager.process_events(event)

            # UI_REFRESH_RATE

            self.manager.update(self.clock.tick(60) / 1000)
            self.manager.draw_ui(self.screen)

            pygame.display.update()
        

        pygame.quit()
        sys.exit()




