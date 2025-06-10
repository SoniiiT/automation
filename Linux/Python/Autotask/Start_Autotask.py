from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os
import time
import platform
import subprocess
import tempfile
import shutil
import uuid
import sys
import logging
from datetime import datetime

# Setup Logging
log_dir = os.path.join(os.path.expanduser("~"), "autotask_logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"autotask_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

def wait():
    logging.info("Starte Wartezeit von 20 Sekunden vor Ausführung...")
    time.sleep(20)

# Diese Funktion prüft, ob ein X-Server läuft und stellt sicher, dass wir Zugriff haben
def setup_display():
    try:
        # Versuche, den ersten verfügbaren X-Display zu finden
        displays = []
        for i in range(10):  # Prüfe die Displays :0 bis :9
            if os.path.exists(f"/tmp/.X11-unix/X{i}"):
                displays.append(f":{i}")
        
        if displays:
            logging.info(f"Verfügbare X-Displays gefunden: {', '.join(displays)}")
            os.environ["DISPLAY"] = displays[0]  # Verwende den ersten verfügbaren Display
        else:
            logging.warning("Kein X-Display gefunden, verwende Standard :0")
            os.environ["DISPLAY"] = ":0"
            
        # Stelle sicher, dass die X-Berechtigung existiert
        home = os.path.expanduser("~")
        xauth_file = os.path.join(home, ".Xauthority")
        if os.path.exists(xauth_file):
            logging.info(f".Xauthority-Datei gefunden unter: {xauth_file}")
        else:
            logging.warning(".Xauthority-Datei nicht gefunden, X-Server-Autorisierung könnte fehlschlagen")
            
        # Prüfe, ob der X-Server erreichbar ist
        test_cmd = ["xdpyinfo"]
        try:
            subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            logging.info("X-Server-Verbindungstest erfolgreich")
        except subprocess.CalledProcessError:
            logging.error("X-Server ist nicht erreichbar! Grafikausgabe wird nicht funktionieren.")
            logging.info("Versuche, die XAUTHORITY-Variable zu setzen...")
            os.environ["XAUTHORITY"] = xauth_file
    except Exception as e:
        logging.error(f"Fehler beim Einrichten des Displays: {e}")

def login_autotask():
    wait()  # <-- Hier wird jetzt wirklich 20 Sekunden gewartet!
    # Bestimme den Pfad zur .env-Datei
    script_dir = os.path.dirname(os.path.realpath(__file__))
    env_path = os.path.join(script_dir, ".env")
    
    # Lade Umgebungsvariablen mit absolutem Pfad
    logging.info(f"Lade .env-Datei von: {env_path}")
    load_dotenv(env_path)
    
    username = os.getenv('AUTOTASK_USERNAME')
    password = os.getenv('AUTOTASK_PASSWORD')
    
    if not username or not password:
        logging.error("Benutzername oder Passwort fehlen in der .env-Datei!")
        logging.error(f"Überprüfe die Datei: {env_path}")
        sys.exit(1)

    logging.info("Konfiguriere Chrome...")
    options = Options()
    
    # Pflichtoptionen für Headless-Server
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # Startoptionen
    options.add_argument('--start-maximized')
    options.add_argument('--start-fullscreen')
    
    # Bei crontab müssen wir explizit den Display setzen (für GUI)
    if platform.system() == "Linux":
        os.environ["DISPLAY"] = ":0"
    
    # Verwalte aktive Chrome-Profile über Dateisystem-Locks
    pid_file = os.path.join(os.path.expanduser("~"), ".chrome_autotask_lock")

    # Prüfe und entferne alte Prozesse und Profilverzeichnisse
    def cleanup_old_sessions():
        try:
            # Prüfe, ob eine PID-Datei existiert
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    old_pid = f.read().strip()
                    old_temp_dir = ""
                    if '\n' in old_pid:  # Format: "PID\nTEMP_DIR"
                        parts = old_pid.split('\n')
                        old_pid = parts[0]
                        if len(parts) > 1:
                            old_temp_dir = parts[1]
                    
                # Prüfe, ob der alte Prozess noch läuft
                try:
                    old_pid = int(old_pid)
                    if platform.system() == "Linux":
                        # Unter Linux können wir direkt prüfen
                        if os.path.exists(f"/proc/{old_pid}"):
                            logging.warning(f"Alter Chrome-Prozess (PID {old_pid}) scheint noch aktiv zu sein")
                            logging.info("Beende alte Chrome-Prozesse...")
                            subprocess.run(["pkill", "-f", "chrome"], stderr=subprocess.DEVNULL)
                            time.sleep(2)  # Warte, bis Prozesse beendet sind
                    else:
                        # Unter Windows ist es komplizierter
                        logging.warning(f"Alter Chrome-Prozess (PID {old_pid}) könnte noch laufen")
                        # Auf allen Systemen versuchen wir, Chrome zu beenden
                        if platform.system() == "Windows":
                            os.system("taskkill /f /im chrome.exe >nul 2>&1")
                        else:
                            subprocess.run(["pkill", "-f", "chrome"], stderr=subprocess.DEVNULL)
                        time.sleep(2)
                except ValueError:
                    logging.warning(f"Ungültige PID in Lock-Datei: {old_pid}")
                
                # Versuche das alte Temp-Verzeichnis zu löschen
                if old_temp_dir and os.path.exists(old_temp_dir):
                    try:
                        logging.info(f"Entferne altes Chrome-Profilverzeichnis: {old_temp_dir}")
                        shutil.rmtree(old_temp_dir, ignore_errors=True)
                    except Exception as e:
                        logging.warning(f"Konnte altes Temp-Verzeichnis nicht löschen: {e}")
                
                # Entferne die alte Lock-Datei
                os.remove(pid_file)
        except Exception as e:
            logging.warning(f"Fehler beim Aufräumen alter Sessions: {e}")

    # Aufräumen vor dem Start
    cleanup_old_sessions()

    # Erstelle ein wirklich eindeutiges temporäres Verzeichnis
    current_pid = os.getpid()
    unique_id = f"{current_pid}_{int(time.time())}"
    temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{unique_id}")

    # Stelle sicher, dass das Verzeichnis nicht existiert
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # Speichere die aktuelle PID und das Temp-Verzeichnis in der Lock-Datei
    with open(pid_file, 'w') as f:
        f.write(f"{current_pid}\n{temp_dir}")

    logging.info(f"Verwende temporäres Profilverzeichnis: {temp_dir}")
    options.add_argument(f"--user-data-dir={temp_dir}")
    
    # Option hinzufügen, damit Chrome nicht geschlossen wird
    options.add_experimental_option("detach", True)
    # Diese Option entfernt die "Chrome wird von Testsoftware gesteuert" Nachricht
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    # Diese Option entfernt den "Chrome ist being controlled by automated test software" InfoBar
    options.add_experimental_option('useAutomationExtension', False)
    # Deaktiviere Passwort-Manager
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    
    # Bei Linux, beende alle laufenden Chrome-Prozesse
    if platform.system() == "Linux":
        try:
            logging.info("Beende laufende Chrome-Prozesse...")
            subprocess.run(["pkill", "-f", "chrome"], stderr=subprocess.DEVNULL)
            time.sleep(2)  # Warte, bis Prozesse beendet sind
        except Exception as e:
            logging.warning(f"Konnte Chrome-Prozesse nicht beenden: {e}")
    
    logging.info("Starte Chrome...")
    try:
        if platform.system() == "Linux":
            try:
                # Prüfe, ob Chrome vorhanden ist
                chrome_binary = subprocess.check_output(["which", "google-chrome"], 
                                                       universal_newlines=True).strip()
                logging.info(f"Chrome gefunden unter: {chrome_binary}")
                
                # Explizit den Chrome-Pfad setzen
                options.binary_location = chrome_binary
                
                # Direkt den Chromedriver verwenden, mit vollständigem Pfad
                logging.info("Versuche direkten Chromedriver-Aufruf...")
                driver_path = "/usr/bin/chromedriver"
                
                if os.path.exists(driver_path):
                    logging.info(f"Chromedriver gefunden unter: {driver_path}")
                    
                    # Stelle sicher, dass Chromedriver ausführbar ist
                    os.chmod(driver_path, 0o755)
                    
                    # Verwende den vorinstallierten Chromedriver
                    service = Service(executable_path=driver_path)
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    # Manuellen Chromedriver-Download überspringen und systemweiten Driver verwenden
                    logging.info("Versuche systemweiten Chromedriver ohne expliziten Pfad")
                    driver = webdriver.Chrome(options=options)
            except Exception as e:
                logging.error(f"Fehler bei Chrome/Chromedriver-Initialisierung: {e}")
                # Versuche eine einfachere Methode als letzten Ausweg
                try:
                    logging.info("Versuche Standard-Chrome...")
                    driver = webdriver.Chrome(options=options)
                except Exception as e2:
                    logging.error(f"Auch Standard-Chrome fehlgeschlagen: {e2}")
                    # Letzter Versuch: Alle Optionen entfernen und neu versuchen
                    logging.info("Letzter Versuch: Minimalkonfiguration")
                    simple_options = Options()
                    simple_options.add_argument('--no-sandbox')
                    simple_options.add_argument('--disable-dev-shm-usage')
                    driver = webdriver.Chrome(options=simple_options)
        else:
            # Auf Windows/Mac versuchen wir, den Chromedriver direkt zu verwenden
            # ohne WebDriverManager, um Abhängigkeiten zu reduzieren
            logging.info(f"System erkannt: {platform.system()}, starte Chrome mit Standardeinstellungen...")
            driver = webdriver.Chrome(options=options)
        
        logging.info("Chrome gestartet, öffne Autotask...")
        driver.get("https://ww18.autotask.net")
        time.sleep(5)
        
        logging.info("Suche Anmeldeformular...")
        try:
            username_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "UserName"))
            )
        except:
            username_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
        
        logging.info("Gebe Benutzernamen ein...")
        username_field.clear()
        username_field.send_keys(username)
        time.sleep(2)
        
        logging.info("Suche Fortfahren-Button...")
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Fortfahren']"))
        )
        continue_button.click()
        time.sleep(2)
        
        logging.info("Suche Passwortfeld...")
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Password"))
        )
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(2)
        
        logging.info("Suche Anmelde-Button...")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Anmelden']"))
        )
        login_button.click()
        
        logging.info("Anmeldung durchgeführt!")
        
        # Warte auf das Dashboard
        logging.info("Warte auf das Dashboard...")
        time.sleep(15)  # Längere Wartezeit für das vollständige Laden
        
        logging.info("Wird aktualisiert...")
        # Aktualisiere die Seite
        driver.refresh()
        # Aktualisiere die Seite alle 2 Minuten (wie F5)
        while True:
            time.sleep(120)  # 2 Minuten warten
            logging.info("Aktualisiere die Seite (F5)...")
            driver.refresh()
        
    except Exception as e:
        logging.error(f"Ein Fehler ist aufgetreten: {e}")
        try:
            screenshot_path = os.path.join(log_dir, "error_screenshot.png")
            driver.save_screenshot(screenshot_path)
            logging.info(f"Screenshot wurde gespeichert als '{screenshot_path}'")
        except:
            pass

if __name__ == "__main__":
    setup_display()
    login_autotask()
