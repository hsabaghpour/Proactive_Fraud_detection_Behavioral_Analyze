import numpy as np
from typing import Dict, List, Any
from collections import defaultdict

class BehavioralFeatureExtractor:
    def __init__(self):
        self.feature_names = []

    def extract_keystroke_features(self, keystroke_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extract features from keystroke data
        :param keystroke_data: List of keystroke events
        :return: Dictionary of features
        """
        if not keystroke_data:
            return {}

        # Sort events by timestamp
        events = sorted(keystroke_data, key=lambda x: x['timestamp'])
        
        # Calculate inter-key timings
        press_times = defaultdict(list)
        release_times = defaultdict(list)
        hold_times = defaultdict(list)
        
        for i, event in enumerate(events[:-1]):
            if event['event_type'] == 'keydown':
                # Find matching keyup event
                for j in range(i + 1, len(events)):
                    if (events[j]['event_type'] == 'keyup' and 
                        events[j]['key_code'] == event['key_code']):
                        hold_time = events[j]['timestamp'] - event['timestamp']
                        hold_times[event['key_code']].append(hold_time)
                        break

            if events[i + 1]['event_type'] == 'keydown':
                interval = events[i + 1]['timestamp'] - event['timestamp']
                if interval < 2.0:  # Filter out long pauses
                    press_times[event['key_code']].append(interval)

        features = {
            'mean_hold_time': np.mean([t for times in hold_times.values() for t in times]),
            'std_hold_time': np.std([t for times in hold_times.values() for t in times]),
            'mean_interkey_time': np.mean([t for times in press_times.values() for t in times]),
            'std_interkey_time': np.std([t for times in press_times.values() for t in times]),
            'typing_speed': len(events) / (events[-1]['timestamp'] - events[0]['timestamp'])
        }

        return features

    def extract_mouse_features(self, mouse_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extract features from mouse movement data
        :param mouse_data: List of mouse events
        :return: Dictionary of features
        """
        if not mouse_data:
            return {}

        # Sort events by timestamp
        events = sorted(mouse_data, key=lambda x: x['timestamp'])
        
        # Calculate movement features
        movements = [e for e in events if e['type'] == 'movement']
        clicks = [e for e in events if e['type'] == 'click']
        
        if len(movements) < 2:
            return {}

        # Calculate velocities and accelerations
        velocities = []
        accelerations = []
        for i in range(1, len(movements)):
            dt = movements[i]['timestamp'] - movements[i-1]['timestamp']
            if dt > 0:
                dx = movements[i]['x'] - movements[i-1]['x']
                dy = movements[i]['y'] - movements[i-1]['y']
                velocity = np.sqrt(dx*dx + dy*dy) / dt
                velocities.append(velocity)
                
                if i > 1:
                    prev_velocity = velocities[-2]
                    acceleration = (velocity - prev_velocity) / dt
                    accelerations.append(acceleration)

        features = {
            'mean_velocity': np.mean(velocities),
            'std_velocity': np.std(velocities),
            'mean_acceleration': np.mean(accelerations) if accelerations else 0,
            'std_acceleration': np.std(accelerations) if accelerations else 0,
            'click_frequency': len(clicks) / (events[-1]['timestamp'] - events[0]['timestamp']),
            'movement_smoothness': np.mean(accelerations) if accelerations else 0
        }

        return features

    def extract_device_features(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from device information
        :param device_info: Device information dictionary
        :return: Dictionary of features
        """
        # Convert resolution to numeric values
        if 'screen_resolution' in device_info:
            width, height = map(int, device_info['screen_resolution'].split('x'))
            features = {
                'screen_width': width,
                'screen_height': height,
                'screen_ratio': width / height,
                'is_mobile': 1 if device_info.get('is_mobile', False) else 0,
                'timezone_offset': device_info.get('timezone_offset', 0)
            }
        else:
            features = {
                'screen_width': 0,
                'screen_height': 0,
                'screen_ratio': 0,
                'is_mobile': 0,
                'timezone_offset': 0
            }

        return features

    def extract_all_features(self, session_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract all features from a session
        :param session_data: Complete session data
        :return: Dictionary of all features
        """
        features = {}
        
        # Extract features from each data type
        keystroke_features = self.extract_keystroke_features(session_data.get('keystroke_data', []))
        mouse_features = self.extract_mouse_features(session_data.get('mouse_data', []))
        device_features = self.extract_device_features(session_data.get('device_info', {}))
        
        # Combine all features
        features.update({f'keystroke_{k}': v for k, v in keystroke_features.items()})
        features.update({f'mouse_{k}': v for k, v in mouse_features.items()})
        features.update({f'device_{k}': v for k, v in device_features.items()})
        
        # Add session-level features
        features['session_duration'] = session_data.get('session_duration', 0)
        
        self.feature_names = list(features.keys())
        return features 