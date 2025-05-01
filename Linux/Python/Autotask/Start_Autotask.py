from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
import time

def login_autotask():
    # Lade Umgebungsvariablen
    load_dotenv()
    username = os.getenv('AUTOTASK_USERNAME')
    password = os.getenv('AUTOTASK_PASSWORD')

    print("Konfiguriere Chrome...")
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    # Option hinzufügen, damit Chrome nicht geschlossen wird
    options.add_experimental_option("detach", True)
    # Diese Option entfernt die "Chrome wird von Testsoftware gesteuert" Nachricht
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    # Diese Option entfernt den "Chrome ist being controlled by automated test software" InfoBar
    options.add_experimental_option('useAutomationExtension', False)
    
    print("Starte Chrome...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        print("Chrome gestartet, öffne Autotask...")
        driver.get("https://ww18.autotask.net")
        
        time.sleep(5)
        
        print("Suche Anmeldeformular...")
        try:
            username_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "UserName"))
            )
        except:
            username_field = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
        
        print("Gebe Benutzernamen ein...")
        username_field.clear()
        username_field.send_keys(username)
        time.sleep(2)
        
        print("Suche Fortfahren-Button...")
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Fortfahren']"))
        )
        continue_button.click()
        time.sleep(2)
        
        print("Suche Passwortfeld...")
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Password"))
        )
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(2)
        
        print("Suche Anmelde-Button...")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Anmelden']"))
        )
        login_button.click()
        
        print("Anmeldung durchgeführt!")
        
        # Warte auf das Dashboard
        print("Warte auf das Dashboard...")
        time.sleep(10)  # Längere Wartezeit für das vollständige Laden
        
        # Wallboard auswählen
        print("Wähle Wallboard aus...")
        wallboard = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@title='Wallboard']"))
        )
        wallboard.click()
        time.sleep(5)
        
        # Dropdown-Menü öffnen
        print("Öffne Dropdown-Menü...")
        dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "TitleBarContextMenuButton1"))
        )
        dropdown.click()
        time.sleep(2)
        
        # Präsentationsmodus auswählen
        print("Wähle Präsentationsmodus...")
        presentation_mode = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Präsentationsmodus']"))
        )
        presentation_mode.click()
        time.sleep(2)
        
        # Option "Nichts" auswählen
        print("Wähle Option 'Nichts'...")
        nothing_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Nichts (weder Filterwert')]"))
        )
        nothing_option.click()
        time.sleep(2)
        
        # Präsentationsmodus starten
        print("Starte Präsentationsmodus...")
        start_presentation = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Präsentationsmodus starten']"))
        )
        start_presentation.click()
        
        print("Alle Aktionen erfolgreich durchgeführt!")
        print("Chrome bleibt geöffnet!")
        
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        try:
            driver.save_screenshot("error_screenshot.png")
            print("Screenshot wurde gespeichert als 'error_screenshot.png'")
        except:
            pass

if __name__ == "__main__":
    login_autotask()
