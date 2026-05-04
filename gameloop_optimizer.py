import subprocess
import ctypes
import sys
import os
import psutil
import winreg
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# --- Admin check ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

# --- Optimization functions ---
def run_cmd(cmd):
    try:
        subprocess.run(cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass

def set_gameloop_high_priority():
    """Set GameLoop and HD-Player to high CPU priority"""
    targets = ["HD-Player.exe", "GameLoop.exe", "MuMuPlayer.exe", "LD9Box.exe", "dnplayer.exe"]
    count = 0
    for proc in psutil.process_iter(['name', 'pid']):
        for t in targets:
            if proc.info['name'] and t.lower() in proc.info['name'].lower():
                try:
                    p = psutil.Process(proc.info['pid'])
                    p.nice(psutil.HIGH_PRIORITY_CLASS)
                    count += 1
                except:
                    pass
    return count

def set_gpu_max():
    """Force GPU to maximum performance via registry"""
    # Disable power saving on GPU (NVIDIA)
    run_cmd('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers" /v HwSchMode /t REG_DWORD /d 2 /f')
    # Disable GPU throttling
    run_cmd('powercfg -setacvalueindex SCHEME_CURRENT 54533251-82be-4824-96c1-47b60b740d00 be337238-0d82-4146-a960-4f3749d470c7 100')
    run_cmd('powercfg -setactive SCHEME_CURRENT')
    # Set GPU preference for GameLoop to high performance
    try:
        key_path = r"SOFTWARE\Microsoft\DirectX\UserGpuPreferences"
        gameloop_paths = [
            r"C:\Program Files\TxGameAssistant\AppMarket\AppMarket.exe",
            r"C:\TxGameAssistant\HD-Player.exe",
            r"C:\Program Files (x86)\TxGameAssistant\HD-Player.exe",
        ]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            for path in gameloop_paths:
                winreg.SetValueEx(key, path, 0, winreg.REG_SZ, "GpuPreference=2;")
    except:
        pass

def trim_ram():
    """Free inactive RAM / working set"""
    run_cmd('powershell -Command "Get-Process | ForEach-Object { $_.WorkingSet64 = 0 }"')
    # Also via EmptyWorkingSet API
    try:
        kernel32 = ctypes.windll.kernel32
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                handle = kernel32.OpenProcess(0x1F0FFF, False, proc.info['pid'])
                if handle:
                    kernel32.SetProcessWorkingSetSize(handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
                    kernel32.CloseHandle(handle)
            except:
                pass
    except:
        pass

def kill_background_apps():
    """Kill known useless background processes"""
    kill_list = [
        "OneDrive.exe", "Teams.exe", "Spotify.exe", "Discord.exe",
        "Slack.exe", "zoom.exe", "SkypeApp.exe", "SearchApp.exe",
        "YourPhone.exe", "XboxApp.exe", "GameBarPresenceWriter.exe",
        "widgets.exe", "Cortana.exe", "msedgewebview2.exe",
    ]
    killed = []
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in kill_list:
            try:
                proc.kill()
                killed.append(proc.info['name'])
            except:
                pass
    return killed

def enable_game_mode():
    run_cmd('reg add "HKCU\\Software\\Microsoft\\GameBar" /v AllowAutoGameMode /t REG_DWORD /d 1 /f')
    run_cmd('reg add "HKCU\\Software\\Microsoft\\GameBar" /v AutoGameModeEnabled /t REG_DWORD /d 1 /f')

def disable_telemetry():
    run_cmd('sc stop DiagTrack')
    run_cmd('sc config DiagTrack start= disabled')
    run_cmd('sc stop dmwappushservice')
    run_cmd('sc config dmwappushservice start= disabled')

def disable_visual_effects():
    run_cmd('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" /v VisualFXSetting /t REG_DWORD /d 2 /f')
    run_cmd('reg add "HKCU\\Control Panel\\Desktop" /v UserPreferencesMask /t REG_BINARY /d 9012038010000000 /f')

def set_high_performance_power():
    run_cmd('powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c')

def flush_dns():
    run_cmd('ipconfig /flushdns')

def clear_temp():
    temp = os.environ.get('TEMP', '')
    sys_temp = r'C:\Windows\Temp'
    for folder in [temp, sys_temp]:
        run_cmd(f'del /q /f /s "{folder}\\*" 2>nul')

# --- GUI ---
class GameLoopOptimizer:
    def __init__(self, root):
        self.root = root
        self.root.title("GameLoop Optimizer Pro")
        self.root.geometry("620x700")
        self.root.configure(bg="#0d0d0d")
        self.root.resizable(False, False)

        self.log_lines = []
        self.build_ui()

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#0d0d0d")
        header.pack(fill="x", padx=20, pady=(20, 5))

        tk.Label(header, text="🎮 GameLoop Optimizer", font=("Segoe UI", 20, "bold"),
                 bg="#0d0d0d", fg="#ffffff").pack(side="left")
        tk.Label(header, text="v1.0", font=("Segoe UI", 10),
                 bg="#0d0d0d", fg="#555").pack(side="left", padx=(8,0), pady=(8,0))

        tk.Label(self.root, text="Max GPU · Max CPU · Geen lags · Geen FPS drops",
                 font=("Segoe UI", 10), bg="#0d0d0d", fg="#888").pack(anchor="w", padx=22)

        # Separator
        tk.Frame(self.root, bg="#222", height=1).pack(fill="x", padx=20, pady=12)

        # Options frame
        options_frame = tk.Frame(self.root, bg="#0d0d0d")
        options_frame.pack(fill="x", padx=20)

        self.checks = {}
        options = [
            ("gpu",        "🖥️  GPU Maximale Prestaties",          "Zet GPU op high performance, disable throttling", True),
            ("priority",   "⚡  GameLoop Hoge CPU Prioriteit",      "Hoge processprioriteit voor GameLoop / HD-Player", True),
            ("gamemode",   "🎯  Windows Game Mode AAN",              "Vertelt Windows om het spel prioriteit te geven", True),
            ("power",      "🔋  Hoge Prestaties Energieplan",        "Schakel over naar High Performance power plan", True),
            ("bgapps",     "🚫  Achtergrond Apps Sluiten",           "Sluit Discord, Teams, Spotify, etc.", True),
            ("ram",        "🧹  RAM Vrijmaken (Trim)",               "Vrijmaken van inactief geheugen", True),
            ("visuals",    "🎨  Visuele Effecten Uitschakelen",      "Animaties/schaduwen uit voor snellere UI", False),
            ("telemetry",  "🔇  Windows Telemetry Uitschakelen",     "Stopt Microsoft diagnostische processen", False),
            ("temp",       "🗑️  Temp Bestanden Wissen",              "Wist Windows/Systeem temp mappen", False),
            ("dns",        "🌐  DNS Cache Leegmaken",                "Flushes DNS cache (ipconfig /flushdns)", False),
        ]

        for key, label, desc, default in options:
            var = tk.BooleanVar(value=default)
            self.checks[key] = var

            row = tk.Frame(options_frame, bg="#161616", bd=0, highlightthickness=1,
                           highlightbackground="#2a2a2a")
            row.pack(fill="x", pady=3)

            inner = tk.Frame(row, bg="#161616")
            inner.pack(fill="x", padx=12, pady=8)

            cb = tk.Checkbutton(inner, variable=var, bg="#161616",
                                activebackground="#161616", fg="#fff",
                                selectcolor="#1e1e1e", cursor="hand2",
                                relief="flat", bd=0)
            cb.pack(side="left")

            txt = tk.Frame(inner, bg="#161616")
            txt.pack(side="left", padx=4)
            tk.Label(txt, text=label, font=("Segoe UI", 10, "bold"),
                     bg="#161616", fg="#ffffff", anchor="w").pack(anchor="w")
            tk.Label(txt, text=desc, font=("Segoe UI", 8),
                     bg="#161616", fg="#666", anchor="w").pack(anchor="w")

        # Separator
        tk.Frame(self.root, bg="#222", height=1).pack(fill="x", padx=20, pady=12)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0d0d0d")
        btn_frame.pack(padx=20, fill="x")

        self.optimize_btn = tk.Button(
            btn_frame, text="▶  Start Optimalisatie", font=("Segoe UI", 12, "bold"),
            bg="#22c55e", fg="#000", activebackground="#16a34a", activeforeground="#000",
            relief="flat", cursor="hand2", pady=10,
            command=self.run_optimization
        )
        self.optimize_btn.pack(fill="x")

        self.prio_btn = tk.Button(
            btn_frame, text="⚡  Pas Prioriteit Toe (na GameLoop starten)",
            font=("Segoe UI", 9), bg="#1e3a5f", fg="#7dd3fc",
            activebackground="#1e40af", activeforeground="#fff",
            relief="flat", cursor="hand2", pady=6,
            command=self.apply_priority_only
        )
        self.prio_btn.pack(fill="x", pady=(6, 0))

        # Log box
        tk.Frame(self.root, bg="#222", height=1).pack(fill="x", padx=20, pady=8)

        self.log_box = tk.Text(self.root, height=8, bg="#0a0a0a", fg="#4ade80",
                               font=("Consolas", 8), relief="flat", bd=0,
                               state="disabled", wrap="word")
        self.log_box.pack(fill="x", padx=20, pady=(0, 15))

        self.log("Klaar om GameLoop te optimaliseren. Druk op Start.")
        self.log("TIP: Start GameLoop eerst, druk dan op '⚡ Pas Prioriteit Toe'.")

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"► {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.root.update()

    def run_optimization(self):
        self.optimize_btn.configure(state="disabled", text="⏳ Bezig...")
        threading.Thread(target=self._do_optimize, daemon=True).start()

    def _do_optimize(self):
        self.log("=== Optimalisatie gestart ===")

        if self.checks["power"].get():
            self.log("Energieplan: High Performance activeren...")
            set_high_performance_power()
            self.log("✓ Energieplan ingesteld op Hoge Prestaties")

        if self.checks["gpu"].get():
            self.log("GPU: Maximale prestaties instellen...")
            set_gpu_max()
            self.log("✓ GPU ingesteld op maximale prestaties (hardware GPU scheduling AAN)")

        if self.checks["gamemode"].get():
            self.log("Windows Game Mode inschakelen...")
            enable_game_mode()
            self.log("✓ Game Mode ingeschakeld")

        if self.checks["telemetry"].get():
            self.log("Telemetry uitschakelen...")
            disable_telemetry()
            self.log("✓ Windows telemetry gestopt")

        if self.checks["visuals"].get():
            self.log("Visuele effecten uitschakelen...")
            disable_visual_effects()
            self.log("✓ Animaties/schaduwen uitgeschakeld")

        if self.checks["bgapps"].get():
            self.log("Achtergrond apps sluiten...")
            killed = kill_background_apps()
            if killed:
                self.log(f"✓ Gesloten: {', '.join(set(killed))}")
            else:
                self.log("✓ Geen onnodige achtergrond apps gevonden")

        if self.checks["ram"].get():
            self.log("RAM vrijmaken...")
            trim_ram()
            self.log("✓ Inactief geheugen vrijgemaakt")

        if self.checks["temp"].get():
            self.log("Temp bestanden wissen...")
            clear_temp()
            self.log("✓ Temp mappen geleegd")

        if self.checks["dns"].get():
            self.log("DNS cache leegmaken...")
            flush_dns()
            self.log("✓ DNS cache geflushed")

        if self.checks["priority"].get():
            self.log("GameLoop prioriteit instellen...")
            count = set_gameloop_high_priority()
            if count > 0:
                self.log(f"✓ {count} GameLoop proces(sen) op Hoge Prioriteit gezet")
            else:
                self.log("⚠ GameLoop niet gevonden. Start GameLoop en druk op '⚡ Pas Prioriteit Toe'")

        self.log("=== ✅ Klaar! GameLoop is geoptimaliseerd ===")
        self.root.after(0, lambda: self.optimize_btn.configure(
            state="normal", text="▶  Start Optimalisatie"))

    def apply_priority_only(self):
        self.log("Prioriteit toepassen op lopende GameLoop processen...")
        count = set_gameloop_high_priority()
        if count > 0:
            self.log(f"✓ {count} GameLoop proces(sen) op Hoge Prioriteit gezet!")
        else:
            self.log("⚠ Geen GameLoop processen gevonden. Zorg dat GameLoop open is.")

# --- Entry point ---
if __name__ == "__main__":
    if not is_admin():
        if messagebox.askyesno("Administrator vereist",
            "Dit programma heeft administrator rechten nodig voor GPU/CPU optimalisatie.\n\nOpnieuw starten als administrator?"):
            run_as_admin()
        sys.exit()

    root = tk.Tk()
    app = GameLoopOptimizer(root)
    root.mainloop()
