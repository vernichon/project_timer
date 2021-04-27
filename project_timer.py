import tkinter as tk
from tkinter import ttk
from datetime import time, timedelta, datetime
from nptime import nptime
from pathlib import Path
import odoorpc
import configparser
VERSION = "0.8" 
config = configparser.ConfigParser()
home = Path.home()
timer_ini = home / "timer.ini"
if Path(timer_ini).exists():
    config.read(timer_ini)


class TimerView(tk.Frame):
    customer_select_id = None
    task_select_id = None
    state = None
    odoo_status = None
    customers_array = []
    customers = {}
    tasks_array = []
    tasks = {}
    oe = None
    duration = nptime(0, 0, 0)

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        style = ttk.Style()

        style.configure("BW.TLabel", foreground="red", background="white")

        button_red_style = ttk.Style()  # style for button1
        button_red_style.configure('red.TButton', foreground='red')
        button_connect_style = ttk.Style()  # style for button1
        button_red_style.configure('connect.TButton', foreground='red')

        self.task_name = tk.StringVar()
        self.task_name.set("/")
        self.label = ttk.Label(text="00:00:00", font=('Helvetica', 48), style="BW.TLabel")
        self.label_description = ttk.Label(text="Description", font=('Helvetica', 18))
        self.description = ttk.Entry(textvariable=self.task_name, font=('Helvetica', 18))
        self.label_log = ttk.Label(text="", font=('Helvetica', 18), style="BW.TLabel")
        self.version_log = ttk.Label(text="Version : %s" % VERSION, font=('Helvetica', 18), style="BW.TLabel")
        self.label_selection_config = ttk.Label(text="Odoo Config", font=('Helvetica', 18))
        self.selection_client = ttk.Combobox(values=self.customers_array)
        self.selection_config = ttk.Combobox(values=config.sections())
        self.selection_config.current(0)
        self.selection_client.bind('<<ComboboxSelected>>', self.client_select)

        self.selection_task = ttk.Combobox(values=self.tasks_array)
        self.selection_task.bind('<<ComboboxSelected>>', self.task_select)
        self.button_start = ttk.Button(text="Start", command=self.start)
        self.button_connect = ttk.Button(text="Connection", command=self.connect_odoo, style="connect.TButton")
        self.button_stop = ttk.Button(text="Stop", command=self.stop)
        self.button_reset = ttk.Button(text="Reset", command=self.reset)
        self.button_save = ttk.Button(text="Save", command=self.save, style='red.TButton')
        self.selection_client.place(x=20, y=25)
        self.label_description.place(x=20, y=65)
        self.description.place(x=120, y=65)
        self.selection_task.place(x=200, y=25)
        self.label.place(x=500, y=20)
        self.button_reset.place(x=220, y=150)
        self.button_stop.place(x=120, y=150)
        self.button_start.place(x=20, y=150)
        self.button_save.place(x=420, y=150)
        self.label_log.place(x=20, y=200)
        self.label_selection_config.place(x=20, y=250)
        self.selection_config.place(x=180, y=250)
        self.button_connect.place(x=390, y=250)
        self.version_log.place(x=520, y=250)
        self.focus_set()
        self.selection_client.focus_force()

    def connect_odoo(self):
        self.tasks = {}
        section = self.selection_config.get()
        serveur = config[section]['server']
        port = config[section]['port']
        protocol = config[section]['protocol']
        user = config[section]['user']
        password = config[section]['password']
        db = config[section]['db']
        try:
            self.oe = odoorpc.ODOO(serveur, port=port, protocol=protocol)
        except:
            self.label_log.configure(text="Serveur indisponible")
            return False
        self.oe.login(db, user, password)

        if self.oe.env.uid:
            tasks_odoo = self.oe.env['project.task'].search_read([('partner_id', '!=', False)], fields=['name', 'partner_id'])
            style = ttk.Style(self)
            style.map('connect.TButton',
                      foreground=[('focus', 'green'), ('!focus', 'green')])
            self.button_connect.configure(text="re-connect")

            for t in tasks_odoo:
                task_name = t['name']
                if t['partner_id'][1] not in self.customers:
                    self.customers_array.append(t['partner_id'][1])
                    self.customers[t['partner_id'][1]] = t['partner_id'][0]

                if not t['partner_id'][1] in self.tasks:
                    self.tasks[t['partner_id'][1]] = []
                self.tasks[t['partner_id'][1]].append({'name': task_name, 'id': t['id']})

            self.tasks_array.sort()
            self.customers_array.sort()
            self.selection_client['values'] = self.customers_array
            self.selection_client.current(0)
            self.client_select()
            self.label_log.configure(text="Connection ok uid= %s " % self.oe.env.uid)
        else:
            self.label_log.configure(text="erreur de connection")

    def client_select(self, event=None):
        customer_select = self.customers_array[self.selection_client.current()]
        self.tasks_array = [x['name'] for x in self.tasks[customer_select]]
        self.selection_task.set('')
        self.selection_task['values'] = self.tasks_array

    def task_select(self, event):
        self.customer_select = self.customers_array[self.selection_client.current()]
        self.customer_select_id = self.customers[self.customer_select]
        self.task_select_id = self.tasks[self.customer_select][self.selection_task.current()]['id']

    def save(self):
        if self.state == 'stopped':
            task_id = self.task_select_id
            name = self.task_name.get()

            value_duration = self.duration.hour
            minutes = self.duration.minute + (self.duration.second / 60.0)
            value_duration = value_duration + (minutes / 60.0)
            if value_duration > 0:
                data = {'task_id': task_id, 'name': name, 'unit_amount': value_duration}
                try:
                    res_id = self.oe.env['account.analytic.line'].create(data)
                    self.label_log.configure(text="Entrée %s créé" % res_id)
                    self.reset()
                except Exception as e:
                    self.label_log.configure(text=e)

        else:
            self.label_log.configure(text="Une durée doit être définie")

    def start(self):
        if not self.customer_select_id or not self.customer_select_id:
            self.label_log.configure(text="Vous devez selectionner une tache !")
            return False
        self.state = "started"
        self.update_clock()

    def stop(self):
        self.after_cancel(self.after_id)
        self.state = "stopped"

    def reset(self):
        self.after_cancel(self.after_id)
        self.duration = nptime(0, 0, 0)
        now = self.duration.strftime("%H:%M:%S")
        self.label.configure(text=now)
        self.state = None

    def update_clock(self):
        if self.duration:
            self.duration = self.duration + timedelta(seconds=1)
        else:
            self.duration = nptime(0, 0, 0)
        now = self.duration.strftime("%H:%M:%S")
        self.label.configure(text=now)
        self.after_id = self.after(1000, self.update_clock)


class Clock(tk.Tk):
    start = None
    after_id = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set the window properties
        self.title("Timer Odoo")
        self.geometry("800x300")
        self.resizable(width=False, height=False)

        # Define the UI
        TimerView(self).grid(sticky=(tk.E + tk.W + tk.N + tk.S))
        self.columnconfigure(0, weight=1)


if __name__ == '__main__':
    app = Clock()
    app.mainloop()
