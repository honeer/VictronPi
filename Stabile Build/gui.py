# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import serial
import time
import re

# ====== Relay & GPIO Setup ======
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'settings.json')
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
except Exception:
    config = {}

# GPIO & relay
GPIO_OPTIONS = config.get('gpio_options', list(range(2, 28)))
relay_pins    = config.get('relay_pins', [])

# VE.Direct parsing
DISPLAY_TAGS = ['V','I','P','SOC','CE','TTG']
TAG_LABELS   = {
    'V':'Voltage (V)', 'I':'Current (A)', 'P':'Power (W)',
    'SOC':'State of Charge (%)','CE':'Consumed Ah','TTG':'Time to Go'
}
TAG_PATTERN = re.compile(r'^([A-Z0-9]{1,4})\t(.+)$')

# UI constants
off_color    = config.get('off_color','#FF5D62')
on_color     = config.get('on_color','#98BB6C')
btn_bg       = config.get('button_bg','#363646')
nav_bg       = config.get('navbar_bg','#2A2A37')
root_bg      = config.get('root_bg','#16161D')
font_family  = config.get('font_family','Consolas')
font_size    = config.get('font_size',18)
font         = (font_family,font_size)
window_width = config.get('window_width',800)
window_height= config.get('window_height',480)
nav_height   = config.get('navbar_height_px',80)
rows         = config.get('grid_rows',2)
cols         = config.get('grid_cols',4)
gap          = config.get('grid_gap_px',5)
NAV_TAGS     = ['V','SOC','P','TTG']

# Language loader
languages = config.get('languages',{})
current_language = config.get('current_language','English')
def translate(key):
    return languages.get(current_language,{}).get(key,key)

class ToggleGridApp:
    def __init__(self, root):
        self.root = root
        root.title(config.get('window_title','GUI'))
        root.attributes('-fullscreen', True)
        root.bind('<Escape>', lambda e: root.attributes('-fullscreen', False))
        root.configure(bg=root_bg)

        # Relay states
        self.states = [False]*(rows*cols)
        if GPIO_AVAILABLE:
            self._setup_gpio()

        self._init_style()
        self._build_notebook()
        self._build_home_tab()
        self._build_settings_tab()
        self._build_debug_tab()

        threading.Thread(target=self._victron_loop, daemon=True).start()

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for pin in relay_pins[:rows*cols]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)

    def _init_style(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Bottom.TNotebook',
                        tabposition='s',
                        background=root_bg,
                        borderwidth=0)
        style.configure('Bottom.TNotebook.Tab',
                        width=int(window_width/len(translate('pages'))),
                        padding=(0,4),
                        font=(font_family, font_size-4),
                        background=btn_bg,
                        foreground=config.get('nav_text_color','#DCD7DA'),
                        relief='flat')
        style.map('Bottom.TNotebook.Tab',
                  background=[('selected', nav_bg)],
                  foreground=[('selected', on_color)])

    def _build_notebook(self):
        # Create once, thereafter just clear/re-add tabs.
        if not hasattr(self, 'notebook'):
            self.notebook = ttk.Notebook(self.root, style='Bottom.TNotebook')
            self.notebook.pack(fill='both', expand=True)
        else:
            # remove old tabs
            for f in list(self.frames.values()):
                self.notebook.forget(f)
            self.frames.clear()

        self.frames = {}
        for page in translate('pages'):
            frame = tk.Frame(self.notebook, bg=root_bg)
            self.notebook.add(frame, text=page)
            self.frames[page] = frame

    def _build_home_tab(self):
        frame = self.frames[translate('pages')[0]]
        for w in frame.winfo_children(): w.destroy()
        nav_r = nav_height/window_height

        # Top metrics bar
        self.navbar = tk.Frame(frame, bg=nav_bg)
        self.navbar.place(relx=0, rely=0, relwidth=1, relheight=nav_r)
        self.nav_labels = {}
        for idx, tag in enumerate(NAV_TAGS):
            cell = tk.Frame(self.navbar, bg=nav_bg)
            cell.place(relx=idx/len(NAV_TAGS), rely=0,
                       relwidth=1/len(NAV_TAGS), relheight=1)
            tk.Label(cell,
                     text=TAG_LABELS[tag],
                     font=(font_family,10),
                     fg=config.get('info_title_color','#DCD7DA'),
                     bg=nav_bg).place(relx=0.5, rely=0.15, anchor=tk.CENTER)
            lbl = tk.Label(cell, text='--',
                           font=(font_family,24),
                           fg=on_color, bg=nav_bg)
            lbl.place(relx=0.5, rely=0.55, anchor=tk.CENTER)
            self.nav_labels[tag] = lbl

        # Relay grid
        grid = tk.Frame(frame, bg=root_bg)
        grid.place(relx=0, rely=nav_r, relwidth=1, relheight=1-nav_r)
        for r in range(rows):   grid.rowconfigure(r, weight=1)
        for c in range(cols):   grid.columnconfigure(c, weight=1)
        self.buttons = []
        labels = config.get('button_labels',
                            [f'Relay {i+1}' for i in range(rows*cols)])
        for idx in range(rows*cols):
            cell = tk.Frame(grid, bg=btn_bg)
            cell.grid(row=idx//cols, column=idx%cols,
                      padx=gap/2, pady=gap/2, sticky='nsew')
            ind = tk.Frame(cell, bg=off_color, width=20, height=20)
            ind.place(relx=0.95, rely=0.05, anchor=tk.NE)
            lbl = tk.Label(cell, text=labels[idx], font=font,
                           fg=off_color, bg=btn_bg)
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            for w in (cell, ind, lbl):
                w.bind('<Button-1>', lambda e,i=idx: self._toggle(i))
            self.buttons.append((cell, ind, lbl))

    def _build_settings_tab(self):
        frame = self.frames[translate('pages')[2]]
        for w in frame.winfo_children(): w.destroy()

        # scrollable container
        canvas = tk.Canvas(frame, bg=root_bg, highlightthickness=0)
        sb     = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        inner  = tk.Frame(canvas, bg=root_bg)
        inner.bind('<Configure>',
                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        # Language selector
        tk.Label(inner, text=translate('select_language'),
                 font=font, fg=on_color, bg=root_bg).pack(pady=10)
        self.var_lang = tk.StringVar(value=current_language)
        cmb = ttk.Combobox(inner, textvariable=self.var_lang,
                           values=list(languages),
                           state='readonly',
                           font=(font_family,font_size-2))
        cmb.pack(fill='x', padx=20)
        cmb.bind('<<ComboboxSelected>>',
                 lambda e: self._change_language(self.var_lang.get()))

        # Button labels
        tk.Label(inner, text=translate('rename_buttons'),
                 font=font, fg=on_color, bg=root_bg).pack(pady=10)
        self.button_vars = []
        for idx, label in enumerate(config.get('button_labels',[])):
            var = tk.StringVar(value=label)
            self.button_vars.append(var)
            row = tk.Frame(inner, bg=root_bg)
            row.pack(fill='x', padx=20, pady=2)
            tk.Label(row, text=f'Relay {idx+1}:', width=18, anchor='w',
                     font=(font_family,12),
                     fg=config.get('info_title_color','#DCD7DA'),
                     bg=root_bg).pack(side='left')
            tk.Entry(row, textvariable=var, font=(font_family,12)).pack(
                side='left', fill='x', expand=True)

        # GPIO pins
        tk.Label(inner, text=translate('select_gpio'),
                 font=font, fg=on_color, bg=root_bg).pack(pady=10)
        self.pin_vars = []
        for idx in range(rows*cols):
            val = relay_pins[idx] if idx<len(relay_pins) else ''
            var = tk.StringVar(value=str(val))
            self.pin_vars.append(var)
            row = tk.Frame(inner, bg=root_bg)
            row.pack(fill='x', padx=20, pady=2)
            tk.Label(row, text=f'Relay {idx+1} GPIO:', width=18, anchor='w',
                     font=(font_family,12),
                     fg=config.get('info_title_color','#DCD7DA'),
                     bg=root_bg).pack(side='left')
            cb = ttk.Combobox(row, textvariable=var,
                              values=[str(x) for x in GPIO_OPTIONS],
                              state='readonly', font=(font_family,12))
            cb.pack(side='left', fill='x', expand=True)

        tk.Button(inner, text=translate('save_settings'),
                  font=(font_family,14), bg=btn_bg, fg='#FFF', bd=0,
                  command=self._save_settings).pack(pady=20)

    def _build_debug_tab(self):
        frame = self.frames[translate('pages')[3]]
        for w in frame.winfo_children(): w.destroy()
        self.widgets = {}
        for tag in DISPLAY_TAGS:
            row = tk.Frame(frame, bg=root_bg); row.pack(fill='x', padx=20,pady=2)
            tk.Label(row, text=TAG_LABELS[tag], font=(font_family,12),
                     fg=config.get('info_title_color','#DCD7DA'),
                     bg=root_bg).pack(side='left')
            lbl = tk.Label(row, text='--', font=(font_family,14),
                           fg=on_color, bg=root_bg)
            lbl.pack(side='right')
            self.widgets[tag] = lbl

    def _toggle(self, i):
        cell, ind, lbl = self.buttons[i]
        self.states[i] = not self.states[i]
        col = on_color if self.states[i] else off_color
        ind.configure(bg=col); lbl.configure(fg=col)
        if GPIO_AVAILABLE and relay_pins:
            GPIO.output(relay_pins[i],
                        GPIO.LOW if self.states[i] else GPIO.HIGH)

    def _change_language(self, lang):
        global current_language
        current_language = lang
        config['current_language'] = lang
        with open(CONFIG_PATH,'w',encoding='utf-8') as f:
            json.dump(config,f,indent=2)
        # re‐label all tabs & contents
        self._build_notebook()
        self._build_home_tab()
        self._build_settings_tab()
        self._build_debug_tab()

    def _save_settings(self):
        # 1) gather
        new_labels = [v.get() for v in self.button_vars]
        new_pins   = [int(v.get()) for v in self.pin_vars]
        new_lang   = self.var_lang.get()

        # 2) update globals
        global relay_pins, current_language
        relay_pins       = new_pins
        current_language = new_lang

        # 3) persist config
        config.update({
            'button_labels':    new_labels,
            'relay_pins':       new_pins,
            'current_language': new_lang
        })
        with open(CONFIG_PATH,'w',encoding='utf-8') as f:
            json.dump(config,f,indent=2)

        # 4) live‐update Home labels
        for idx, (_,_,lbl) in enumerate(self.buttons):
            lbl.configure(text=new_labels[idx])

        # 5) re‐setup GPIO, rebuild all tabs
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            self._setup_gpio()
        self._build_notebook()
        self._build_home_tab()
        self._build_settings_tab()   # ◀️ ensure Settings is repopulated
        self._build_debug_tab()

        messagebox.showinfo('', translate('settings_saved'))

    def _victron_loop(self):
        try:
            ser = serial.Serial(config.get('victron_port','/dev/ttyUSB0'),
                                config.get('victron_baud',19200),
                                timeout=config.get('victron_timeout',0.1))
        except:
            return
        while True:
            raw = ser.readline()
            if not raw:
                time.sleep(config.get('victron_poll_interval_ms',100)/1000.0)
                continue
            line = raw.decode('ascii','ignore').strip()
            m = TAG_PATTERN.match(line)
            if not m: continue
            key,val = m.groups()
            text = val
            try:
                num = float(val)
                if key=='V':   text=f"{num/1000:.1f}"
                elif key=='I': text=f"{num/1000:.2f}"
                elif key=='P': text=f"{num:.0f}"
                elif key=='SOC': text=f"{num/10:.1f}%"
                elif key=='CE':  text=f"{num/1000:.1f} Ah"
                elif key=='TTG':
                    t=int(num)
                    text = ('--' if t<0 else
                            f"{t} m" if t<60 else
                            f"{t/60:.1f} h" if t<1440 else
                            f"{t/1440:.1f} d")
            except:
                pass

            if key in self.widgets:
                self.root.after(0, lambda k=key,t=text:
                                self.widgets[k].config(text=t))
            if key in self.nav_labels:
                self.root.after(0, lambda k=key,t=text:
                                self.nav_labels[k].config(text=t))

def main():
    root = tk.Tk()
    app  = ToggleGridApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
