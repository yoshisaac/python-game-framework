from Xlib import display, X, XK, Xutil, Xatom, ext
import threading
import time
import math
import subprocess

import sprites
import key_struct

from log import log

class window:
    window_is_open:bool = False;
    window_width:int = 0;
    window_height:int = 0;

    stop_render_loop:bool = True;

    sprites_array = [];

    keys = [];
    
    def __init__(self):
        log.printg("game_framework.__init__() -> window.__init__(): called");
        self.display = display.Display();
        self.screen = self.display.screen();
        self.root_window = self.screen.root;
        self.keys = self.display.query_keymap();
        self.window_fps = (1000*1000)/float(subprocess.check_output("xrandr | grep \"\\*\" | awk {\'print $2\'} | grep -Eo \'[0-9.0-9]+\'", shell=True, text=True))/(1000000);
    
    def create_win(self, width:int=250, height:int=250, resizable:bool=False, title:str=""):
        if self.window_is_open == True:
            log.printy("game_framework.spawn_window() -> window.create_win(): window already created");
            return;
        self.window = self.root_window.create_window(0,0,width,height,1,
                                                     self.screen.root_depth,
                                                     X.InputOutput,
                                                     X.CopyFromParent,
                                                     event_mask=X.ExposureMask | X.KeyPressMask
                                                     );
        if resizable == False:
            size_hints = {
                'flags': Xutil.PMinSize | Xutil.PMaxSize,
                'min_width': width,
                'min_height': height,
                'max_width': width,
                'max_height': height
            }
            self.window.set_wm_normal_hints(size_hints);
        self.window_height = height;
        self.window_width = width;
        self.window.map();
        self.window_is_open = True;
        self.stop_render_loop = False;
        self.display.flush();
        self.render_thread = threading.Thread(None, self.render_loop);
        self.render_thread.start();
        return;
        
    def render_loop(self):
        log.printg("game_framework.spawn_window() -> window.create_win() -> window.render_loop(): entered")
        while True:
            if self.stop_render_loop == True:
                break;            
            #primary render loop

            self.keys = self.display.query_keymap(); #refresh the key map on the window thread

            self.window_width  = self.window.get_geometry()._data['width'];
            self.window_height = self.window.get_geometry()._data['height'];

            #allocate the graphics context and pixmap
            pixmap = self.window.create_pixmap(self.window_width, self.window_height, self.screen.root_depth)
            gc = pixmap.create_gc(
                foreground = self.screen.black_pixel,
                background = self.screen.white_pixel,
                line_width = 2,
                line_style = X.LineSolid,
                cap_style  = X.CapButt,
                join_style = X.JoinMiter
            );
    
            #draw background
            gc.change(foreground=self.screen.white_pixel); #TODO: make the native background color customizable
            pixmap.fill_rectangle(gc,0,0,self.window_width,self.window_height);

            #draw the sprites
            for sprite in self.sprites_array:
                if sprite.index == -1:
                    self.sprites_array.remove(sprite);
                    continue;
                
                self.change_gc_color(gc,
                                     sprite.color[0],
                                     sprite.color[1],
                                     sprite.color[2]);

                if type(sprite) == sprites.Line:
                    gc.change(line_width=sprite.width,
                              line_style=sprite.style);
                    pixmap.line(gc,
                                sprite.x1, sprite.y1,
                                sprite.x2, sprite.y2,
                                );                    
                elif type(sprite) == sprites.Rectangle:
                    if sprite.filled == False:
                        gc.change(line_width=sprite.edge_width,
                                  line_style=X.LineSolid);
                        pixmap.rectangle(gc,
                                         sprite.x, sprite.y,
                                         sprite.width, sprite.height
                                         );
                    elif sprite.filled == True:
                        pixmap.fill_rectangle(gc,
                                              sprite.x, sprite.y,
                                              sprite.width, sprite.height
                                              );
                elif type(sprite) == sprites.Text:
                    pixmap.draw_text(gc,
                                     sprite.x, sprite.y,
                                     sprite.text
                                     );
            #swap the pixmap buffer to the window graphics 
            self.window.copy_area(gc, pixmap, 0, 0, self.window_width, self.window_height, 0, 0);
            time.sleep(self.window_fps); #magic number (causes it to loop at roughly 300 frames per second)
            #free the graphics context and pixmap
            gc.free();
            pixmap.free();
            self.display.flush();
        log.printg("game_framework.spawn_window() -> window.create_win() -> window.render_loop(): exited");
        return;

    def is_x11_key_down(self, key:int) -> bool:
        keycodemap = self.display.keysym_to_keycodes(key);
        keycode = list(keycodemap)[0][0]
        return ((self.keys[keycode//8]) & (1 << (keycode % 8)) != 0);

    def get_x11_arrow_keys_down(self):
        return key_struct.Arrow_keys(
            (self.keys[13] & 128 != 0), #up
            (self.keys[14] & 16  != 0), #down
            (self.keys[14] & 2   != 0), #left
            (self.keys[14] & 4   != 0) #right
        );
    
    def custom_draw_x11_line(self, x1:int, y1:int, x2:int, y2:int):
        """
        delta_x:int = sprite.x2-sprite.x1;
        if delta_x == 0:
            delta_x = 0.00000001;
        delta_y:int = sprite.y2-sprite.y1;
        if delta_y == 0:
            delta_y = 0.00000001;
        """
        #f(x) = mx+b
        #m:float = (delta_y/delta_x)
        """
        for x in range(sprite.x2-sprite.x1):
            y:int = int(m*x)
            pixmap.point(gc,
                         x, y
        );

                
        for y in range(sprite.y2-sprite.y1):
            x:int = int(y/m)
            pixmap.point(gc,
                        x, y
        );
        """    

        
        
    def create_x11_line_with_color(self, x1:int, y1:int, x2:int, y2:int, color:int=[0,0,0], width:int=2, style:str="solid"):
        line = sprites.Line(len(self.sprites_array), x1, y1, x2, y2, color, width, style);
        self.sprites_array.append(line);
        return line;

    def create_x11_rectangle_with_color(self, x:int, y:int, width:int, height:int, color:int=[0,0,0], filled:bool=True, edge_width:int=2):
        rectangle = sprites.Rectangle(len(self.sprites_array), x, y, width, height, color, filled, edge_width);
        self.sprites_array.append(rectangle);
        return rectangle;

    def create_x11_text_with_color(self, x:int, y:int, text:str, color:int=[0,0,0]):
        text = sprites.Text(len(self.sprites_array), x, y, text, color);
        self.sprites_array.append(text);
        return text;
        
    def change_gc_color(self, gc, red:int, green:int, blue:int):
        if red > 255 or green > 255 or blue > 255:
            log.printy("window.change_gc_color(): invalid color range");
            return;
        colormap = self.root_window.create_colormap(self.screen.root_visual, X.AllocNone);
        color = colormap.alloc_color(int((red/255) * 65535),
                                     int((green/255) * 65535),
                                     int((blue/255) * 65535));
        colormap.free();
        gc.change(foreground=color.pixel);

    def get_window_resolution(self) -> tuple:
        return (self.window_width, self.window_height);
        
    def elegant_exit(self):
        log.printr("game_framework.stop_game() -> window.elegant_exit(): called")
        if self.stop_render_loop != True:
            self.stop_render_loop = True;
            log.printr("game_framework.stop_game() -> window.elegant_exit(): waiting for window.render_loop() to stop")
            self.render_thread.join();
            log.printr("game_framework.stop_game() -> window.elegant_exit(): window.render_loop() stopped")
        else:
            log.printy("game_framework.stop_game() -> window.elegant_exit(): window.render_loop() is probably already stopped")
        self.window.destroy();
        self.display.close();



