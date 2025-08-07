import customtkinter as ctk
import threading
from tkinter import filedialog, messagebox, simpledialog
import os
import time
import queue
import random
import json
# Import pynput at the top, as it's needed for the recorder's listeners
from pynput import keyboard, mouse
from player import SequencePlayer
from recorder import ElementRecorder
   

# Set color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Custom colors
RED_PRIMARY = "#C73E1D"
RED_DARK = "#8C2B1E"
DARK_GREY = "#1A1A1A"
MEDIUM_GREY = "#2A2A2A"
LIGHT_GREY = "#3A3A3A"
TEXT_COLOR = "#F0F0F0"

# Animation settings
ANIMATION_SPEED = 0.05
loading_active = False
update_queue = queue.Queue()

def update_status(text):
    update_queue.put(text)

def animate_loading():
    wave_chars = "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁"
    vibration_offset = 0
    direction = 1
    frame = 0
    while loading_active:
        status_label.update_idletasks()
        bar_width = status_label.winfo_width()
        char_count = max(10, bar_width // 8)
        wave_pattern = (wave_chars * (char_count // len(wave_chars) + 1))[:char_count]
        wave_shift = frame % len(wave_chars)
        shifted_wave = wave_pattern[wave_shift:] + wave_pattern[:wave_shift]
        vibrated_wave = shifted_wave[vibration_offset:] + shifted_wave[:vibration_offset]
        app.after(0, lambda t=f"{vibrated_wave}": status_label.configure(text=t))
        frame += 1
        vibration_offset = (vibration_offset + direction) % len(wave_pattern)
        if random.random() < 0.1: direction = -direction
        time.sleep(ANIMATION_SPEED)

def check_queue():
    try:
        while True:
            msg = update_queue.get_nowait()
            status_label.configure(text=msg)
    except queue.Empty:
        pass
    app.after(50, check_queue)

def browse_initial_file(entry_widget):
    """Browse for initial sequence/chain file"""
    file_path = filedialog.askopenfilename(
        title="Select Initial Sequence/Chain File", 
        filetypes=[("JSON Files", "*.json")]
    )
    if file_path:
        entry_widget.delete(0, ctk.END)
        entry_widget.insert(0, file_path)

def start_recording(sequence_name):
    def record_thread():
        # Declare global at the very beginning of the function
        global loading_active
        
        directory = os.path.join(os.getcwd(), "sequences")
        os.makedirs(directory, exist_ok=True)
        # Construct the correct output path
        output_file = os.path.join(directory, f"{sequence_name}.json")
        
        # Get initial sequence if specified (Optional: Add logic to play it)
        initial_file = initial_sequence_entry.get().strip()
        # (Optional) You could add code here to use SequencePlayer from player.py to play the initial sequence

        

        try:
            update_status("Recording... (Press ESC to stop)")
            # Create an instance of the NEW recorder
            recorder = ElementRecorder()
            
            # === Define the callback functions used by the new recorder ===
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
            # === End of callback definitions ===
            
            # Start the listeners (this will block until ESC is pressed)
            mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
            keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

            mouse_listener.start()
            keyboard_listener.start()
            keyboard_listener.join()  # Blocks here until ESC
            mouse_listener.stop()

            # The recorder saves to 'sequence.json'. Move it to the correct location.
            temp_file = 'sequence.json'
            if os.path.exists(temp_file):
                # Read the data to update the metadata
                with open(temp_file, 'r') as f:
                    data = json.load(f)
                # Update the metadata to reflect the sequence name
                data['metadata']['sequence_name'] = sequence_name
                # Save to the correct sequences folder
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=4)
                # Clean up the temporary file
                os.remove(temp_file)
                update_status(f"Recording saved as {sequence_name}.json")
            else:
                update_status("Recording failed")
                messagebox.showerror("Recording Error", "Recording file was not created.")
                
        except Exception as e:
            update_status("Error occurred")
            messagebox.showerror("Recording Error", str(e))
        finally:
            # The 'global' declaration at the top handles this
            loading_active = False
            update_queue.put("Ready")
    
    # Start the recording thread
    threading.Thread(target=record_thread, daemon=True).start()

def start_playback(sequence_file, loop_count, extra_delay):
    # Import the player from player.py
    

    def play_thread():
        player = SequencePlayer(sequence_file=sequence_file)
        try:
            update_status("Playing sequence...")
            for _ in range(loop_count):
                player.play_sequence()
                time.sleep(extra_delay)
            update_status("Playback completed")
        except Exception as e:
            update_status("Error occurred")
            messagebox.showerror("Playback Error", str(e))
        finally:
            global loading_active
            loading_active = False
            update_queue.put("Ready")
    threading.Thread(target=play_thread, daemon=True).start()

def start_chain_playback(chain_config):
    # Import the player from player.py
    try:
        from player import MultiSequencePlayer
    except ImportError:
        messagebox.showerror("Import Error", "Could not import MultiSequencePlayer from player.py.")
        return

    def chain_thread():
        player = MultiSequencePlayer(chain_config=chain_config)
        try:
            update_status("Playing chain...")
            player.play_chain()
            update_status("Chain completed")
        except Exception as e:
            update_status("Error occurred")
            messagebox.showerror("Chain Playback Error", str(e))
        finally:
            global loading_active
            loading_active = False
            update_queue.put("Ready")
    threading.Thread(target=chain_thread, daemon=True).start()

# Rest of the GUI code (chain_config, update_chain_display, add_sequence, etc.) remains the same...
chain_config = []

def update_chain_display():
    chain_display.configure(state="normal")
    chain_display.delete("0.0", ctk.END)
    for idx, item in enumerate(chain_config):
        chain_display.insert(ctk.END, f"{idx+1}. File: {item['sequence_file']}, Loops: {item['loop_count']}, Delay: {item['extra_delay']} sec\n")
    # Keep the textbox editable for manual editing

def parse_chain_from_text():
    """Parse the chain configuration from the editable text box"""
    global chain_config
    try:
        text_content = chain_display.get("0.0", ctk.END).strip()
        if not text_content:
            chain_config = []
            return
        
        lines = text_content.split('\n')
        new_chain_config = []
        
        for line in lines:
            line = line.strip()
            if not line or not line.startswith(tuple('123456789')):
                continue
                
            # Parse format: "1. File: path, Loops: X, Delay: Y sec"
            try:
                # Extract file path
                file_start = line.find('File: ') + 6
                file_end = line.find(', Loops:')
                sequence_file = line[file_start:file_end].strip()
                
                # Extract loops
                loops_start = line.find('Loops: ') + 7
                loops_end = line.find(', Delay:')
                loop_count = int(line[loops_start:loops_end].strip())
                
                # Extract delay
                delay_start = line.find('Delay: ') + 7
                delay_end = line.find(' sec')
                extra_delay = float(line[delay_start:delay_end].strip())
                
                new_chain_config.append({
                    'sequence_file': sequence_file,
                    'loop_count': loop_count,
                    'extra_delay': extra_delay
                })
            except (ValueError, IndexError):
                # Skip malformed lines
                continue
                
        chain_config = new_chain_config
    except Exception as e:
        messagebox.showerror("Parse Error", f"Error parsing chain configuration: {str(e)}")

def export_chain_to_batch():
    """Export the current chain configuration to a batch script"""
    if not chain_config:
        messagebox.showwarning("Export Error", "No chain configuration to export")
        return
        
    # Parse any manual edits first
    parse_chain_from_text()
    
    if not chain_config:
        messagebox.showwarning("Export Error", "No valid chain configuration found")
        return
    
    file_path = filedialog.asksaveasfilename(
        title="Save Chain as Batch Script",
        defaultextension=".bat",
        filetypes=[("Batch Files", "*.bat"), ("All Files", "*.*")]
    )
    
    if not file_path:
        return
        
    try:
        with open(file_path, 'w') as f:
            f.write("@echo off\n")
            f.write("setlocal enabledelayedexpansion\n")
            f.write("echo Starting automation chain...\n")
            f.write("\n")
            
            # Get the directory where the main.py is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            player_path = os.path.join(script_dir, "player.py")
            venv_path = os.path.join(script_dir, "venv", "Scripts", "activate.bat")
            
            # Activate virtual environment
            f.write(f"echo Activating virtual environment...\n")
            f.write(f"call \"{venv_path}\"\n")
            f.write("if %errorlevel% neq 0 (\n")
            f.write("    echo Failed to activate virtual environment\n")
            f.write("    pause\n")
            f.write("    exit /b 1\n")
            f.write(")\n")
            f.write("\n")

            for idx, item in enumerate(chain_config, 1):
                 f.write(f"echo Step {idx}: Running {os.path.basename(item['sequence_file'])} ({item['loop_count']} loops, {item['extra_delay']}s delay)...\n")
                 
                 # Handle multiple loops for each sequence
                 f.write(f"for /L %%i in (1,1,{item['loop_count']}) do (\n")
                 f.write(f"    echo   Loop %%i of {item['loop_count']}\n")
                 f.write(f"    python \"{player_path}\" play \"{item['sequence_file']}\"\n")
                 f.write("    if !errorlevel! neq 0 (\n")
                 f.write(f"        echo Error in step {idx}, loop %%i, stopping chain\n")
                 f.write("        pause\n")
                 f.write("        exit /b 1\n")
                 f.write("    )\n")
                 
                 # Add delay between loops (except for the last loop)
                 f.write(f"    if %%i lss {item['loop_count']} (\n")
                 f.write(f"        echo   Waiting {item['extra_delay']} seconds...\n")
                 f.write(f"        timeout /t {int(item['extra_delay'])} /nobreak >nul\n")
                 f.write("    )\n")
                 f.write(")\n")
                 f.write("\n")
            
            f.write("echo Chain completed successfully!\n")
            f.write("pause\n")
        
        messagebox.showinfo("Export Success", f"Chain exported to: {file_path}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export chain: {str(e)}")

def add_sequence():
    file_path = filedialog.askopenfilename(title="Select Sequence File", filetypes=[("JSON Files", "*.json")])
    if not file_path: return
    try:
        loop_count = simpledialog.askinteger("Loop Count", "Enter loop count:", minvalue=1, initialvalue=1)
        extra_delay = simpledialog.askfloat("Extra Delay", "Enter extra delay (sec):", minvalue=0, initialvalue=1.0)
    except Exception:
        messagebox.showwarning("Input Error", "Invalid input")
        return
    chain_config.append({
        'sequence_file': file_path,
        'loop_count': loop_count,
        'extra_delay': extra_delay
    })
    update_chain_display()

def remove_sequence():
    if chain_config:
        chain_config.pop()
        update_chain_display()
    else:
        messagebox.showinfo("Remove", "No sequence to remove")

def on_record():
    """Callback for start recording button"""
    name = sequence_name_entry.get().strip()
    if not name:
        messagebox.showwarning("Input Error", "Please enter a name.")
        return
    global loading_active
    loading_active = True
    threading.Thread(target=animate_loading, daemon=True).start()
    start_recording(name)

def on_play():
    """Callback for start playback button"""
    sequence_file = sequence_file_entry.get().strip()
    if not os.path.isfile(sequence_file):
        messagebox.showwarning("Input Error", "Select a valid file.")
        return
    try:
        loop_count = int(loop_count_entry.get().strip())
        extra_delay = float(extra_delay_entry.get().strip())
    except ValueError:
        messagebox.showwarning("Input Error", "Invalid numbers.")
        return
    global loading_active
    loading_active = True
    threading.Thread(target=animate_loading, daemon=True).start()
    start_playback(sequence_file, loop_count, extra_delay)

def on_chain_play():
    """Callback for start chain button"""
    # Parse any manual edits first
    parse_chain_from_text()
    
    if not chain_config:
        messagebox.showwarning("Input Error", "Add sequences first.")
        return
    global loading_active
    loading_active = True
    threading.Thread(target=animate_loading, daemon=True).start()
    start_chain_playback(chain_config)

def browse_file():
    """Callback for file browse button"""
    file_path = filedialog.askopenfilename(title="Select Sequence File", filetypes=[("JSON Files", "*.json")])
    if file_path:
        sequence_file_entry.delete(0, ctk.END)
        sequence_file_entry.insert(0, file_path)

# --- GUI Setup ---
app = ctk.CTk()
app.title("Automatron UI")
app.configure(fg_color=DARK_GREY)

# Main tabview
tab_view = ctk.CTkTabview(app, width=400, height=120, fg_color=MEDIUM_GREY, 
                         border_color=RED_DARK, segmented_button_selected_color=RED_PRIMARY)
tab_view.pack(padx=5, pady=5, fill="both", expand=True)
tab_view.add("Record")
tab_view.add("Play")
tab_view.add("Chain")

# Record Tab
record_frame = tab_view.tab("Record")
record_box = ctk.CTkFrame(record_frame, fg_color="transparent")
record_box.pack(fill="x", pady=2)
name_box = ctk.CTkFrame(record_box, fg_color="transparent")
name_box.pack(fill="x", pady=2)
ctk.CTkLabel(name_box, text="Sequence Name:", text_color=TEXT_COLOR).pack(side="left", padx=5)
sequence_name_entry = ctk.CTkEntry(name_box, width=150, fg_color=LIGHT_GREY, text_color=TEXT_COLOR, 
                               placeholder_text="sequence_name")
sequence_name_entry.pack(side="left", padx=5)
initial_box = ctk.CTkFrame(record_box, fg_color="transparent")
initial_box.pack(fill="x", pady=2)
ctk.CTkLabel(initial_box, text="Initial:", text_color=TEXT_COLOR).pack(side="left", padx=5)
initial_sequence_entry = ctk.CTkEntry(initial_box, width=250, fg_color=LIGHT_GREY, text_color=TEXT_COLOR, 
                                  placeholder_text="Optional initial sequence or chain file")
initial_sequence_entry.pack(side="left", padx=5)
ctk.CTkButton(initial_box, text="...", command=lambda: browse_initial_file(initial_sequence_entry), 
              fg_color=RED_DARK, hover_color=RED_PRIMARY, width=25, height=24).pack(side="left")

# Play Tab
play_frame = tab_view.tab("Play")
file_box = ctk.CTkFrame(play_frame, fg_color="transparent")
file_box.pack(fill="x", pady=2)
ctk.CTkLabel(file_box, text="File:", text_color=TEXT_COLOR).pack(side="left", padx=5)
sequence_file_entry = ctk.CTkEntry(file_box, width=250, fg_color=LIGHT_GREY, text_color=TEXT_COLOR, 
                                 placeholder_text="sequence.json")
sequence_file_entry.pack(side="left", padx=5)
ctk.CTkButton(file_box, text="...", command=browse_file, fg_color=RED_DARK, hover_color=RED_PRIMARY, 
              width=25, height=24).pack(side="left")
params_box = ctk.CTkFrame(play_frame, fg_color="transparent")
params_box.pack(fill="x", pady=2)
ctk.CTkLabel(params_box, text="Loops:", text_color=TEXT_COLOR).pack(side="left", padx=5)
loop_count_entry = ctk.CTkEntry(params_box, width=40, fg_color=LIGHT_GREY, text_color=TEXT_COLOR)
loop_count_entry.insert(0, "1")
loop_count_entry.pack(side="left")
ctk.CTkLabel(params_box, text="Delay:", text_color=TEXT_COLOR).pack(side="left", padx=(10,5))
extra_delay_entry = ctk.CTkEntry(params_box, width=40, fg_color=LIGHT_GREY, text_color=TEXT_COLOR)
extra_delay_entry.insert(0, "1")
extra_delay_entry.pack(side="left")

# Chain Tab
chain_frame = tab_view.tab("Chain")
chain_tools = ctk.CTkFrame(chain_frame, fg_color="transparent")
chain_tools.pack(fill="x", pady=2)
ctk.CTkButton(chain_tools, text="+", command=add_sequence, fg_color=RED_DARK, hover_color=RED_PRIMARY, 
              width=25, height=24).pack(side="left", padx=5)
ctk.CTkButton(chain_tools, text="-", command=remove_sequence, fg_color=RED_DARK, hover_color=RED_PRIMARY, 
              width=25, height=24).pack(side="left", padx=2)
ctk.CTkButton(chain_tools, text="Export", command=export_chain_to_batch, fg_color=RED_DARK, hover_color=RED_PRIMARY, 
              width=60, height=24).pack(side="right", padx=5)
chain_display = ctk.CTkTextbox(chain_frame, width=390, height=60, fg_color=LIGHT_GREY, text_color=TEXT_COLOR)
chain_display.pack(pady=(2,0), fill="both", expand=True)
# Keep textbox editable for manual editing

# Status bar with start button
status_container = ctk.CTkFrame(app, fg_color=MEDIUM_GREY, height=28, corner_radius=3)
status_container.pack(fill="x", padx=5, pady=(0,5))
status_container.pack_propagate(False)
status_label = ctk.CTkLabel(status_container, text="Ready", font=("Segoe UI", 9), text_color="#A0A0B0")
status_label.pack(side="left", padx=5)
start_button = ctk.CTkButton(status_container, text="Start", command=lambda: 
                           on_record() if tab_view.get() == "Record" else
                           on_play() if tab_view.get() == "Play" else
                           on_chain_play(), 
                           fg_color=RED_PRIMARY, hover_color=RED_DARK,
                           height=24, width=60)
start_button.pack(side="right", padx=5, pady=2)

app.after(50, check_queue)
app.mainloop()