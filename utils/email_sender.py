import os
import urllib.parse

def send_email_mailto(subject, body):
    """
    Opens the default email client (Outlook, Mail, Mailbird etc.) using the mailto: protocol.
    """
    try:
        # Kodlamayı default windows mail client algılayabilecek şekilde URL Encoding yapıyoruz
        subject_enc = urllib.parse.quote(subject)
        body_enc = urllib.parse.quote(body)
        
        # Sınırlandırmalar gereği bazen çok uzun mesajlar çalışmayabilir ama özetler için genelde sorun olmaz
        mailto_url = f"mailto:?subject={subject_enc}&body={body_enc}"
        os.startfile(mailto_url)
        return True
    except Exception as e:
        print(f"E-posta istemcisi başlatılamadı: {e}")
        return False
