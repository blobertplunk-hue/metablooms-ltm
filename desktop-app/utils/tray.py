"""
System Tray - Minimize to tray and show notifications
"""

import os
import sys
import threading
from typing import Callable, List, Tuple

# Try to import pystray (optional dependency)
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    pystray = None


def create_icon_image(color: str = "#569cd6", size: int = 64) -> 'Image':
    """Create a simple icon image"""
    if not HAS_TRAY:
        return None

    # Create a simple colored square icon
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Parse color
    if color.startswith('#'):
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
    else:
        r, g, b = 86, 156, 214  # Default blue

    # Draw a rounded rectangle with M
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=8,
        fill=(r, g, b, 255)
    )

    # Draw "M" for MetaBlooms
    draw.text(
        (size // 2, size // 2),
        "M",
        fill=(255, 255, 255, 255),
        anchor="mm"
    )

    return image


class SystemTray:
    """System tray icon and menu"""

    STATUS_COLORS = {
        "synced": "#4ec9b0",    # Green
        "syncing": "#cca700",   # Yellow
        "error": "#f14c4c",     # Red
        "offline": "#808080"    # Gray
    }

    def __init__(self, app_name: str = "MetaBlooms Sync"):
        self.app_name = app_name
        self.icon = None
        self.status = "synced"
        self.is_running = False

        # Callbacks
        self.on_show_window = None
        self.on_sync_all = None
        self.on_quit = None
        self.menu_items: List[Tuple[str, Callable]] = []

    def is_available(self) -> bool:
        """Check if system tray is available"""
        return HAS_TRAY

    def add_menu_item(self, label: str, callback: Callable):
        """Add a menu item"""
        self.menu_items.append((label, callback))

    def set_status(self, status: str):
        """Update status icon color"""
        if status in self.STATUS_COLORS and self.icon:
            self.status = status
            color = self.STATUS_COLORS[status]
            self.icon.icon = create_icon_image(color)

    def _create_menu(self):
        """Create the tray menu"""
        if not HAS_TRAY:
            return None

        items = []

        # Show window
        items.append(pystray.MenuItem(
            "Show Window",
            lambda: self.on_show_window() if self.on_show_window else None,
            default=True
        ))

        items.append(pystray.Menu.SEPARATOR)

        # Sync all
        items.append(pystray.MenuItem(
            "Sync All Repos",
            lambda: self.on_sync_all() if self.on_sync_all else None
        ))

        # Custom menu items
        if self.menu_items:
            items.append(pystray.Menu.SEPARATOR)
            for label, callback in self.menu_items:
                items.append(pystray.MenuItem(label, callback))

        items.append(pystray.Menu.SEPARATOR)

        # Status indicator (not clickable)
        items.append(pystray.MenuItem(
            f"Status: {self.status.title()}",
            lambda: None,
            enabled=False
        ))

        items.append(pystray.Menu.SEPARATOR)

        # Quit
        items.append(pystray.MenuItem(
            "Quit",
            lambda: self._quit()
        ))

        return pystray.Menu(*items)

    def _quit(self):
        """Quit the app"""
        if self.on_quit:
            self.on_quit()
        self.stop()

    def start(self):
        """Start the system tray"""
        if not HAS_TRAY:
            return False

        if self.is_running:
            return True

        try:
            image = create_icon_image(self.STATUS_COLORS[self.status])
            menu = self._create_menu()

            self.icon = pystray.Icon(
                self.app_name,
                image,
                self.app_name,
                menu
            )

            # Run in background thread
            self.is_running = True
            thread = threading.Thread(target=self.icon.run, daemon=True)
            thread.start()

            return True

        except Exception as e:
            print(f"Failed to start system tray: {e}")
            return False

    def stop(self):
        """Stop the system tray"""
        self.is_running = False
        if self.icon:
            try:
                self.icon.stop()
            except:
                pass
            self.icon = None

    def show_notification(self, title: str, message: str):
        """Show a notification"""
        if not HAS_TRAY or not self.icon:
            return

        try:
            self.icon.notify(message, title)
        except:
            pass

    def update_menu(self):
        """Update the menu (call after changing menu items)"""
        if self.icon:
            self.icon.menu = self._create_menu()


def show_toast_notification(title: str, message: str):
    """Show a Windows toast notification without pystray"""
    if sys.platform == 'win32':
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5, threaded=True)
            return True
        except ImportError:
            pass

        # Fallback to PowerShell
        try:
            import subprocess
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
            $template = "<toast><visual><binding template='ToastText02'><text id='1'>{title}</text><text id='2'>{message}</text></binding></visual></toast>"
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("MetaBlooms Sync").Show($toast)
            '''
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
            return True
        except:
            pass

    return False


if __name__ == "__main__":
    if HAS_TRAY:
        print("System tray available")
        tray = SystemTray()

        def show():
            print("Show window!")

        def sync():
            print("Sync all!")

        tray.on_show_window = show
        tray.on_sync_all = sync

        print("Starting tray...")
        tray.start()

        import time
        time.sleep(3)

        print("Setting status to syncing...")
        tray.set_status("syncing")

        time.sleep(3)

        print("Showing notification...")
        tray.show_notification("Test", "This is a test notification")

        time.sleep(5)
        tray.stop()
    else:
        print("System tray NOT available - install pystray and Pillow")
