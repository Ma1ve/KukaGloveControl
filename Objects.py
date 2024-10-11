import pygame as pg


def range_cut(mi, ma, val):
    return min(ma, max(mi, val))


def convert_range(new_min, new_max, old_min, old_max, old_value):
    old_range = (old_max - old_min)
    new_range = (new_max - new_min)
    return (((old_value - old_min) * new_range) / old_range) + new_min


class NoCvMatSet(Exception):
    """Raised when no cv mat set for object of class Mat"""
    pass


class Button:
    def __init__(self, par_surf, /,
                 x=0,
                 y=0,
                 width=100,
                 height=10,
                 func=lambda *args: args,
                 color=(100, 100, 100)):
        self.par_surf = par_surf
        self.func = func
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.surf = pg.Surface((self.width, self.height))
        self.surf.fill(self.color)
        self.rect = par_surf.add_object(self)

    def pressed(self, *args):
        self.func(args)

    def dragged(self, *args):
        pass

    def hover(self, *args):
        pass

    def update(self):
        pass


class Text:
    def __init__(self, par_surf, /,
                 x=0,
                 y=0,
                 inp_text=lambda *args: "your text",
                 font='serif',
                 font_size=10,
                 func=lambda *args: args,
                 color=(255, 255, 255)):
        self.par_surf = par_surf
        self.func = func
        self.x = x
        self.y = y
        self.inp_text = inp_text
        self.text = inp_text
        self.color = color
        self.text = pg.font.SysFont(font, font_size)
        self.surf = self.text.render(self.inp_text(), False, self.color)
        self.rect = par_surf.add_object(self)

    def pressed(self, *args):
        self.func(args)

    def dragged(self, *args):
        pass

    def hover(self, *args):
        pass

    def update(self):
        self.surf = self.text.render(self.inp_text(), False, self.color)


class Slider:
    def __init__(self, par_surf, /,
                 x=0,
                 y=0,
                 width=100,
                 height=10,
                 func=lambda *args: args,
                 color=(100, 100, 100),
                 slider_color=(255, 255, 255),
                 min=0,
                 max=100,
                 val=None):

        self.par_surf = par_surf
        self.func = func
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.slider_color = slider_color
        self.min = min
        self.max = max

        self.slider_rad = self.height // 2
        self.slider_y = self.slider_rad
        self.surf = pg.Surface((self.width, self.height))

        if val:
            self.val = val
        else:
            self.val = self.min

        self.slider_x = convert_range(self.slider_rad, self.width - self.slider_rad, self.min, self.max, self.val)

        pg.draw.rect(self.surf, self.color, (0, 0, self.width, self.height), border_radius=self.height // 2)
        pg.draw.circle(self.surf, (255, 255, 255), (self.slider_x, self.slider_y), self.slider_rad)
        # self.surf.fill(self.color)
        self.rect = par_surf.add_object(self)

    def set_val(self, val):
        self.slider_x = convert_range(self.slider_rad, self.width - self.slider_rad, self.min, self.max, val)

    def pressed(self, *args):
        pass

    def dragged(self, *args):
        self.slider_x = range_cut(self.slider_rad, self.width - self.slider_rad, args[0])
        self.val = convert_range(self.min, self.max, self.slider_rad, self.width - self.slider_rad, self.slider_x)
        self.func(self.val)

    def hover(self, *args):
        pass

    def update(self):
        pg.draw.rect(self.surf, self.color, (0, 0, self.width, self.height), border_radius=self.height // 2)
        pg.draw.circle(self.surf, (255, 255, 255), (self.slider_x, self.slider_y), self.slider_rad)


class Mat:
    def __init__(self, par_surf, /,
                 func=lambda *args: args,
                 x=0,
                 y=0,
                 cv_mat_stream=None):
        self.par_surf = par_surf
        self.x = 0
        self.y = 0
        self.func = lambda *args: args
        self.is_mat_stream = False
        self.last_hover_pos = (0, 0)
        self.is_pressed = False

        self.func = func
        self.x = x
        self.y = y

        if cv_mat_stream:
            self.cv_mat_stream = cv_mat_stream
        else:
            raise NoCvMatSet
        self.rect = par_surf.add_object(self)

    @property
    def surf(self):
        mat = self.cv_mat_stream()
        surf = pg.transform.flip(pg.transform.rotate(pg.surfarray.make_surface(mat), -90), 1, 0)
        return surf

    def update(self):
        self.func(self.last_hover_pos, self.is_pressed)

    def pressed(self, *args):
        self.last_hover_pos = args
        self.is_pressed = True

    def dragged(self, *args):
        self.is_pressed = True
        self.last_hover_pos = args
        pass

    def hover(self, *args):
        self.last_hover_pos = args
        self.is_pressed = False
