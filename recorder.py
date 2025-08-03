#recorder.py
from pynput import mouse, keyboard
import time
import json

class ElementRecorder:
    def __init__(self):
        self.recorded_actions = []
        self.current_string = ""
        self.last_scroll_time = 0
        self.scroll_threshold = 0.1
        self.last_scroll_position = 0
        self.start_time = time.time()
        self.modifiers = {'ctrl': False, 'shift': False, 'alt': False}
        self.drag_start = None
        self.pressed_button = None  # Track which button was pressed

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
        if now - self.last_scroll_time > self.scroll_threshold:
            self.last_scroll_position += dy * 50
            action = {
                'type': 'scroll',
                'delta': round(dy * 50),
                'position': round(self.last_scroll_position),
                'coordinates': {'x': x, 'y': y},
                'timestamp': now
            }
            self.recorded_actions.append(action)
            print(f"\n🡅 Scroll Δ={dy} → pos={round(self.last_scroll_position)}")
            self.last_scroll_time = now

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
                
                # ✅ Reset only after handling
                self.drag_start = None
            elif button != mouse.Button.left:
                # Handle right/middle clicks as simple clicks
                self.record_click(x, y, str(button))
            
            # ✅ Always reset pressed button
            self.pressed_button = None

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
                
                # Fallback to virtual key codes (corrected values)
                elif key_vk is not None:
                    if key_vk == 67:   # VK_C (0x43)
                        detected_key = 'c'
                    elif key_vk == 88: # VK_X (0x58)
                        detected_key = 'x'
                    elif key_vk == 86: # VK_V (0x56)
                        detected_key = 'v'
                    elif key_vk == 65: # VK_A (0x41)
                        detected_key = 'a'

                if detected_key:
                    self.flush_current_string()

                    # Use 'clipboard' type with 'operation' field to match player expectations
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
                    
                    return  # Prevent further processing

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
        print("\n✅ Saved to sequence.json")


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
print("📋 Ctrl+C/V/X/A work reliably")
print("⏹ ESC to save and exit")

mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

mouse_listener.start()
keyboard_listener.start()
keyboard_listener.join()  # Will block until ESC
mouse_listener.stop()