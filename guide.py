import tkinter as Tk
import tkinter.ttk as ttk
from tkinter import messagebox
import json
import socket
from const import *
import random

launchArg: dict = {"mode": "none",
                   "ip": "127.0.0.1",
                   "port": 0}

launchArg_history: dict = configuration.initializeSettings

def writeSettings() -> None:
    with open(".\\configs\\initializeSettings.json", "w") as f:
        json.dump(launchArg, f)

def singlePlayer() -> None:
    launchArg["mode"] = "single"
    tk.destroy()

def multiPlayer() -> bool:
    try:
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    launchArg["mode"] = "multi"
    launchArg["ip"] = ip
    launchArg["port"] = random.randint(1000, 9999)
    if ipEntry.get() != "" and portEntry.get() != "":
        launchArg["ip"] = ipEntry.get()
        launchArg["port"] = int(portEntry.get())
        writeSettings()
        messagebox.showinfo("Gaming Argument", f"You will join a game at {launchArg['ip']}:{launchArg['port']}")
    else:
        messagebox.showinfo("Gaming Argument", f"Please fill the IP and port to join a game")
        return False
    tk.destroy()
    return True

tk = Tk.Tk()
tk.title("Gameguide")
tk.resizable(0, 0)

ttk.Label(tk, text="Airwar Game Guide",justify='center').grid(row=0,column=0,columnspan=999)
ttk.Button(tk, text="Single Player",command=singlePlayer).grid(row=1,column=0)
ttk.Button(tk, text="Multi-Player",command=multiPlayer).grid(row=1,column=1)

ttk.Label(tk, text="IP & Port", justify='center').grid(row=2,column=0)
ipEntry =  ttk.Combobox(tk, values=["127.0.0.1","localhost"])
ipEntry.grid(row=2,column=1)
portEntry =  ttk.Entry(tk,width=5)
portEntry.grid(row=2,column=2)

def gameguide() -> None:
    if 'ip' in launchArg_history:
        ipEntry.set(launchArg_history['ip'])
    if 'port' in launchArg_history:
        portEntry.insert(0, str(launchArg_history['port']))
    tk.mainloop()
