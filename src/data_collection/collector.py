import time
from datetime import datetime
from typing import Dict, List, Any
import json
import hashlib

class BehavioralDataCollector:
    def __init__(self):
        self.keystroke_buffer: List[Dict[str, Any]] = []
        self.mouse_buffer: List[Dict[str, Any]] = []
        self.session_start = datetime.now()
        self.session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID based on timestamp and random data"""
        timestamp = str(time.time()).encode()
        return hashlib.sha256(timestamp).hexdigest()[:16]

    def collect_keystroke(self, event_type: str, key_code: int, timestamp: float) -> None:
        """
        Collect keystroke events
        :param event_type: 'keydown' or 'keyup'
        :param key_code: ASCII code of the key
        :param timestamp: Unix timestamp of the event
        """
        self.keystroke_buffer.append({
            "event_type": event_type,
            "key_code": key_code,  # Store only the key code, not the actual key for privacy
            "timestamp": timestamp
        })

    def collect_mouse_movement(self, x: float, y: float, timestamp: float) -> None:
        """
        Collect mouse movement data
        :param x: X coordinate
        :param y: Y coordinate
        :param timestamp: Unix timestamp of the event
        """
        self.mouse_buffer.append({
            "type": "movement",
            "x": x,
            "y": y,
            "timestamp": timestamp
        })

    def collect_mouse_click(self, x: float, y: float, button: str, timestamp: float) -> None:
        """
        Collect mouse click events
        :param x: X coordinate
        :param y: Y coordinate
        :param button: Which mouse button was clicked
        :param timestamp: Unix timestamp of the event
        """
        self.mouse_buffer.append({
            "type": "click",
            "x": x,
            "y": y,
            "button": button,
            "timestamp": timestamp
        })

    def collect_device_info(self) -> Dict[str, Any]:
        """
        Collect anonymous device information
        Returns a dictionary of device characteristics
        """
        # Note: In a real implementation, this would use JavaScript to collect
        # browser/device information securely
        return {
            "screen_resolution": "1920x1080",  # Example
            "browser_language": "en-US",
            "timezone_offset": -240,  # Example: EST
            "platform": "MacOS",
            "is_mobile": False
        }

    def get_session_data(self) -> Dict[str, Any]:
        """
        Get all collected data for the current session
        """
        return {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "keystroke_data": self.keystroke_buffer,
            "mouse_data": self.mouse_buffer,
            "device_info": self.collect_device_info()
        }

    def clear_buffers(self) -> None:
        """Clear all data buffers"""
        self.keystroke_buffer.clear()
        self.mouse_buffer.clear()

    def save_session(self, filepath: str) -> None:
        """
        Save the current session data to a file
        :param filepath: Path to save the session data
        """
        with open(filepath, 'w') as f:
            json.dump(self.get_session_data(), f, indent=2) 