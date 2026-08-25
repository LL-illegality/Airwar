import tkinter as Tk
import tkinter.ttk as ttk
from tkinter import messagebox
import json
import socket
from const import *
import random

launchArg: dict = {"mode": "none",
                   "ip": "127.0.0.1",
                   "port": 0,
                   "playerName": "{default}",
                   "showTutorial": True,
                   "fullscreen": True,}

launchArg_history: dict = configuration.initializeSettings

def writeSettings() -> None:
    with open(".\\configs\\initializeSettings.json", "w") as f:
        json.dump(launchArg, f)

def getCurrIp() -> str:
    ip = "127.0.0.1"
    s: socket.socket | None = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        if s is not None:
            s.close()
    return ip

def getCurrIpv6() -> str:
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.connect(('2001:4860:4860::8888', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ''

def singlePlayer() -> None:
    launchArg["mode"] = "single"
    launchArg["ip"] = ipEntry.get()
    launchArg["port"] = int(portEntry.get())
    launchArg["playerName"] = playerNameEntry.get()
    if launchArg["playerName"] == "":
            launchArg["playerName"] = "{default}"
    launchArg["showTutorial"] = launchArg_history["showTutorial"]
    launchArg["fullscreen"] = bool(fullscreenVar.get())
    writeSettings()
    tk.destroy()

def multiPlayer() -> bool:
    if ipEntry.get() != "" and portEntry.get() != "":
        launchArg["ip"] = ipEntry.get()
        launchArg["port"] = int(portEntry.get())
        launchArg["playerName"] = playerNameEntry.get()
        launchArg["mode"] = "multi"
        if launchArg["playerName"] == "":
            launchArg["playerName"] = "{default}"
        launchArg["showTutorial"] = launchArg_history["showTutorial"]
        launchArg["fullscreen"] = bool(fullscreenVar.get())
        writeSettings()
        messagebox.showinfo("Gaming Argument", f"You will join a game at {launchArg['ip']}:{launchArg['port']}")
    else:
        messagebox.showinfo("Gaming Argument", f"Please fill the IP and port to join a game")
        return False
    tk.destroy()
    return True

tk = Tk.Tk()
tk.title("Gameguide")
tk.resizable(False, False)

ttk.Label(tk, text="Airwar Game Guide",justify='center').grid(row=0,column=0,columnspan=999)
ttk.Button(tk, text="Single Player",command=singlePlayer).grid(row=1,column=0)
ttk.Button(tk, text="Multi-Player",command=multiPlayer).grid(row=1,column=1)

ttk.Label(tk, text="Player Name", justify='center').grid(row=2,column=0)
playerNameEntry = ttk.Entry(tk, width=28)
playerNameEntry.grid(row=2,column=1,columnspan=999)

ttk.Label(tk, text="IP & Port", justify='center').grid(row=3,column=0)
ipv6 = getCurrIpv6()
cb_values = ["127.0.0.1", "localhost", getCurrIp()]
if ipv6:
    cb_values.append(ipv6)
ipEntry =  ttk.Combobox(tk, values=cb_values)
ipEntry.grid(row=3,column=1)
portEntry =  ttk.Entry(tk,width=5)
portEntry.grid(row=3,column=2)

fullscreenVar = Tk.BooleanVar(value=True)
ttk.Checkbutton(tk, text="Fullscreen", variable=fullscreenVar).grid(row=4,column=0)

def gameguide() -> None:
    if 'ip' in launchArg_history:
        ipEntry.set(launchArg_history['ip'])
    if 'port' in launchArg_history:
        portEntry.insert(0, str(launchArg_history['port']))
    if 'playerName' in launchArg_history:
        playerNameEntry.insert(0, launchArg_history['playerName'])
    else:
        playerNameEntry.insert(0, "{default}")
    if 'fullscreen' in launchArg_history:
        fullscreenVar.set(bool(launchArg_history['fullscreen']))
    else:
        fullscreenVar.set(True)
    tk.mainloop()
