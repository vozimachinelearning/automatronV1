<<<<<<< HEAD
# automatronV1
General automation tool for repetitive processes, let's you to teach how to do things to your pc, and exports a json with the steps, has a custom playback interpreter that serves as the interface for llms to build their own MCP easily.
=======
# Automatron

Automatron is a user-friendly automation tool designed to record and replay browser and desktop actions. It features a modern graphical interface and supports advanced automation scenarios, making it ideal for repetitive web tasks, testing, and workflow automation.

## Main Features

- **Graphical User Interface (GUI):**
  - Intuitive, tabbed interface for recording, playing, and chaining automation sequences.
  - Status bar with real-time feedback and animated progress indicator.

- **Action Recording:**
  - Record your interactions (mouse clicks, typing, scrolling, etc.) in the browser or desktop.
  - Save recorded actions as reusable sequences in JSON format.
  - Optionally start a new recording from an existing sequence or chain.

- **Playback Automation:**
  - Replay recorded sequences as many times as needed.
  - Set custom loop counts and delays between repetitions.
  - Supports human-like mouse and keyboard simulation for realistic automation.

- **Chain Automation:**
  - Combine multiple sequences into a chain for complex workflows.
  - Configure each step with its own file, loop count, and delay.
  - Play the entire chain with a single click.

- **File Management:**
  - Browse and select sequence files easily from the interface.
  - Organize your automation files in the provided `sequences/` folder.

- **Logging and Feedback:**
  - Automation progress and errors are displayed in the status bar and logged to `automation.log`.

## How to Use

### 1. Recording a Sequence
- Go to the **Record** tab.
- Enter a name for your new sequence.
- (Optional) Select an initial sequence or chain file to start from.
- Click **Start** to begin recording. Perform your actions in the browser window that opens.
- When finished, the sequence is saved in the `sequences/` folder.

### 2. Playing a Sequence
- Go to the **Play** tab.
- Select a sequence file (JSON) to play.
- Set the number of loops and delay between repetitions.
- Click **Start** to replay the actions automatically.

### 3. Creating and Playing a Chain
- Go to the **Chain** tab.
- Add one or more sequence files, specifying loop count and delay for each.
- Remove sequences as needed.
- Click **Start** to play the entire chain in order.

### 4. Status and Feedback
- The status bar at the bottom shows progress, errors, and completion messages.
- All activity is also logged in `automation.log` for review.

## Requirements
- Linux operating system
- Google Chrome (prepackaged installer included)
- Python 3.12+
- All required Python packages are listed in `requirements.txt`

## Typical Use Cases
- Automating repetitive web tasks
- Testing web applications
- Creating complex, multi-step workflows
- Demonstrating or reproducing user interactions

## Getting Help
- If you encounter issues, check the `automation.log` file for details.
- For questions or suggestions, contact the project maintainer.

---
Automatron makes automation accessible and flexible for everyone. Enjoy automating your workflows!
>>>>>>> 29a3696 (Initial commit of my script)
