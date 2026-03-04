import sys
import os
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from ui.splash import SplashScreen
from ui.main_window import MainWindow

def log_error(err):
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write("\n" + "="*50 + "\n")
        f.write(traceback.format_exc())
        f.write("\n" + "="*50 + "\n")

def main():
    try:
        # Windows'ta Görev Çubuğu (Taskbar) ikonunun Python logotipine dönmemesi için:
        if sys.platform == "win32":
            import ctypes
            myappid = 'serco.localainotetaker.app.1.0' # Arbitrary benzersiz ID
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        app.splash = SplashScreen()
        app.main_window = None

        def launch_main_app():
            try:
                app.splash.hide()
                app.main_window = MainWindow()
                app.main_window.show()
            except Exception as e:
                log_error(e)
                QMessageBox.critical(None, "Hata", f"Uygulama başlatılamadı:\n{str(e)}")
                sys.exit(1)

        app.splash.finished.connect(launch_main_app)
        app.splash.show()

        code = app.exec()
        sys.exit(code)
    except Exception as e:
        log_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
