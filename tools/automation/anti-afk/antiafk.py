import time
import random
from pynput.keyboard import Key, Controller

# Keyboard Controller erstellen
keyboard = Controller()

# Reihenfolge der Tasten
keys = ['w', 'a', 's', 'd']

print("Anti-AFK gestartet. Drücke Ctrl+C zum Beenden.")
print("Stelle sicher, dass das Spielfenster aktiv ist!")

# 5 Sekunden warten, damit du das Spielfenster aktivieren kannst
for i in range(5, 0, -1):
    print(f"Start in {i} Sekunden...")
    time.sleep(1)

print("Anti-AFK läuft!")

try:
    while True:
        for key in keys:
            print(f"Drücke Taste: {key}")
            # Taste drücken und loslassen mit pynput
            keyboard.press(key)
            time.sleep(0.1)  # Kurz gedrückt halten
            keyboard.release(key)
            # Zufällige Pause zwischen 5 und 10 Sekunden
            delay = random.uniform(5, 10)
            print(f"Warte {delay:.1f} Sekunden...")
            time.sleep(delay)
except KeyboardInterrupt:
    print("\nAnti-AFK beendet.")
