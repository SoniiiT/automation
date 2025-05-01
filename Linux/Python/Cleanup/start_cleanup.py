#!/usr/bin/env python3

import os
import shutil
import subprocess
from datetime import datetime

def get_disk_usage():
    """Gibt die Festplattennutzung zurück"""
    total, used, free = shutil.disk_usage("/")
    return {
        "total": total // (2**30),  # Konvertierung zu GB
        "used": used // (2**30),
        "free": free // (2**30)
    }

def cleanup_system():
    """Führt verschiedene Reinigungsoperationen durch"""
    try:
        # Temporäre Dateien löschen
        subprocess.run(["sudo", "rm", "-rf", "/tmp/*"])
        
        # APT Cache leeren
        subprocess.run(["sudo", "apt-get", "clean"])
        
        # Alte Kernel entfernen
        subprocess.run(["sudo", "apt-get", "autoremove", "-y"])
        
        # Journal Logs aufräumen
        subprocess.run(["sudo", "journalctl", "--vacuum-time=7d"])
        
        return True
    except Exception as e:
        print(f"Fehler beim Aufräumen: {str(e)}")
        return False

def main():
    # Aktuelle Festplattennutzung prüfen
    before = get_disk_usage()
    print(f"Festplattennutzung vor der Reinigung:")
    print(f"Gesamt: {before['total']} GB")
    print(f"Verwendet: {before['used']} GB")
    print(f"Frei: {before['free']} GB")
    
    # Reinigung durchführen
    print("\nStarte Systemreinigung...")
    if cleanup_system():
        print("Reinigung erfolgreich abgeschlossen!")
    else:
        print("Reinigung konnte nicht vollständig durchgeführt werden.")
    
    # Neue Festplattennutzung prüfen
    after = get_disk_usage()
    print(f"\nFestplattennutzung nach der Reinigung:")
    print(f"Gesamt: {after['total']} GB")
    print(f"Verwendet: {after['used']} GB")
    print(f"Frei: {after['free']} GB")
    
    # Einsparung berechnen
    saved = before['used'] - after['used']
    print(f"\nFreigegebener Speicherplatz: {saved} GB")

if __name__ == "__main__":
    main()
