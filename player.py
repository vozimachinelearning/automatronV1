
# player.py

# Import necessary libraries
from bs4 import BeautifulSoup       # Used for parsing HTML and XML, though not actively used in this script's logic.
from numpy import random            # Used for generating random numbers, especially for human-like delays.
import time                         # Provides time-related functions, essential for delays and timestamps.
import pyautogui                    # Core library for GUI automation: controls mouse and keyboard.
import pandas as pd                 # Data analysis library, not actively used in this script's logic.
import json                         # Used for reading and writing JSON files (for action sequences).
import sys                          # Provides access to system-specific parameters and functions, like command-line arguments.
from pynput import keyboard, mouse  # Used to listen for and record keyboard and mouse events.
import functools                    # Used for creating decorators, like the retry mechanism.
import logging                      # Library for logging events, errors, and debugging information.
import hashlib                      # Used to generate a unique session ID for recordings.
import cv2                          # OpenCV library for computer vision, not actively used in this script's logic.
import numpy as np                  # Fundamental package for scientific computing with Python.
import os                           # Provides a way of using operating system dependent functionality.
from datetime import datetime       # Used for timestamping, not actively used in this script's logic.


# --- Logging Configuration ---
# Sets up how the script will log information. It will both save to a file ('automation.log')
# and print to the console.
logging.basicConfig(
    level=logging.INFO,  # Sets the minimum level of messages to log (INFO, DEBUG, WARNING, ERROR).
    format='%(asctime)s - %(levelname)s - %(message)s',  # Defines the format of the log messages.
    handlers=[
        logging.FileHandler("automation.log"),  # Handler to write logs to a file.
        logging.StreamHandler(sys.stdout)       # Handler to print logs to the console.
    ]
)
# Creates a logger instance for the script.
logger = logging.getLogger(__name__)

# --- Base Bot Class ---

class SeleniumBot:
    """
    A base class for automation bots.
    Despite the name, it does not use Selenium. It provides foundational
    functionalities like human-like delays, mouse movements, and action execution
    using pyautogui.
    """
    def __init__(self):
        """
        Initializes the bot's attributes.
        """
        self.wait = None                     # Placeholder for a Selenium-like wait object.
        self.default_timeout = 10            # Default timeout in seconds for operations.
        self.retry_attempts = 5              # Number of times to retry a failed action.
        self.ignored_exceptions = (Exception,) # Placeholder for exceptions to ignore during retries.
        self.action_count = 0                # Counter for the number of actions performed.
        self.last_action_time = time.time()  # Timestamp of the last action.
        self.last_click_time = time.time()   # Timestamp of the last click, for timing subsequent actions.
        self.mouse_movement_history = []     # Stores a history of mouse movements.

    def random_delay(self, min_seconds=0.5, max_seconds=3.0):
        """
        Waits for a random amount of time to simulate human behavior.
        The delay follows a normal (Gaussian) distribution between the min and max values.
        
        Args:
            min_seconds (float): The minimum delay time.
            max_seconds (float): The maximum delay time.
        """
        mu = (min_seconds + max_seconds) / 2      # Calculate the mean (center) of the distribution.
        sigma = (max_seconds - min_seconds) / 6   # Calculate the standard deviation.
        delay = random.normal(mu, sigma)          # Generate a delay from the normal distribution.
        delay = max(min_seconds, min(max_seconds, delay)) # Ensure the delay is within the specified bounds.
        time.sleep(delay)                         # Pause the script execution.
        logger.debug(f"Random delay: {delay:.2f}s")

    def retry_on_exception(f):
        """
        A decorator that retries a function if it raises an exception.
        It uses an exponential backoff strategy, waiting longer after each failed attempt.
        """
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            for attempt in range(self.retry_attempts):
                try:
                    # Try to execute the function.
                    return f(self, *args, **kwargs)
                except Exception as e:
                    # Calculate wait time with exponential backoff plus some randomness.
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    if attempt == self.retry_attempts - 1:
                        # If this was the last attempt, log the final failure and re-raise the exception.
                        logger.error(f"Final attempt failed: {str(e)}")
                        raise
                    # Log the failure and the upcoming retry attempt.
                    logger.warning(f"Attempt {attempt+1} failed: {str(e)}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
            return None # Should not be reached if an exception is always raised.
        return wrapper

    def human_mouse_move(self, x, y):
        """
        Moves the mouse cursor to a target coordinate (x, y) in a human-like, curved path.
        This avoids straight, robotic mouse movements. It uses a quadratic Bézier curve.

        Args:
            x (int): The target x-coordinate.
            y (int): The target y-coordinate.
        """
        logger.debug(f"Moving mouse to ({x}, {y})")
        start_x, start_y = pyautogui.position() # Get the current mouse position.
        distance = ((x - start_x)**2 + (y - start_y)**2)**0.5 # Calculate the distance to the target.

        # Calculate a random control point for the Bézier curve.
        # This point pulls the curve away from a straight line.
        ctrl_x = (start_x + x) / 2 + random.uniform(-distance/3, distance/3)
        ctrl_y = (start_y + y) / 2 + random.uniform(-distance/3, distance/3)

        points = []
        # Generate points along the Bézier curve.
        for t in [i/10 for i in range(1, 11)]: # t goes from 0.1 to 1.0.
            # Quadratic Bézier formula: B(t) = (1-t)^2*P0 + 2(1-t)t*P1 + t^2*P2
            bx = (1-t)**2*start_x + 2*(1-t)*t*ctrl_x + t**2*x
            by = (1-t)**2*start_y + 2*(1-t)*t*ctrl_y + t**2*y
            points.append((bx, by))

        # Move the mouse through the generated points.
        for point in points:
            pyautogui.moveTo(point[0], point[1], duration=0.01)
            time.sleep(0.01) # Small sleep to make movement smoother.

        # Final move to the exact target coordinate.
        pyautogui.moveTo(x, y, duration=0.1)
        self.mouse_movement_history.append((start_x, start_y, x, y))

    def execute_with_timing(self, idx, action):
        """
        Executes a single action from a sequence (e.g., click, type, scroll).
        It handles timing, delays, and different action types based on the 'action' dictionary.

        Args:
            idx (int): The index of the action in the sequence.
            action (dict): A dictionary describing the action to be performed.
        """
        # Get the delay before the action, or use a default random delay.
        delay = action.get('delay_before', random.uniform(0.5, 1.5))
        logger.debug(f"Action {idx}: Waiting {delay:.2f}s before action")
        # Ensure the delay is within a reasonable range (0.1 to 5.0 seconds).
        time.sleep(max(0.1, min(delay, 5.0)))

        try:
            # --- Handle CLICK action ---
            if action['type'] == 'click':
                self.random_delay(0.5, 1.0) # Add a small random delay before clicking.
                abs_x = action['coordinates']['x']
                abs_y = action['coordinates']['y']
                self.human_mouse_move(abs_x, abs_y) # Move mouse to the target.
                time.sleep(0.2) # Short pause before the click.
                pyautogui.click() # Perform the click.
                self.last_click_time = time.time() # Record the time of the click.
                logger.info(f"Clicked at ({abs_x}, {abs_y})")

            # --- Handle TYPE_STRING action ---
            elif action['type'] == 'type_string':
                if 'text' in action:
                    # Check if a specific delay is required after a click before typing.
                    if 'delay_after_click' in action:
                        time_since_click = time.time() - self.last_click_time
                        required_delay = action['delay_after_click']
                        if time_since_click < required_delay:
                            wait_time = required_delay - time_since_click
                            logger.debug(f"Waiting {wait_time:.2f}s after click before typing")
                            time.sleep(wait_time)
                    # Type the text character by character with small random delays.
                    for char in action['text']:
                        pyautogui.write(char)
                        time.sleep(random.uniform(0.05, 0.15))
                    logger.info(f"Typed text: {action['text']}")

            # --- Handle KEYSTROKE action (for special keys like Enter, Tab, etc.) ---
            elif action['type'] == 'keystroke':
                # Similar to typing, check for a required delay after a click.
                if 'delay_after_click' in action:
                    time_since_click = time.time() - self.last_click_time
                    required_delay = action['delay_after_click']
                    if time_since_click < required_delay:
                        wait_time = required_delay - time_since_click
                        logger.debug(f"Waiting {wait_time:.2f}s after click before keystroke")
                        time.sleep(wait_time)
                # Clean the key name (e.g., 'Key.enter' -> 'enter').
                key = action['key'].replace('Key.', '')
                # Map pynput key names to pyautogui key names.
                key_mapping = {
                    'space': 'space', 'enter': 'enter', 'backspace': 'backspace',
                    'tab': 'tab', 'esc': 'escape', 'up': 'up', 'down': 'down',
                    'left': 'left', 'right': 'right', 'delete': 'delete',
                    'shift': 'shift', 'ctrl': 'ctrl', 'alt': 'alt'
                }
                if key in key_mapping:
                    pyautogui.press(key_mapping[key]) # Press the special key.
                    logger.info(f"Pressed special key: {key}")

            # --- Handle SCROLL action ---
            elif action['type'] == 'scroll':
                # Extract vertical scroll amount from correct field
                dy = action.get('total_delta', 0)  # Use total_delta from recordings
                
                # Fallback to old 'delta' structure for backward compatibility
                if dy == 0 and 'delta' in action and isinstance(action['delta'], dict):
                    dy = action['delta'].get('y', 0)
                
                if dy == 0:
                    logger.info("Scroll action with zero delta, skipping.")
                    return

                # Get step count and duration from recording
                num_steps = max(1, int(action.get('steps', 1)))  # Ensure at least 1 step
                total_duration = action.get('duration_sec', 0.0)
                
                # Calculate per-step scroll amount and timing
                step_dy = dy / num_steps
                step_duration = total_duration / num_steps if total_duration > 0 else 0
                
                logger.info(f"Simulating scroll: total_delta={dy}, steps={num_steps}, duration={total_duration:.3f}s")
                
                # Execute scroll in small steps (mimics real user behavior)
                accumulated = 0.0
                for i in range(num_steps):
                    # Calculate exact step amount (avoids precision loss)
                    current_target = (i + 1) * step_dy
                    rounded_target = round(current_target)
                    step_amount = int(rounded_target - accumulated)
                    accumulated = rounded_target
                    
                    if step_amount != 0:
                        pyautogui.scroll(step_amount)  # Execute small scroll
                    
                    # Pause between steps to match original timing
                    if i < num_steps - 1 and step_duration > 0:
                        time.sleep(step_duration)

            # --- Handle CLIPBOARD actions (copy, paste, cut, select all) ---
            elif action['type'] in ['clipboard', 'copy', 'paste', 'cut', 'select_all']:
                operation = None
                # Determine the operation (e.g., 'copy', 'paste').
                if action['type'] == 'clipboard':
                    operation = action.get('operation')
                else:
                    operation = action['type']
                
                # Execute the corresponding hotkey.
                if operation == 'copy' or operation == 'c':
                    time.sleep(0.1) # Small delay to ensure text is selected before copying.
                    pyautogui.hotkey('ctrl', 'c')
                    logger.info("Performed Ctrl+C operation")
                elif operation == 'paste' or operation == 'v':
                    time.sleep(0.1) # Small delay to ensure the input field is focused.
                    pyautogui.hotkey('ctrl', 'v')
                    logger.info("Performed Ctrl+V operation")
                elif operation == 'cut' or operation == 'x':
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'x')
                    logger.info("Performed Ctrl+X operation")
                elif operation == 'select_all' or operation == 'a':
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'a')
                    logger.info("Performed Ctrl+A operation")

            # --- Handle DRAG_START action ---
            elif action['type'] == 'drag_start':
                abs_x = action['coordinates']['x']
                abs_y = action['coordinates']['y']
                self.human_mouse_move(abs_x, abs_y)
                pyautogui.mouseDown() # Press and hold the mouse button.
                logger.info(f"Started drag at ({abs_x}, {abs_y})")

            # --- Handle DRAG_END action ---
            elif action['type'] == 'drag_end':
                abs_x = action['coordinates']['x']
                abs_y = action['coordinates']['y']
                self.human_mouse_move(abs_x, abs_y)
                pyautogui.mouseUp() # Release the mouse button.
                logger.info(f"Ended drag at ({abs_x}, {abs_y})")

            # --- Handle DRAG_DROP action ---
            elif action['type'] == 'drag_drop':
                start_x, start_y = action['from']['x'], action['from']['y']
                end_x, end_y = action['to']['x'], action['to']['y']
                self.human_mouse_move(start_x, start_y)
                pyautogui.mouseDown()
                self.human_mouse_move(end_x, end_y)
                pyautogui.mouseUp()
                logger.info(f"Performed drag_drop from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            
            # After a click action, add a very short random delay.
            if action['type'] == 'click':
                self.random_delay(0.1, 0.3)
                
        except Exception as e:
            logger.error(f"Failed to execute action {idx}: {str(e)}")
            raise # Re-raise the exception to be handled by the caller.

    def close(self):
        """
        Placeholder for closing the bot. Since no browser is opened, this does nothing.
        """
        logger.info("Shutting down (no browser to close)")

# --- Sequence Recorder Class ---

# DEPRECATED: This class is marked as deprecated.
class SequenceRecorder(SeleniumBot):
    """
    Records user mouse and keyboard actions and saves them to a JSON file.
    It operates on the entire desktop, not just a specific browser window.
    """
    def __init__(self, output_file, initial_sequence=None):
        """
        Initializes the recorder.

        Args:
            output_file (str): The path to the JSON file where the recording will be saved.
            initial_sequence (str or list, optional): A sequence or chain to play before recording starts.
        """
        super().__init__()
        self.output_file = output_file
        self.initial_sequence = initial_sequence
        self.actions = []                     # A list to store recorded actions.
        self.recording = True                 # A flag to control the recording loop.
        self.desktop_mode = True              # Always in desktop mode for this version.
        self.last_event_time = time.time()    # Timestamp of the last recorded event.
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8] # Unique ID for the session.
        self.last_scroll_time = time.time()   # Timestamp of the last scroll event.
        self.scroll_threshold = 0.1           # Minimum time between recorded scroll events to avoid flooding.
        logger.info(f"Starting desktop recording session: {self.session_id}")

    def play_initial_sequence(self):
        """
        Plays a pre-defined sequence of actions before starting the recording.
        Useful for setting up an initial state (e.g., logging into an application).
        """
        if not self.initial_sequence:
            return
        try:
            # If the initial sequence is a list, it's a chain of files.
            if isinstance(self.initial_sequence, list):
                chain_player = MultiSequencePlayer(chain_config=self.initial_sequence)
                chain_player.play_chain()
            # Otherwise, it's a single sequence file.
            else:
                player = SequencePlayer(sequence_file=self.initial_sequence)
                player.play_sequence()
            logger.info("Initial sequence playback completed")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to play initial sequence: {str(e)}")

    def start_recording(self):
        """
        Starts the keyboard and mouse listeners and begins the recording process.
        The recording stops when the 'Esc' key is pressed.
        """
        logger.info("Starting desktop recording...")
        if self.initial_sequence:
            logger.info("Playing initial sequence...")
            self.play_initial_sequence()
        logger.info("Recording started! F8=toggle mode, Esc=stop")
        
        # Set up listeners from the pynput library.
        mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)
        keyboard_listener = keyboard.Listener(on_release=self.on_key_release)
        mouse_listener.start()
        keyboard_listener.start()
        
        try:
            # Keep the main thread alive while the listeners run in the background.
            while self.recording:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.warning("Recording interrupted by user")
        finally:
            # Stop the listeners and save the recorded actions to a file.
            keyboard_listener.stop()
            mouse_listener.stop()
            self.save_recording()
            logger.info(f"Recording saved to {self.output_file}")

    def on_click(self, x, y, button, pressed):
        """
        Callback function that is executed whenever a mouse click occurs.

        Args:
            x (int): The x-coordinate of the click.
            y (int): The y-coordinate of the click.
            button: The mouse button that was clicked.
            pressed (bool): True if the button was pressed, False if released.
        """
        # We only care about the moment the button is pressed.
        if not pressed or not self.recording:
            return
        current_time = time.time()
        time_since_last = current_time - self.last_event_time
        self.last_event_time = current_time
        
        # Create a dictionary for the click action.
        action = {
            'type': 'click',
            'coordinates': {'x': x, 'y': y},
            'timestamp': current_time,
            'delay_before': time_since_last # Time elapsed since the previous action.
        }
        self.actions.append(action)
        logger.info(f"Recorded desktop click at ({x}, {y})")

    def on_key_release(self, key):
        """
        Callback function that is executed whenever a keyboard key is released.

        Args:
            key: The key that was released.
        """
        if not self.recording:
            return False # Stop the listener callback chain.
            
        current_time = time.time()
        time_since_last = current_time - self.last_event_time
        self.last_event_time = current_time

        # Handle special hotkeys.
        if key == keyboard.Key.f8: # F8 toggles mode (deprecated).
            self.desktop_mode = not self.desktop_mode
            mode = "DESKTOP" if self.desktop_mode else "BROWSER (N/A)"
            logger.info(f"Switched to {mode} mode")
            return
        if key == keyboard.Key.esc: # Esc stops the recording.
            self.recording = False
            return False # Stop the listener.

        key_data = {'timestamp': current_time, 'delay_before': time_since_last}
        # Check if the key is a printable character.
        if hasattr(key, 'char') and key.char:
            key_data['type'] = 'type_string'
            key_data['text'] = key.char
            self.actions.append(key_data)
            logger.info(f"Recorded key: {key.char}")
        # Otherwise, it's a special key (like Enter, Shift, etc.).
        else:
            key_data['type'] = 'keystroke'
            key_data['key'] = str(key)
            self.actions.append(key_data)
            logger.info(f"Recorded special key: {key}")

    def on_scroll(self, x, y, dx, dy):
        """
        Callback function that is executed whenever the mouse wheel is scrolled.

        Args:
            x (int): The x-coordinate of the mouse pointer.
            y (int): The y-coordinate of the mouse pointer.
            dx (int): The horizontal scroll amount.
            dy (int): The vertical scroll amount.
        """
        if not self.recording:
            return
        current_time = time.time()
        # Throttle scroll events to avoid recording too many in a short time.
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
        """
        Saves the recorded actions and metadata to a JSON file.
        """
        # Create metadata for the recording.
        metadata = {
            "session_id": self.session_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "actions_count": len(self.actions),
            "duration": time.time() - self.last_event_time, # Approximate duration.
            "config": {"mode": "desktop_only"}
        }
        # Combine metadata and actions into a single dictionary.
        recording = {
            "metadata": metadata,
            "actions": self.actions
        }
        # Write the data to the output file in a human-readable format.
        with open(self.output_file, 'w') as f:
            json.dump(recording, f, indent=2)

# --- Sequence Player Class ---

class SequencePlayer(SeleniumBot):
    """
    Plays back a sequence of recorded desktop actions from a JSON file.
    """
    def __init__(self, sequence_file):
        """
        Initializes the player.

        Args:
            sequence_file (str): The path to the JSON file containing the actions.
        """
        super().__init__()
        self.sequence_data = self.load_sequence(sequence_file)
        self.running = True
        self.loop_counter = 0
        logger.info(f"Loaded sequence for playback: {sequence_file}")

    def load_sequence(self, filename):
        """
        Loads and validates the action sequence from a JSON file.

        Args:
            filename (str): The path to the JSON file.
        
        Returns:
            dict: The parsed JSON data.
        """
        with open(filename, 'r') as f:
            data = json.load(f)
        if "actions" not in data:
            raise ValueError("Invalid sequence format: Missing actions")
        logger.info(f"Sequence contains {len(data['actions'])} actions")
        return data

    def play_sequence(self):
        """
        Iterates through the loaded sequence and executes each action.
        """
        logger.info("Starting desktop playback")
        time.sleep(2) # Give the user time to switch to the target window.
        self.last_action_time = time.time()
        # Loop through each action in the sequence.
        for idx, action in enumerate(self.sequence_data['actions']):
            try:
                # Use the execute_with_timing method from the base class.
                self.execute_with_timing(idx, action)
            except Exception as e:
                logger.error(f"Action {idx} failed: {str(e)}")
                break # Stop playback on failure.
        logger.info("Playback completed")

# --- Multi-Sequence Player Class ---

class MultiSequencePlayer(SequencePlayer):
    """
    Plays multiple sequences back-to-back, as defined in a chain configuration file.
    This allows for looping and chaining different automation tasks.
    """
    def __init__(self, chain_config):
        """
        Initializes the multi-sequence player.

        Args:
            chain_config (list): A list of dictionaries, where each dictionary
                                 defines a sequence file to play, the number of loops,
                                 and any extra delay.
        """
        SeleniumBot.__init__(self) # Directly initialize the base class.
        self.chain_config = chain_config
        logger.info(f"Loaded chain with {len(chain_config)} sequences")

    def play_chain(self):
        """
        Executes the entire chain of sequences.
        """
        logger.info("Starting chain playback")
        time.sleep(2) # Initial delay.
        # Iterate through each item in the chain configuration.
        for item in self.chain_config:
            seq_file = item['sequence_file']
            loops = item['loop_count']
            extra_delay = item.get('extra_delay', 1) # Delay between loops.
            try:
                # Load the sequence data for the current item.
                with open(seq_file, 'r') as f:
                    sequence_data = json.load(f)
                logger.info(f"Playing {seq_file} for {loops} loops")
            except Exception as e:
                logger.error(f"Failed to load {seq_file}: {str(e)}")
                continue # Skip to the next item in the chain if loading fails.
            
            # Play the loaded sequence for the specified number of loops.
            for i in range(loops):
                logger.info(f"Loop {i+1}/{loops}")
                self.sequence_data = sequence_data # Set the current sequence for the player.
                self.play_sequence() # Call the inherited play_sequence method.
                time.sleep(max(1, extra_delay)) # Wait before the next loop or sequence.
        logger.info("Chain playback completed")


# --- Main Execution Block ---

if __name__ == "__main__":
    """
    This is the entry point of the script when run from the command line.
    It parses command-line arguments to determine whether to record, play a single
    sequence, or play a chain of sequences.
    
    Usage:
        python player.py record <output_file.json>
        python player.py play <input_file.json>
        python player.py chain <chain_config.json>
    """
    # Check for the minimum number of arguments.
    if len(sys.argv) < 2:
        print("Usage: python script.py <mode> <file>")
        print("Modes: record, play, chain")
        sys.exit(1)
        
    mode = sys.argv[1] # The mode of operation (e.g., 'record').
    file = sys.argv[2] if len(sys.argv) > 2 else None # The associated file path.
    
    try:
        # --- RECORD MODE ---
        if mode == "record":
            if not file:
                print("Output file required for recording")
                sys.exit(1)
            recorder = SequenceRecorder(output_file=file)
            recorder.start_recording()
            
        # --- PLAY MODE ---
        elif mode == "play":
            if not file:
                print("Sequence file required for playback")
                sys.exit(1)
            player = SequencePlayer(sequence_file=file)
            player.play_sequence()
            
        # --- CHAIN MODE ---
        elif mode == "chain":
            if not file:
                print("Chain config file required")
                sys.exit(1)
            with open(file) as f:
                chain_config = json.load(f)
            player = MultiSequencePlayer(chain_config=chain_config)
            player.play_chain()
            
        # --- INVALID MODE ---
        else:
            print(f"Invalid mode: {mode}")
            sys.exit(1)
            
    except Exception as e:
        # Log any fatal error that occurs during execution.
        logger.exception("Fatal error during execution")
        sys.exit(1)
        
    finally:
        # This block runs whether an error occurred or not.
        pass # No cleanup needed as no browser is opened.
