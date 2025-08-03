#player.py
from bs4 import BeautifulSoup
from numpy import random
import time
import pyautogui
import pandas as pd
import json
import pyautogui
import sys
from pynput import keyboard, mouse
import functools
import logging
import hashlib
import cv2
import numpy as np
import os
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("automation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
#im changing this
class SeleniumBot:
    """Minimal base class — no browser initialized."""
    def __init__(self):
        # No driver, no Chrome
        self.wait = None
        self.default_timeout = 10
        self.retry_attempts = 5
        self.ignored_exceptions = (Exception,)  # Placeholder
        self.action_count = 0
        self.last_action_time = time.time()
        self.last_click_time = time.time()
        self.mouse_movement_history = []
    
    def random_delay(self, min_seconds=0.5, max_seconds=3.0):
        mu = (min_seconds + max_seconds) / 2
        sigma = (max_seconds - min_seconds) / 6
        delay = random.normal(mu, sigma)
        delay = max(min_seconds, min(max_seconds, delay))
        time.sleep(delay)
        logger.debug(f"Random delay: {delay:.2f}s")
    
    def retry_on_exception(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            for attempt in range(self.retry_attempts):
                try:
                    return f(self, *args, **kwargs)
                except Exception as e:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    if attempt == self.retry_attempts - 1:
                        logger.error(f"Final attempt failed: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt+1} failed: {str(e)}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
            return None
        return wrapper
    
    def human_mouse_move(self, x, y):
        logger.debug(f"Moving mouse to ({x}, {y})")
        start_x, start_y = pyautogui.position()
        distance = ((x - start_x)**2 + (y - start_y)**2)**0.5
        ctrl_x = (start_x + x) / 2 + random.uniform(-distance/3, distance/3)
        ctrl_y = (start_y + y) / 2 + random.uniform(-distance/3, distance/3)
        points = []
        for t in [i/10 for i in range(1, 11)]:
            bx = (1-t)**2*start_x + 2*(1-t)*t*ctrl_x + t**2*x
            by = (1-t)**2*start_y + 2*(1-t)*t*ctrl_y + t**2*y
            points.append((bx, by))
        for point in points:
            pyautogui.moveTo(point[0], point[1], duration=0.01)
            time.sleep(0.01)
        pyautogui.moveTo(x, y, duration=0.1)
        self.mouse_movement_history.append((start_x, start_y, x, y))
    
    def execute_with_timing(self, idx, action):
        delay = action.get('delay_before', random.uniform(0.5, 1.5))
        logger.debug(f"Action {idx}: Waiting {delay:.2f}s before action")
        time.sleep(max(0.1, min(delay, 5.0)))
        
        try:
            if action['type'] == 'click':
                self.random_delay(0.5, 1.0)
                abs_x = action['coordinates']['x']
                abs_y = action['coordinates']['y']
                self.human_mouse_move(abs_x, abs_y)
                time.sleep(0.2)
                pyautogui.click()
                self.last_click_time = time.time()
                logger.info(f"Clicked at ({abs_x}, {abs_y})")
                
            elif action['type'] == 'type_string':
                if 'text' in action:
                    if 'delay_after_click' in action:
                        time_since_click = time.time() - self.last_click_time
                        required_delay = action['delay_after_click']
                        if time_since_click < required_delay:
                            wait_time = required_delay - time_since_click
                            logger.debug(f"Waiting {wait_time:.2f}s after click before typing")
                            time.sleep(wait_time)
                    for char in action['text']:
                        pyautogui.write(char)
                        time.sleep(random.uniform(0.05, 0.15))
                    logger.info(f"Typed text: {action['text']}")
                    
            elif action['type'] == 'keystroke':
                if 'delay_after_click' in action:
                    time_since_click = time.time() - self.last_click_time
                    required_delay = action['delay_after_click']
                    if time_since_click < required_delay:
                        wait_time = required_delay - time_since_click
                        logger.debug(f"Waiting {wait_time:.2f}s after click before keystroke")
                        time.sleep(wait_time)
                key = action['key'].replace('Key.', '')
                key_mapping = {
                    'space': 'space', 'enter': 'enter', 'backspace': 'backspace',
                    'tab': 'tab', 'esc': 'escape', 'up': 'up', 'down': 'down',
                    'left': 'left', 'right': 'right', 'delete': 'delete',
                    'shift': 'shift', 'ctrl': 'ctrl', 'alt': 'alt'
                }
                if key in key_mapping:
                    pyautogui.press(key_mapping[key])
                    logger.info(f"Pressed special key: {key}")
                    
            elif action['type'] == 'scroll':
                coords = action.get('coordinates', {})
                # Simulate scroll via pyautogui
                dx = action.get('delta', {}).get('x', 0)
                dy = action.get('delta', {}).get('y', 0)
                if dy != 0:
                    pyautogui.scroll(int(dy))
                logger.info(f"Simulated scroll: delta_y={dy}")
                
            # Handle clipboard operations in all possible formats
            elif action['type'] in ['clipboard', 'copy', 'paste', 'cut', 'select_all']:
                operation = None
                
                # Extract operation from various possible formats
                if action['type'] == 'clipboard':
                    operation = action.get('operation')
                else:
                    # Direct type mapping (e.g., type='copy')
                    operation = action['type']
                
                if operation == 'copy' or operation == 'c':
                    # Added delay before Ctrl+C to ensure selection
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'c')
                    logger.info("Performed Ctrl+C operation")
                    
                elif operation == 'paste' or operation == 'v':
                    # Added delay before Ctrl+V to ensure focus
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'v')
                    logger.info("Performed Ctrl+V operation")
                    
                elif operation == 'cut' or operation == 'x':
                    # Added delay before Ctrl+X to ensure selection
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'x')
                    logger.info("Performed Ctrl+X operation")
                    
                elif operation == 'select_all' or operation == 'a':
                    # Added delay before Ctrl+A to ensure context
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'a')
                    logger.info("Performed Ctrl+A operation")
                    
            elif action['type'] == 'drag_start':
                abs_x = action['coordinates']['x']
                abs_y = action['coordinates']['y']
                self.human_mouse_move(abs_x, abs_y)
                pyautogui.mouseDown()
                logger.info(f"Started drag at ({abs_x}, {abs_y})")
                
            elif action['type'] == 'drag_end':
                abs_x = action['coordinates']['x']
                abs_y = action['coordinates']['y']
                self.human_mouse_move(abs_x, abs_y)
                pyautogui.mouseUp()
                logger.info(f"Ended drag at ({abs_x}, {abs_y})")
                
            elif action['type'] == 'drag_drop':
                start_x = action['from']['x']
                start_y = action['from']['y']
                end_x = action['to']['x']
                end_y = action['to']['y']
                self.human_mouse_move(start_x, start_y)
                pyautogui.mouseDown()
                self.human_mouse_move(end_x, end_y)
                pyautogui.mouseUp()
                logger.info(f"Performed drag_drop from ({start_x}, {start_y}) to ({end_x}, {end_y})")
                
            if action['type'] == 'click':
                self.random_delay(0.1, 0.3)
                
        except Exception as e:
            logger.error(f"Failed to execute action {idx}: {str(e)}")
            raise
    
    def close(self):
        logger.info("Shutting down (no browser to close)")
#deprecated
class SequenceRecorder(SeleniumBot):
    """Records user actions (mouse/keyboard) without opening Chrome."""
    def __init__(self, output_file, initial_sequence=None):
        super().__init__()
        self.output_file = output_file
        self.initial_sequence = initial_sequence
        self.actions = []
        self.recording = True
        self.desktop_mode = True  # Always in desktop mode
        self.last_event_time = time.time()
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.last_scroll_time = time.time()
        self.scroll_threshold = 0.1
        logger.info(f"Starting desktop recording session: {self.session_id}")
    
    def play_initial_sequence(self):
        """Play initial sequence (if provided)"""
        if not self.initial_sequence:
            return
        try:
            if isinstance(self.initial_sequence, list):
                chain_player = MultiSequencePlayer(chain_config=self.initial_sequence)
                chain_player.play_chain()
            else:
                player = SequencePlayer(sequence_file=self.initial_sequence)
                player.play_sequence()
            logger.info("Initial sequence playback completed")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to play initial sequence: {str(e)}")
    
    def start_recording(self):
        logger.info("Starting desktop recording...")
        if self.initial_sequence:
            logger.info("Playing initial sequence...")
            self.play_initial_sequence()
        logger.info("Recording started! F8=toggle mode, Esc=stop")
        mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)
        keyboard_listener = keyboard.Listener(on_release=self.on_key_release)
        mouse_listener.start()
        keyboard_listener.start()
        try:
            while self.recording:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.warning("Recording interrupted by user")
        finally:
            keyboard_listener.stop()
            mouse_listener.stop()
            self.save_recording()
            logger.info(f"Recording saved to {self.output_file}")
    
    def on_click(self, x, y, button, pressed):
        if not pressed or not self.recording:
            return
        current_time = time.time()
        time_since_last = current_time - self.last_event_time
        self.last_event_time = current_time
        action = {
            'type': 'click',
            'coordinates': {'x': x, 'y': y},
            'timestamp': current_time,
            'delay_before': time_since_last
        }
        self.actions.append(action)
        logger.info(f"Recorded desktop click at ({x}, {y})")
    
    def on_key_release(self, key):
        if not self.recording:
            return False
        current_time = time.time()
        time_since_last = current_time - self.last_event_time
        self.last_event_time = current_time
        if key == keyboard.Key.f8:
            self.desktop_mode = not self.desktop_mode
            mode = "DESKTOP" if self.desktop_mode else "BROWSER (N/A)"
            logger.info(f"Switched to {mode} mode")
            return
        if key == keyboard.Key.esc:
            self.recording = False
            return False
        key_data = {'timestamp': current_time, 'delay_before': time_since_last}
        if hasattr(key, 'char') and key.char:
            key_data['type'] = 'type_string'
            key_data['text'] = key.char
            self.actions.append(key_data)
            logger.info(f"Recorded key: {key.char}")
        else:
            key_data['type'] = 'keystroke'
            key_data['key'] = str(key)
            self.actions.append(key_data)
            logger.info(f"Recorded special key: {key}")
    
    def on_scroll(self, x, y, dx, dy):
        if not self.recording:
            return
        current_time = time.time()
        if current_time - self.last_scroll_time > self.scroll_threshold:
            delay = current_time - self.last_event_time
            action = {
                'type': 'scroll',
                'coordinates': {'x': x, 'y': y},
                'delta': {'x': dx, 'y': dy},
                'timestamp': current_time,
                'delay_before': delay
            }
            self.actions.append(action)
            logger.info(f"Recorded scroll at ({x}, {y}) with delta ({dx}, {dy})")
            self.last_scroll_time = current_time
            self.last_event_time = current_time
    
    def save_recording(self):
        metadata = {
            "session_id": self.session_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "actions_count": len(self.actions),
            "duration": time.time() - self.last_event_time,
            "config": {"mode": "desktop_only"}
        }
        recording = {
            "metadata": metadata,
            "actions": self.actions
        }
        with open(self.output_file, 'w') as f:
            json.dump(recording, f, indent=2)

class SequencePlayer(SeleniumBot):
    """Plays back recorded desktop actions without Chrome."""
    def __init__(self, sequence_file):
        super().__init__()
        self.sequence_data = self.load_sequence(sequence_file)
        self.running = True
        self.loop_counter = 0
        logger.info(f"Loaded sequence for playback: {sequence_file}")
    
    def load_sequence(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        if "actions" not in data:
            raise ValueError("Invalid sequence format: Missing actions")
        logger.info(f"Sequence contains {len(data['actions'])} actions")
        return data
    
    def play_sequence(self):
        logger.info("Starting desktop playback")
        time.sleep(2)
        self.last_action_time = time.time()
        for idx, action in enumerate(self.sequence_data['actions']):
            try:
                self.execute_with_timing(idx, action)
            except Exception as e:
                logger.error(f"Action {idx} failed: {str(e)}")
                break
        logger.info("Playback completed")

class MultiSequencePlayer(SequencePlayer):
    """Plays multiple sequences in chain."""
    def __init__(self, chain_config):
        SeleniumBot.__init__(self)
        self.chain_config = chain_config
        logger.info(f"Loaded chain with {len(chain_config)} sequences")
    
    def play_chain(self):
        logger.info("Starting chain playback")
        time.sleep(2)
        for item in self.chain_config:
            seq_file = item['sequence_file']
            loops = item['loop_count']
            extra_delay = item.get('extra_delay', 1)
            try:
                with open(seq_file, 'r') as f:
                    sequence_data = json.load(f)
                logger.info(f"Playing {seq_file} for {loops} loops")
            except Exception as e:
                logger.error(f"Failed to load {seq_file}: {str(e)}")
                continue
            for i in range(loops):
                logger.info(f"Loop {i+1}/{loops}")
                self.sequence_data = sequence_data
                self.play_sequence()
                time.sleep(max(1, extra_delay))
        logger.info("Chain playback completed")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <mode> <file>")
        print("Modes: record, play, chain")
        sys.exit(1)
    mode = sys.argv[1]
    file = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if mode == "record":
            if not file:
                print("Output file required for recording")
                sys.exit(1)
            recorder = SequenceRecorder(output_file=file)
            recorder.start_recording()
        elif mode == "play":
            if not file:
                print("Sequence file required for playback")
                sys.exit(1)
            player = SequencePlayer(sequence_file=file)
            player.play_sequence()
        elif mode == "chain":
            if not file:
                print("Chain config file required")
                sys.exit(1)
            with open(file) as f:
                chain_config = json.load(f)
            player = MultiSequencePlayer(chain_config=chain_config)
            player.play_chain()
        else:
            print(f"Invalid mode: {mode}")
            sys.exit(1)
    except Exception as e:
        logger.exception("Fatal error during execution")
        sys.exit(1)
    finally:
        pass  # No browser to close