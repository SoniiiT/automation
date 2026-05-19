from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import pyautogui
pyautogui.FAILSAFE = False  # Deaktiviert den Failsafe bei Mausbewegung in Ecken
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


def _env_bool(name, default=False):
    """Liest boolesche Umgebungsvariablen robust ein (1/true/yes/on)."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y", "ja"}


def normalize_browser_viewport(driver):
    """Stellt sicher, dass der Browser sichtbar/maximiert ist und Zoom auf 100% steht."""
    try:
        driver.set_window_position(0, 0)
    except Exception as e:
        logging.debug(f"set_window_position übersprungen: {e}")

    try:
        driver.maximize_window()
    except Exception as e:
        logging.warning(f"maximize_window fehlgeschlagen: {e}")

    # Zoom auf 100% zurücksetzen, falls die Seite skaliert wurde.
    try:
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("0").key_up(Keys.CONTROL).perform()
    except Exception as e:
        logging.debug(f"Zoom-Reset per Tastenkürzel fehlgeschlagen: {e}")

    try:
        driver.execute_script("document.body.style.zoom='100%';")
    except Exception as e:
        logging.debug(f"Zoom-Reset per JavaScript fehlgeschlagen: {e}")

    try:
        driver.execute_cdp_cmd("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
    except Exception as e:
        logging.debug(f"CDP PageScaleFactor konnte nicht gesetzt werden: {e}")


def ensure_autotask_window_state(driver):
    """Sorgt dafür, dass der aktive Tab/Window wirklich Autotask zeigt und voll sichtbar ist."""
    try:
        handles = driver.window_handles
        autotask_handles = []

        for handle in handles:
            driver.switch_to.window(handle)
            url = (driver.current_url or "").lower()
            if "autotask.net" in url:
                autotask_handles.append(handle)

        autotask_handle = autotask_handles[-1] if autotask_handles else None

        if autotask_handle:
            driver.switch_to.window(autotask_handle)
        elif handles:
            driver.switch_to.window(handles[-1])

        # Leere/Neue Tabs schließen, damit keine falsche Seite im Fokus bleibt.
        for handle in list(driver.window_handles):
            try:
                driver.switch_to.window(handle)
                current_url = (driver.current_url or "").lower()
                if current_url.startswith("chrome://newtab") or current_url in {"about:blank", "chrome://new-tab-page/"}:
                    if len(driver.window_handles) > 1:
                        driver.close()
            except Exception:
                continue

        # Zurück auf den bevorzugten Autotask-Tab, falls vorhanden.
        remaining_handles = driver.window_handles
        if autotask_handle and autotask_handle in remaining_handles:
            driver.switch_to.window(autotask_handle)
        elif remaining_handles:
            driver.switch_to.window(remaining_handles[-1])

        # Explizite Fenstergröße verhindert seltene Minimierungs-/Viewport-Fehler unter Windows.
        try:
            screen = pyautogui.size()
            width = int(screen.width)
            height = int(screen.height)
            driver.set_window_rect(x=0, y=0, width=width, height=height)
        except Exception as e:
            logging.debug(f"set_window_rect übersprungen: {e}")

        normalize_browser_viewport(driver)
        logging.info(f"Aktive URL nach Fensterkorrektur: {driver.current_url}")
    except Exception as e:
        logging.warning(f"Fenster-/Tab-Korrektur fehlgeschlagen: {e}")


def stabilize_presentation_mode(driver):
    """Stabilisiert den Präsentationsmodus nach dem Umschalten bzw. nach einem Reload."""
    try:
        time.sleep(3)
        ensure_autotask_window_state(driver)
        time.sleep(1)
        driver.switch_to.default_content()
        logging.info(f"Präsentationsmodus stabilisiert. Aktive URL: {driver.current_url}")
    except Exception as e:
        logging.warning(f"Präsentationsmodus konnte nicht stabilisiert werden: {e}")

# Diese Funktion prüft, ob ein X-Server läuft und stellt sicher, dass wir Zugriff haben
def setup_display():
    # Auf Windows gibt es kein X11-Setup; frühzeitig beenden.
    if platform.system() != "Linux":
        logging.info("X-Display-Setup wird auf diesem System übersprungen.")
        return

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


def _safe_click(driver, locator, timeout=8):
    """Klickt robust per normalem Klick und JavaScript-Fallback."""
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)
    return element


def _click_first_match(driver, locators, step_name):
    """Probiert mehrere Locator-Varianten und klickt den ersten Treffer."""
    last_error = None
    for locator in locators:
        try:
            _safe_click(driver, locator, timeout=5)
            logging.info(f"{step_name}: Klick erfolgreich mit Locator {locator}")
            return True
        except Exception as e:
            last_error = e
    if last_error:
        raise last_error
    return False


def _dismiss_blocking_overlay(driver):
    """Schließt blockierende Overlays (z. B. KaseyaOne-App-Launcher), falls vorhanden."""
    try:
        overlay = driver.find_elements(By.CSS_SELECTOR, "div.fixed.z-overlay")
        if not overlay:
            return

        close_candidates = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'z-overlay')]//button[normalize-space()=''] | "
            "//div[contains(@class,'z-overlay')]//*[@aria-label='Close' or @aria-label='Schließen']"
        )

        if close_candidates:
            try:
                close_candidates[0].click()
            except Exception:
                driver.execute_script("arguments[0].click();", close_candidates[0])
            logging.info("Blockierendes Overlay wurde geschlossen.")
            time.sleep(1)
    except Exception as e:
        logging.debug(f"Overlay-Prüfung übersprungen: {e}")


def _switch_to_frame_with_text(driver, text, timeout=10):
    """Wechselt in das iFrame, das den gesuchten Text enthält."""
    end_time = time.time() + timeout

    while time.time() < end_time:
        driver.switch_to.default_content()

        # Falls der Text im Hauptdokument steht, kein Frame-Wechsel nötig
        if text in driver.page_source:
            return True

        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                if text in driver.page_source:
                    return True
            except Exception:
                continue

        time.sleep(0.3)

    driver.switch_to.default_content()
    return False


def enter_presentation_mode(driver):
    """
    Öffnet den Präsentationsmodus über das UI:
    1) 3-Punkte-Menü öffnen
    2) Präsentationsmodus wählen
    3) Option 'Nichts ... wechseln' auswählen
    4) 'Präsentationsmodus starten' klicken
    """
    logging.info("Starte Wechsel in den Präsentationsmodus über das Menü...")

    _dismiss_blocking_overlay(driver)

    # 1) Dashboard-3-Punkte-Menü öffnen (nicht das Benutzer-Menü oben rechts)
    menu_button_locators = [
        (By.XPATH, "//main//button[contains(normalize-space(.),'')]"),
        (By.XPATH, "//main//button[contains(@class,'c-button--icon-only') and @data-onyx-external-id]"),
        (By.XPATH, "//button[contains(normalize-space(.),'')]")
    ]
    _click_first_match(driver, menu_button_locators, "3-Punkte-Menü")

    # 2) Eintrag 'Präsentationsmodus' im Dropdown klicken
    presentation_entry_locators = [
        (By.XPATH, "//*[self::option or @role='option' or @role='menuitem'][contains(normalize-space(.),'Präsentationsmodus')]") ,
        (By.XPATH, "//*[contains(normalize-space(.),'Präsentationsmodus') and not(contains(normalize-space(.),'starten'))]"),
    ]
    _click_first_match(driver, presentation_entry_locators, "Menüeintrag Präsentationsmodus")

    # Dialog erscheint in einem iFrame
    if not _switch_to_frame_with_text(driver, "Einstellungen für Präsentationsmodus", timeout=10):
        raise RuntimeError("Dialog 'Einstellungen für Präsentationsmodus' wurde nicht gefunden.")

    # 3) In Dialog Option 'Nichts (...)' wählen
    nothing_option_locators = [
        (By.XPATH, "//span[contains(@class,'PrimaryText') and contains(normalize-space(.),'Nichts (weder Filterwert auf Registerkartenebene noch Registerkarte wechseln)')]"),
        (By.XPATH, "//*[contains(normalize-space(.),'Nichts (weder Filterwert auf Registerkartenebene noch Registerkarte wechseln)')]"),
        (By.XPATH, "//*[contains(normalize-space(.),'Nichts (weder')]")
    ]
    _click_first_match(driver, nothing_option_locators, "Option 'Nichts'")

    # 4) Präsentationsmodus starten
    start_button_locators = [
        (By.XPATH, "//div[contains(@class,'Button2') and contains(normalize-space(.),'Präsentationsmodus starten')]") ,
        (By.XPATH, "//*[contains(normalize-space(.),'Präsentationsmodus starten')]")
    ]
    _click_first_match(driver, start_button_locators, "Button 'Präsentationsmodus starten'")

    # Kurze Stabilisierung nach Moduswechsel
    time.sleep(2)
    driver.switch_to.default_content()
    logging.info("Präsentationsmodus wurde gestartet.")

def login_autotask():
    wait()  # <-- Hier wird jetzt wirklich 20 Sekunden gewartet!
    # Bestimme den Pfad zur .env-Datei (kompatibel mit PyInstaller .exe)
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.realpath(__file__))
    env_path = os.path.join(script_dir, ".env")
    
    # Lade Umgebungsvariablen mit absolutem Pfad
    logging.info(f"Lade .env-Datei von: {env_path}")
    load_dotenv(env_path)
    
    username = os.getenv('AUTOTASK_USERNAME')
    password = os.getenv('AUTOTASK_PASSWORD')
    enable_presentation_mode = _env_bool('AUTOTASK_ENABLE_PRESENTATION_MODE', default=False)
    
    if not username or not password:
        logging.error("Benutzername oder Passwort fehlen in der .env-Datei!")
        logging.error(f"Überprüfe die Datei: {env_path}")
        sys.exit(1)

    logging.info("Konfiguriere Chrome...")
    options = Options()
    
    # Pflichtoptionen
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-infobars')  # Unterdrückt das "Chrome for Testing" Banner
    options.add_argument('--start-maximized')
    options.add_argument('--new-window')

    if platform.system() == "Windows":
        # Verhindert bekannte Render-/Kompositionsprobleme mit Chrome auf Windows/Intel-GPUs.
        options.add_argument('--disable-direct-composition')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--force-device-scale-factor=1')
        options.add_argument('--high-dpi-support=1')
        options.add_argument('--disable-features=CalculateNativeWinOcclusion')
    
    # window-position nur auf Linux benötigt
    if platform.system() == "Linux":
        options.add_argument('--window-position=0,0')
    
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
    # Fester Pfad ohne Windows 8.3-Kurzpfad-Problem
    current_pid = os.getpid()
    unique_id = f"{current_pid}_{int(time.time())}"
    if platform.system() == "Windows":
        temp_dir = os.path.join("C:\\Autotask\\tmp", f"chrome_profile_{unique_id}")
    else:
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
            logging.info(f"System erkannt: {platform.system()}, starte Chrome mit Standardeinstellungen...")
            
            # Explizit Chrome-Pfad auf Windows setzen
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    logging.info(f"Chrome gefunden unter: {path}")
                    options.binary_location = path
                    break
            else:
                logging.warning("Chrome nicht unter Standardpfaden gefunden, versuche ohne expliziten Pfad")

            # ChromeDriver mit verbose Logging starten
            log_path = os.path.join(log_dir, "chromedriver.log")
            service = Service(log_output=log_path)
            driver = webdriver.Chrome(service=service, options=options)
        
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
        
        logging.info("Suche Passwortfeld...")
        password_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.NAME, "Password"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
        time.sleep(1)
        password_field.click()
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(1)
        
        logging.info("Suche Anmelde-Button...")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Anmelden']"))
        )
        login_button.click()
        
        logging.info("Anmeldung durchgeführt!")
        
        # Warte auf das Dashboard
        logging.info("Warte auf das Dashboard...")
        time.sleep(15)  # Längere Wartezeit für das vollständige Laden
        
        logging.info("Normalisiere Browser-Ansicht...")
        ensure_autotask_window_state(driver)
        time.sleep(1)

        if enable_presentation_mode:
            try:
                enter_presentation_mode(driver)
                stabilize_presentation_mode(driver)
            except Exception as e:
                logging.warning(f"Präsentationsmodus über UI fehlgeschlagen: {e}")
                logging.warning("Präsentationsmodus wird übersprungen, normale Dashboard-Ansicht bleibt aktiv.")
        else:
            logging.info("Präsentationsmodus ist deaktiviert (AUTOTASK_ENABLE_PRESENTATION_MODE=false).")
        
        logging.info("Wird aktualisiert...")
        if enable_presentation_mode:
            logging.info("Initialer Refresh wird im Präsentationsmodus übersprungen, um die Ansicht stabil zu halten.")
        else:
            # Aktualisiere die Seite
            driver.refresh()
            ensure_autotask_window_state(driver)
        # Aktualisiere die Seite alle 2 Minuten (wie F5)
        while True:
            time.sleep(120)  # 2 Minuten warten
            logging.info("Aktualisiere die Seite (F5)...")
            driver.refresh()
            ensure_autotask_window_state(driver)
            if enable_presentation_mode:
                stabilize_presentation_mode(driver)
        
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
