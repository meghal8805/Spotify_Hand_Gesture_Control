# Spotify Hand Gesture Control

A real-time, cross-platform computer vision application that lets you control Spotify playback and system volume hands-free using webcam hand gestures.

## Features

* **Real-Time Hand Tracking:** Uses Google's MediaPipe Hand Landmarker (`VIDEO` mode) to detect 21 3D hand landmarks at high frame rates.
* **Cross-Platform OS Automation:** Automatically detects your operating system and maps gestures to native media controls:
  * **Windows:** `pyautogui` media keys and `taskkill`
  * **macOS:** Native `AppleScript` (`osascript`) commands
  * **Linux:** `playerctl` and `pactl` audio controls
* **False-Trigger Prevention:** Includes a frame-stability buffer (`4` consecutive frames) and a `2.0s` cooldown timer to prevent accidental triggers while moving your hand.
* **Asynchronous Execution:** Dispatches OS media commands on background daemon threads so the OpenCV video feed never freezes or lags.
* **Auto-Model Setup:** Automatically downloads the required `hand_landmarker.task` model on first run if not present locally.

## Gesture Controls

| Gesture | Action |
| :--- | :--- |
| **Thumbs Up** | Play / Pause |
| **Peace / Victory** | Next Track |
| **Pointer (Index Up)** | Previous Track |
| **Open Palm** | Volume Up (+10%) |
| **Fist** | Volume Down (-10%) |
| **Middle Finger** | Close Spotify |

## Tech Stack

* **Python 3.10+**
* **OpenCV (`opencv-python`)** — Video capture, frame mirroring, and HUD rendering
* **MediaPipe (`mediapipe`)** — Hand landmark detection and tracking
* **PyAutoGUI (`pyautogui`)** — Windows media key simulation

## Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/spotify-hand-gesture-control.git
   cd spotify-hand-gesture-control
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Linux users should also ensure `playerctl` is installed via their package manager.)*

3. **Run the application:**
   Open the Spotify desktop app, start playing a track, and run:
   ```bash
   python spotify_gesture_control.py
   ```
   Press **`Q`** to quit the webcam window.