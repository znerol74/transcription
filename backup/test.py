from O365 import Account
import os
from dotenv import load_dotenv

load_dotenv()

# --- DEINE DATEN HIER EINTRAGEN ---
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TARGET_EMAIL = os.getenv("TARGET_EMAIL")  # E-Mail Adresse des Postfachs,

credentials = (CLIENT_ID, CLIENT_SECRET)

# Verbindung zum Microsoft 365 Account herstellen
# auth_flow_type='credentials' wird für Hintergrund-Skripte (Application Permissions) genutzt
account = Account(credentials, auth_flow_type='credentials', tenant_id=TENANT_ID)

if account.authenticate():
    print("✅ Verbindung zum Microsoft Server erfolgreich!")
    
    # Zugriff auf das Postfach der spezifischen E-Mail-Adresse
    mailbox = account.mailbox(resource=TARGET_EMAIL)
    
    # Die letzte ungelesene E-Mail abrufen
    # Wir filtern nach 'isRead eq false' und sortieren nach Datum (absteigend)
    messages = mailbox.get_messages(limit=1, query='isRead eq true', order_by='receivedDateTime desc')

    # Liste in Variable umwandeln
    msg_list = list(messages)

    if not msg_list:
        print("❌ Keine ungelesenen E-Mails gefunden.")
    else:
        msg = msg_list[0]
        print(f"📧 E-Mail gefunden: '{msg.subject}' von {msg.sender}")
        
        # Sicherer Weg, um Anhänge bei der O365 Library zu laden
        print("🔍 Suche nach Anhängen...")
        
        # Wir laden die Details der Nachricht inklusive Anhänge explizit nach
        if msg.has_attachments:
            attachments = msg.attachments.download_attachments() # Lädt sie in den Arbeitsspeicher
            
            print(f"📎 Anhänge gefunden: {len(msg.attachments)}")
            
            for attachment in msg.attachments:
                print(f"   -> Datei erkannt: {attachment.name}")
                
                if attachment.name.lower().endswith('.wav'):
                    print(f"⬇️ Speichere WAV-Datei: {attachment.name}")
                    attachment.save(location='.') 
                    print("✅ Download abgeschlossen.")
                else:
                    print(f"ℹ️ Überspringe: {attachment.name}")
        else:
            print("⚠️ Diese E-Mail hat laut 'has_attachments' Flag keine Anhänge.")