import pygame as pg

class Screen:
    def __init__(self, width, height):
        pg.init()
        self.running = True
        self.objects = []
        self.screen = pg.display.set_mode((width, height))
        self.pressed_obj_ind = None
        self.fps = 24
        self.pressed_keys = []
        self.mouse_wheel_pos = 0

    def step(self):
        if self.running:
            self.update_object()
            pg.display.update()
            pg.display.flip()
            self.handle_events()

    def run(self):
        while self.running:
            self.step()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                pg.quit()
                return
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                    pg.quit()
                    return
                else:
                    self.pressed_keys.append(event.key)
            if event.type == pg.KEYUP:
                if event.key in self.pressed_keys:
                    self.pressed_keys.pop(self.pressed_keys.index(event.key))
            if event.type == pg.MOUSEWHEEL:
                self.mouse_wheel_pos += event.y


            elif event.type == pg.MOUSEBUTTONDOWN:
                for obj_ind in range(len(self.objects)):
                    obj = self.objects[obj_ind]
                    if obj.rect.collidepoint(pg.mouse.get_pos()):
                        obj.pressed(pg.mouse.get_pos()[0] - obj.x, pg.mouse.get_pos()[1] - obj.y)
                        self.pressed_obj_ind = obj_ind
            elif event.type == pg.MOUSEBUTTONUP:
                self.pressed_obj_ind = None
            if self.pressed_obj_ind is not None:
                obj = self.objects[self.pressed_obj_ind]
                obj.dragged(pg.mouse.get_pos()[0] - obj.x, pg.mouse.get_pos()[1] - obj.y)
            else:
                for obj_ind in range(len(self.objects)):
                    obj = self.objects[obj_ind]
                    if obj.rect.collidepoint(pg.mouse.get_pos()):
                        obj.hover(pg.mouse.get_pos()[0] - obj.x, pg.mouse.get_pos()[1] - obj.y)

    def add_object(self, obj):
        self.objects.append(obj)
        return self.screen.blit(obj.surf, (obj.x, obj.y))

    def update_object(self):
        for obj_ind in range(len(self.objects)):
            obj = self.objects[obj_ind]
            obj.update()
            obj.rect = self.screen.blit(obj.surf, (obj.x, obj.y))
