import sys
import speech_recognition as sr
import webbrowser
import time
import subprocess
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGraphicsDropShadowEffect, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath
import threading

AKTIVIERUNGSWORT = "nova"
PROGRAMM_INDEX_DATEI = "programm_index.json"
WEBSITE_INDEX_DATEI = "website_index.json"

# Globale Variablen für die Indizes
PROGRAMM_INDEX = {}
WEBSITE_INDEX = {}

class GlowLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._opacity = 1.0
        self.glow_color = QColor(0, 255, 157)  # Grün
        self.setFont(QFont('Segoe UI', 36, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(80)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # Animation für Opacity
        self.animation = QPropertyAnimation(self, b"opacity", self)
        self.animation.setDuration(2000)  # 2 Sekunden pro Zyklus
        self.animation.setStartValue(1.0)  # Start hell
        self.animation.setKeyValueAt(0.5, 0.4)  # In der Mitte dunkel
        self.animation.setEndValue(1.0)  # Ende wieder hell
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)  # Sanfte Übergänge
        self.animation.setLoopCount(-1)  # Endlose Wiederholung
        
    @pyqtProperty(float)
    def opacity(self):
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.update()
        
    def start_pulsing(self):
        self.animation.start()
        
    def stop_pulsing(self):
        self.animation.stop()
        self._opacity = 1.0
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Erstelle einen Textpfad
        path = QPainterPath()
        font = self.font()
        rect = self.rect()
        path.addText(rect.center().x() - painter.fontMetrics().horizontalAdvance(self.text()) / 2,
                    rect.center().y() + painter.fontMetrics().ascent() / 2,
                    font,
                    self.text())
        
        # Zeichne den Glow-Effekt
        glow_radius = 10  # Konstanter Glow-Radius
        for i in range(5):
            pen = QPen(self.glow_color)
            pen.setWidth(1 + i)
            # Opacity wird hier einbezogen
            alpha = int(150 * self._opacity * (1 - i / 5))
            pen.setColor(QColor(0, 255, 157, alpha))
            painter.setPen(pen)
            painter.drawPath(path)
        
        # Zeichne den Text selbst mit der aktuellen Opacity
        color = QColor(self.glow_color)
        color.setAlpha(int(255 * self._opacity))
        painter.fillPath(path, color)

class ChatBubble(QFrame):
    def __init__(self, text, is_command=False, parent=None):
        super().__init__(parent)
        print(f"Erstelle ChatBubble mit Text: {text}")
        
        # Unterschiedliche Styles für Befehle und Antworten
        if is_command:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border-radius: 15px;
                    margin: 5px 15px 5px 100px;  /* Viel mehr Platz links für Befehle */
                    min-height: 30px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border-radius: 15px;
                    margin: 5px 50px 5px 15px;  /* Viel mehr Platz rechts für Antworten */
                    min-height: 30px;
                    border: 1px solid #00ff9d;
                }
            """)
        
        # Layout mit minimalen Margins
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(0)
        
        # Text Label ohne Rahmen
        self.label = QLabel(text)
        self.label.setStyleSheet("""
            QLabel {
                color: #00ff9d;
                font-family: 'Segoe UI';
                font-size: 12px;
                background: transparent;
                padding: 5px;
                border: none;
            }
        """)
        
        # Aktiviere Textumbruch
        self.label.setWordWrap(True)
        
        # Berechne die optimale Breite für den Text
        metrics = self.label.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        
        # Maximale und minimale Breite für die Bubble
        max_bubble_width = 250  # Reduziert von 300
        min_bubble_width = 60   # Reduziert von 80
        
        # Padding für die Berechnung
        total_padding = 20  # Reduziert von 30
        
        if text_width + total_padding > max_bubble_width:
            # Text ist zu lang, nutze maximale Breite
            self.label.setMinimumWidth(max_bubble_width - total_padding)
            self.label.setMaximumWidth(max_bubble_width - total_padding)
        else:
            # Text passt in eine Zeile, nutze exakte Textbreite
            actual_width = text_width + total_padding
            bubble_width = max(min_bubble_width, actual_width)
            self.label.setMinimumWidth(bubble_width - total_padding)
            self.label.setMaximumWidth(bubble_width - total_padding)
        
        # Ausrichtung je nach Nachrichtentyp
        if is_command:
            layout.addStretch()
            layout.addWidget(self.label)
        else:
            layout.addWidget(self.label)
            layout.addStretch()
        
        # Stelle sicher, dass der Text komplett sichtbar ist
        self.label.adjustSize()
        self.adjustSize()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            # Aktualisiere die Breite basierend auf der Fensterbreite
            available_width = self.parent().width() - 100  # Berücksichtige Margins
            max_width = min(300, available_width)  # Maximale Breite oder verfügbare Breite
            
            # Setze die neue Breite
            self.label.setMaximumWidth(max_width)
            self.label.adjustSize()
            
            # Aktualisiere die Bubble-Größe
            self.adjustSize()

class VoiceAssistantGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initialisiere VoiceAssistantGUI")
        self.setWindowTitle("Nova")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(400, 600)  # Breiter und länger
        
        # Hauptwidget
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #000000;")  # Solider schwarzer Hintergrund
        self.setCentralWidget(main_widget)
        
        # Layout
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header Layout für Logo und Exit-Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Platzhalter links für Zentrierung
        spacer_left = QWidget()
        spacer_left.setFixedWidth(30)
        
        # Nova Logo Label
        self.nova_label = GlowLabel("NOVA", self)
        self.nova_label.setFixedHeight(80)
        self.nova_label.setStyleSheet("""
            QLabel {
                color: #00ff9d;
                font-family: 'Segoe UI';
                font-size: 36px;
                font-weight: bold;
                background: transparent;
                margin-left: 20px;  /* Option 1: Verschiebe das Logo nach rechts mit margin */
            }
        """)
        self.nova_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Exit Button
        exit_button = QPushButton("×")
        exit_button.setFixedSize(30, 30)
        exit_button.setStyleSheet("""
            QPushButton {
                color: #00ff9d;
                background-color: transparent;
                border: none;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff0000;
            }
        """)
        exit_button.clicked.connect(self.close)
        
        # Header Layout zusammenbauen
        header_layout.addWidget(spacer_left)
        header_layout.addWidget(self.nova_label, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(exit_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        header_layout.setStretch(0, 2)  # Option 2: Erhöhe den linken Spacer für mehr Rechtsverschiebung
        header_layout.setStretch(1, 11)  # Logo
        header_layout.setStretch(2, 1)  # Exit-Button
        
        # Chat Bereich
        self.chat_frame = QFrame()
        self.chat_frame.setStyleSheet("""
            QFrame {
                background-color: #121212;
                border-radius: 20px;
                margin: 10px;
            }
        """)
        chat_layout = QVBoxLayout(self.chat_frame)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        
        # Scroll Area für Chat
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Horizontale Scrollbar deaktivieren
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #1a1a1a;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #00ff9d;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)
        
        # Chat Widget
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(10)
        
        self.scroll.setWidget(self.chat_widget)
        chat_layout.addWidget(self.scroll)
        
        # Status Label
        self.status_label = QLabel("Warte auf Aktivierung...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #00ff9d;
                font-family: 'Segoe UI';
                font-size: 12px;
                text-align: center;
            }
        """)
        
        # Layout zusammenbauen
        layout.addLayout(header_layout)
        layout.addWidget(self.chat_frame)
        layout.addWidget(self.status_label)
        
        # Test-Nachricht hinzufügen
        QTimer.singleShot(1000, lambda: self.add_message("Das hier ist eine Test-Nachricht, die länger ist und daher in mehrere Zeilen geht.", False))
        
        # Maus-Events für das Verschieben
        self.old_pos = None
        self.nova_label.mousePressEvent = self.mousePressEvent
        self.nova_label.mouseMoveEvent = self.mouseMoveEvent
        
        # Starte den Assistenten in einem separaten Thread
        self.assistant_thread = threading.Thread(target=self.run_assistant)
        self.assistant_thread.daemon = True
        self.assistant_thread.start()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.position().toPoint()
            
    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.position().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            
    def add_message(self, text, is_command):
        """Thread-sichere Methode zum Hinzufügen von Nachrichten"""
        print(f"Versuche Nachricht hinzuzufügen: {text}")  # Debug-Ausgabe
        if not hasattr(self, '_message_queue'):
            self._message_queue = []
        self._message_queue.append((text, is_command))
        QTimer.singleShot(0, self._process_message_queue)

    def _process_message_queue(self):
        """Verarbeitet die Nachrichtenwarteschlange im Hauptthread"""
        if not hasattr(self, '_message_queue'):
            return
        
        while self._message_queue:
            text, is_command = self._message_queue.pop(0)
            try:
                bubble = ChatBubble(text, is_command, self.chat_widget)
                self.chat_layout.addWidget(bubble)
                bubble.show()
                
                # Aktualisiere das Layout
                self.chat_widget.updateGeometry()
                self.chat_widget.update()
                self.chat_frame.update()
                
                # Scrolle zum Ende
                QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(
                    self.scroll.verticalScrollBar().maximum()
                ))
                
                print(f"Nachricht erfolgreich hinzugefügt: {text}")
            except Exception as e:
                print(f"Fehler beim Hinzufügen der Nachricht: {str(e)}")
        
    def update_status(self, text):
        self.status_label.setText(text)
        
    def start_glow_animation(self):
        """Thread-sichere Methode zum Starten der Animation"""
        QTimer.singleShot(0, self.nova_label.start_pulsing)

    def stop_glow_animation(self):
        """Thread-sichere Methode zum Stoppen der Animation"""
        QTimer.singleShot(0, self.nova_label.stop_pulsing)

    def run_assistant(self):
        print("Starte Assistent")
        erstelle_programm_index()
        erstelle_website_index()
        
        self.update_status(f"Warte auf '{AKTIVIERUNGSWORT}'...")
        
        aktiv = True
        while aktiv:
            text = sprache_zu_text(timeout=3)
            
            if text and AKTIVIERUNGSWORT in text:
                print(f"Aktivierungswort erkannt: {text}")
                self.start_glow_animation()
                self.update_status("Aktiviert! Sag deinen Befehl...")
                befehl = sprache_zu_text(timeout=6)
                if befehl:
                    print(f"Befehl erkannt: {befehl}")
                    # Benutzerbefehl anzeigen (rechts)
                    self.add_message(befehl, True)
                    # Verarbeite den Befehl
                    aktiv = self.befehl_verarbeiten(befehl)
                self.stop_glow_animation()
                self.update_status(f"Warte auf '{AKTIVIERUNGSWORT}'...")
            
            time.sleep(0.1)

    def befehl_verarbeiten(self, befehl):
        # Website-Befehle
        if "öffne" in befehl:
            website_name = befehl.replace("öffne", "").strip()
            if website_name in WEBSITE_INDEX:
                antwort = f"Ich öffne {website_name} für dich..."
                self.add_message(antwort, False)
                webbrowser.open(WEBSITE_INDEX[website_name]["url"])
                return True
            else:
                antwort = f"Tut mir leid, ich kenne die Website {website_name} nicht."
                self.add_message(antwort, False)
                return True
        
        # Such-Befehle
        elif "suche auf" in befehl:
            teil = befehl.replace("suche auf", "").strip()
            website_name = teil.split(" nach ")[0].strip()
            suchbegriff = teil.split(" nach ")[1].strip() if " nach " in teil else ""
            
            if website_name in WEBSITE_INDEX and suchbegriff:
                antwort = f"Ich suche auf {website_name} nach '{suchbegriff}'..."
                self.add_message(antwort, False)
                url = WEBSITE_INDEX[website_name]["suche"].format(suchbegriff.replace(" ", "+"))
                webbrowser.open(url)
                return True
            else:
                antwort = "Tut mir leid, ich konnte die Suche nicht ausführen."
                self.add_message(antwort, False)
                return True
        
        # Programm-Befehle
        elif "starte" in befehl:
            programm_name = befehl.replace("starte", "").strip()
            if not programm_name:
                antwort = "Bitte gib den Namen des Programms an, das du starten möchtest."
                self.add_message(antwort, False)
                return True
            
            if programm_name.lower() in PROGRAMM_INDEX:
                antwort = f"Ich starte {programm_name} für dich..."
                self.add_message(antwort, False)
            else:
                antwort = f"Tut mir leid, ich konnte {programm_name} nicht finden."
                self.add_message(antwort, False)
            return starte_programm(programm_name)

        elif "ende" in befehl:
            antwort = "Auf Wiedersehen! Der Assistent wird beendet."
            self.add_message(antwort, False)
            return False

        else:
            antwort = "Tut mir leid, ich verstehe diesen Befehl nicht."
            self.add_message(antwort, False)
        return True

def erstelle_programm_index():
    global PROGRAMM_INDEX
    print("📂 Erstelle Programm-Index...")
    
    # Versuche zuerst, den Index aus der Datei zu laden
    if os.path.exists(PROGRAMM_INDEX_DATEI):
        try:
            with open(PROGRAMM_INDEX_DATEI, 'r') as f:
                PROGRAMM_INDEX = json.load(f)
            print(f"✅ Index aus Datei geladen mit {len(PROGRAMM_INDEX)} Programmen")
            return
        except:
            print("⚠️ Fehler beim Laden des Index, erstelle neuen Index...")
    
    # Liste der gängigen Installationsverzeichnisse
    such_pfade = [
        os.path.expandvars("%ProgramFiles%"),
        os.path.expandvars("%ProgramFiles(x86)%"),
        os.path.expandvars("%LocalAppData%"),
        os.path.expandvars("%AppData%"),
        os.path.expandvars("%SystemRoot%")
    ]
    
    # Suche nach .exe-Dateien
    for pfad in such_pfade:
        for root, dirs, files in os.walk(pfad):
            for file in files:
                if file.endswith('.exe'):
                    # Entferne .exe und mache den Namen klein
                    programm_name = file[:-4].lower()
                    vollstaendiger_pfad = os.path.join(root, file)
                    PROGRAMM_INDEX[programm_name] = vollstaendiger_pfad
    
    # Speichere den Index in einer Datei
    with open(PROGRAMM_INDEX_DATEI, 'w') as f:
        json.dump(PROGRAMM_INDEX, f, indent=4)
    
    print(f"✅ Index erstellt mit {len(PROGRAMM_INDEX)} Programmen")
    print(f"📝 Index wurde in {PROGRAMM_INDEX_DATEI} gespeichert")

def starte_programm(programm_name):
    try:
        # Suche im Index
        if programm_name.lower() in PROGRAMM_INDEX:
            programm_pfad = PROGRAMM_INDEX[programm_name.lower()]
            print(f"🚀 Starte {programm_name}...")
            subprocess.Popen(programm_pfad)
            return True
        else:
            print(f"⚠️ Konnte {programm_name} nicht im Index finden.")
            return False
            
    except Exception as e:
        print(f"⚠️ Fehler beim Starten von {programm_name}: {str(e)}")
        return False

def sprache_zu_text(timeout=5):
    recognizer = sr.Recognizer()
    with sr.Microphone() as quelle:
        try:
            print("🎙️ ...")
            audio = recognizer.listen(quelle, timeout=timeout)
            text = recognizer.recognize_google(audio, language="de-DE").lower()
            print(f"🗣️ Erkannt: {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.WaitTimeoutError:
            return ""
        except sr.RequestError:
            print("⚠️ Problem mit der Spracherkennung.")
            return ""

def erstelle_website_index():
    global WEBSITE_INDEX
    print("🌐 Erstelle Website-Index...")
    
    # Versuche zuerst, den Index aus der Datei zu laden
    if os.path.exists(WEBSITE_INDEX_DATEI):
        try:
            with open(WEBSITE_INDEX_DATEI, 'r') as f:
                WEBSITE_INDEX = json.load(f)
            print(f"✅ Website-Index aus Datei geladen mit {len(WEBSITE_INDEX)} Einträgen")
            return
        except:
            print("⚠️ Fehler beim Laden des Website-Index, erstelle neuen Index...")
    
    # Basis-URLs und Such-URLs für verschiedene Websites
    websites = {
        "youtube": {
            "url": "https://www.youtube.com",
            "suche": "https://www.youtube.com/results?search_query={}"
        },
        "netflix": {
            "url": "https://www.netflix.com",
            "suche": "https://www.netflix.com/search?q={}"
        },
        "crunchyroll": {
            "url": "https://www.crunchyroll.com",
            "suche": "https://www.crunchyroll.com/search?q={}"
        },
        "amazon": {
            "url": "https://www.amazon.de",
            "suche": "https://www.amazon.de/s?k={}"
        },
        "google": {
            "url": "https://www.google.com",
            "suche": "https://www.google.com/search?q={}"
        },
        "wikipedia": {
            "url": "https://de.wikipedia.org",
            "suche": "https://de.wikipedia.org/wiki/Spezial:Suche?search={}"
        }
    }
    
    WEBSITE_INDEX = websites
    
    # Speichere den Index in einer Datei
    with open(WEBSITE_INDEX_DATEI, 'w') as f:
        json.dump(WEBSITE_INDEX, f, indent=4)
    
    print(f"✅ Website-Index erstellt mit {len(WEBSITE_INDEX)} Einträgen")
    print(f"📝 Website-Index wurde in {WEBSITE_INDEX_DATEI} gespeichert")

def main():
    app = QApplication(sys.argv)
    window = VoiceAssistantGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
