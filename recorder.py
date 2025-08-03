# recorder.py
from pynput import mouse, keyboard
import time
import json

class ElementRecorder:
    def __init__(self):
        self.recorded_actions = []
        self.current_string = ""
        self.start_time = time.time()
        self.modifiers = {'ctrl': False, 'shift': False, 'alt': False}
        self.drag_start = None
        self.pressed_button = None  # Track which button was pressed

        # Enhanced scroll tracking
        self._current_scroll_burst = None
        self.SCROLL_TIMEOUT = 0.3   # Max time between scrolls to stay in burst (seconds)
        self.SCROLL_EPSILON = 5     # Ignore very small scroll movements (pixels)
        self.last_scroll_position = 0  # Cumulative scroll position in pixels

        print("Desktop recorder started. Drag, copy, paste now reliable.")

    def flush_current_string(self):
        if self.current_string:
            action = {
                'type': 'type_string',
                'text': self.current_string,
                'timestamp': time.time()
            }
            self.recorded_actions.append(action)
            print(f"🔤 Typed: '{self.current_string}'")
            self.current_string = ""

    def record_click(self, x, y, button='left'):
        self.flush_current_string()
        action = {
            'type': 'click',
            'button': button,
            'coordinates': {'x': x, 'y': y},
            'timestamp': time.time()
        }
        self.recorded_actions.append(action)
        print(f"\n🖱 Click at ({x}, {y})")

    def record_scroll(self, x, y, dx, dy):
        now = time.time()
        pixel_delta = int(dy * 50)  # Standard: ~50px per mouse wheel notch

        # Optional: filter out negligible scrolls
        if abs(pixel_delta) < self.SCROLL_EPSILON:
            return

        # Check if we should continue current burst or finalize it
        if (self._current_scroll_burst is not None and
            now - self._current_scroll_burst['last_time'] <= self.SCROLL_TIMEOUT and
            ((pixel_delta > 0) == (self._current_scroll_burst['total_delta'] > 0))):  # Same direction
            # Extend current burst
            self._current_scroll_burst['total_delta'] += pixel_delta
            self._current_scroll_burst['end'] = {'x': x, 'y': y}
            self._current_scroll_burst['last_time'] = now
            self._current_scroll_burst['steps'] += 1
            # Update cumulative scroll position
            self.last_scroll_position += pixel_delta
            self._current_scroll_burst['final_position'] = round(self.last_scroll_position)

        else:
            # Finalize previous burst if exists
            self._finalize_scroll_burst()

            # Start new burst
            self.last_scroll_position += pixel_delta
            self._current_scroll_burst = {
                'type': 'scroll',
                'total_delta': pixel_delta,
                'start': {'x': x, 'y': y},
                'end': {'x': x, 'y': y},
                'start_time': now,
                'last_time': now,
                'final_position': round(self.last_scroll_position),
                'steps': 1
            }

    def _finalize_scroll_burst(self):
        """Finalize and save the current scroll burst as one action."""
        if self._current_scroll_burst is None:
            return

        burst = self._current_scroll_burst
        start_pos = burst['final_position'] - burst['total_delta']

        action = {
            'type': 'scroll',
            'total_delta': burst['total_delta'],
            'direction': 'up' if burst['total_delta'] > 0 else 'down',
            'start': burst['start'],
            'end': burst['end'],
            'start_position': round(start_pos),
            'final_position': burst['final_position'],
            'duration_sec': burst['last_time'] - burst['start_time'],
            'steps': burst['steps'],
            'timestamp': burst['start_time']
        }

        self.recorded_actions.append(action)
        print(f"\n🡅 SCROLLED {action['direction'].upper()}: {action['total_delta']}px "
              f"→ pos={action['final_position']} "
              f"[{action['steps']} notches, {action['duration_sec']:.2f}s]")

        self._current_scroll_burst = None

    def on_mouse_press(self, x, y, button, pressed):
        if pressed and self.pressed_button is None:  # Only start if no other button down
            self.pressed_button = button
            if button == mouse.Button.left:
                self.drag_start = {'x': x, 'y': y}
                print(f"📍 Drag start set at ({x}, {y})")

    def on_mouse_release(self, x, y, button):
        if button == self.pressed_button:
            if button == mouse.Button.left and self.drag_start is not None:
                dx = x - self.drag_start['x']
                dy = y - self.drag_start['y']
                distance = (dx ** 2 + dy ** 2) ** 0.5

                # 🔍 Only drag if moved more than 10 pixels
                if distance > 10:
                    action = {
                        'type': 'drag_drop',
                        'from': self.drag_start,
                        'to': {'x': x, 'y': y},
                        'timestamp': time.time()
                    }
                    self.recorded_actions.append(action)
                    print(f"\n✅ DRAGGED from {self.drag_start} to ({x}, {y}) [dist={distance:.1f}]")
                else:
                    self.record_click(x, y, 'left')

                self.drag_start = None

            elif button != mouse.Button.left:
                # Handle right/middle clicks as simple clicks
                self.record_click(x, y, str(button))

            self.pressed_button = None  # Always reset

    def handle_keypress(self, key):
        try:
            # --- Get char and vk safely ---
            key_char = None
            key_vk = None

            if hasattr(key, 'char') and key.char is not None:
                key_char = key.char.lower()
            elif hasattr(key, 'vk'):
                key_vk = key.vk

            # --- Handle modifier keys ---
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.modifiers['ctrl'] = True
                return
            elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                self.modifiers['shift'] = True
                return
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.modifiers['alt'] = True
                return

            # --- Handle Ctrl+X, Ctrl+C, Ctrl+V, Ctrl+A ---
            if self.modifiers['ctrl']:
                detected_key = None

                # Check for ASCII control characters first (most reliable)
                if hasattr(key, 'char') and key.char is not None:
                    ctrl_code = ord(key.char)
                    if ctrl_code == 3:    # Ctrl+C = ASCII 3 (ETX)
                        detected_key = 'c'
                    elif ctrl_code == 24: # Ctrl+X = ASCII 24 (CAN)
                        detected_key = 'x'
                    elif ctrl_code == 22: # Ctrl+V = ASCII 22 (SYN)
                        detected_key = 'v'
                    elif ctrl_code == 1:  # Ctrl+A = ASCII 1 (SOH)
                        detected_key = 'a'

                # Fallback to virtual key codes
                elif key_vk is not None:
                    if key_vk == 67:   # VK_C
                        detected_key = 'c'
                    elif key_vk == 88: # VK_X
                        detected_key = 'x'
                    elif key_vk == 86: # VK_V
                        detected_key = 'v'
                    elif key_vk == 65: # VK_A
                        detected_key = 'a'

                if detected_key:
                    self.flush_current_string()

                    action = {
                        'type': 'clipboard',
                        'operation': detected_key,
                        'timestamp': time.time()
                    }

                    self.recorded_actions.append(action)

                    if detected_key == 'c':
                        print("\n📋 COPY (Ctrl+C)")
                    elif detected_key == 'v':
                        print("\n📎 PASTE (Ctrl+V)")
                    elif detected_key == 'x':
                        print("\n✂️ CUT (Ctrl+X)")
                    elif detected_key == 'a':
                        print("\n🅰 SELECT ALL (Ctrl+A)")

                    return

            # --- Regular typing: only printable characters ---
            if hasattr(key, 'char') and key.char is not None:
                char_ord = ord(key.char)
                if char_ord < 32 or char_ord == 127:  # Control characters
                    self.flush_current_string()
                    action = {
                        'type': 'keystroke',
                        'key': str(key).replace('Key.', ''),
                        'timestamp': time.time()
                    }
                    self.recorded_actions.append(action)
                    print(f"⌨ Control Key: {action['key']}")
                    return

                # Safe printable character
                self.current_string += key.char
            else:
                self.flush_current_string()
                key_name = str(key).replace('Key.', '')
                action = {
                    'type': 'keystroke',
                    'key': key_name,
                    'timestamp': time.time()
                }
                self.recorded_actions.append(action)
                print(f"⌨ Key: {key_name}")

        except Exception as e:
            print(f"Error in handle_keypress: {e}")

    def handle_keyrelease(self, key):
        """Reset modifier keys on release"""
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.modifiers['ctrl'] = False
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.modifiers['shift'] = False
        elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
            self.modifiers['alt'] = False

    def save_sequence(self):
        """Save all recorded actions to JSON"""
        self.flush_current_string()
        self._finalize_scroll_burst()  # Finalize any ongoing scroll

        output = {
            'metadata': {
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_actions': len(self.recorded_actions),
                'duration_sec': round(time.time() - self.start_time, 2),
                'mode': 'desktop_only'
            },
            'actions': self.recorded_actions
        }
        with open('sequence.json', 'w') as f:
            json.dump(output, f, indent=4)
        print(f"\n✅ Saved to sequence.json | {len(self.recorded_actions)} actions")


# === Initialize ===
recorder = ElementRecorder()

# Callbacks for listeners
def on_click(x, y, button, pressed):
    if pressed:
        recorder.on_mouse_press(x, y, button, pressed)
    else:
        recorder.on_mouse_release(x, y, button)

def on_scroll(x, y, dx, dy):
    recorder.record_scroll(x, y, dx, dy)

def on_press(key):
    if key == keyboard.Key.esc:
        recorder.save_sequence()
        return False  # Stop listener
    recorder.handle_keypress(key)

def on_release(key):
    recorder.handle_keyrelease(key)

# Start listeners
print("\n🟢 Recording. Try dragging now!")
print("🖱 Drag >10px to trigger drag, else click")
print("🡅 Scroll actions are grouped for accurate replay")
print("📋 Ctrl+C/V/X/A work reliably")
print("⏹ ESC to save and exit")

mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

mouse_listener.start()
keyboard_listener.start()
keyboard_listener.join()  # Will block until ESC
mouse_listener.stop()