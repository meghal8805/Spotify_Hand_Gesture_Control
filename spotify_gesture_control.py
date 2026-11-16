import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.components.containers.landmark import NormalizedLandmark
import time
import sys
import os
import threading
import subprocess
import urllib.request

# ─────────────────────────────────────────────
# MediaPipe model — auto-downloaded if missing
# ─────────────────────────────────────────────
MODEL_PATH = "hand_landmarker.task"
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

if not os.path.exists(MODEL_PATH):
    print(f"Downloading MediaPipe hand model to '{MODEL_PATH}' ...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Download complete.")

# ─────────────────────────────────────────────
# Platform detection
# ─────────────────────────────────────────────
PLATFORM = sys.platform   # "win32" | "darwin" | "linux"

if PLATFORM == "win32":
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
    except ImportError:
        print("Install pyautogui:  pip install pyautogui")
        sys.exit(1)

# ─────────────────────────────────────────────
# OS-level Spotify control helpers
# ─────────────────────────────────────────────

def _run(cmd: str) -> str:
    """Run a shell command silently; return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── macOS ──────────────────────────────────────
def _mac(script: str) -> str:
    return _run(f"osascript -e '{script}'")

def mac_play_pause():
    _mac("tell application \"Spotify\" to playpause")
    state = _mac("tell application \"Spotify\" to player state as string")
    return "Playing" if state == "playing" else "Paused"

def mac_next():
    _mac("tell application \"Spotify\" to next track")
    time.sleep(0.35)
    name = _mac("tell application \"Spotify\" to name of current track as string")
    return f"Next: {name or '...'}"

def mac_prev():
    _mac("tell application \"Spotify\" to previous track")
    time.sleep(0.35)
    name = _mac("tell application \"Spotify\" to name of current track as string")
    return f"Prev: {name or '...'}"

def mac_vol_up():
    vol = _mac("tell application \"Spotify\" to sound volume as integer")
    new = min(100, int(vol or 50) + 10)
    _mac(f"tell application \"Spotify\" to set sound volume to {new}")
    return f"Volume: {new}%"

def mac_vol_down():
    vol = _mac("tell application \"Spotify\" to sound volume as integer")
    new = max(0, int(vol or 50) - 10)
    _mac(f"tell application \"Spotify\" to set sound volume to {new}")
    return f"Volume: {new}%"

def mac_close():
    _mac("tell application \"Spotify\" to quit")
    return "Spotify Closed"


# ── Windows ────────────────────────────────────
def win_play_pause():
    pyautogui.press("playpause")
    return "Play / Pause toggled"

def win_next():
    pyautogui.press("nexttrack")
    return "Next Track ▶▶"

def win_prev():
    pyautogui.press("prevtrack")
    return "Prev Track ◀◀"

def win_vol_up():
    # 5 presses ≈ +10% on Windows default scale
    for _ in range(5):
        pyautogui.press("volumeup")
    return "Volume Up 🔊"

def win_vol_down():
    for _ in range(5):
        pyautogui.press("volumedown")
    return "Volume Down 🔉"

def win_close():
    _run("taskkill /f /im Spotify.exe")
    return "Spotify Closed"


# ── Linux ──────────────────────────────────────
def linux_play_pause():
    _run("playerctl --player=spotify play-pause")
    status = _run("playerctl --player=spotify status")
    return "Playing" if status == "Playing" else "Paused"

def linux_next():
    _run("playerctl --player=spotify next")
    time.sleep(0.35)
    name = _run("playerctl --player=spotify metadata title")
    return f"Next: {name or '...'}"

def linux_prev():
    _run("playerctl --player=spotify previous")
    time.sleep(0.35)
    name = _run("playerctl --player=spotify metadata title")
    return f"Prev: {name or '...'}"

def linux_vol_up():
    _run("pactl set-sink-volume @DEFAULT_SINK@ +10%")
    return "Volume Up 🔊"

def linux_vol_down():
    _run("pactl set-sink-volume @DEFAULT_SINK@ -10%")
    return "Volume Down 🔉"

def linux_close():
    _run("pkill -x spotify")
    return "Spotify Closed"


# ─────────────────────────────────────────────
# Unified action map — pick by platform
# ─────────────────────────────────────────────
if PLATFORM == "darwin":
    ACTIONS_MAP = {
        "THUMBS_UP":     mac_play_pause,
        "PEACE":         mac_next,
        "POINTER":       mac_prev,
        "OPEN_PALM":     mac_vol_up,
        "FIST":          mac_vol_down,
        "MIDDLE_FINGER": mac_close,
    }
elif PLATFORM == "win32":
    ACTIONS_MAP = {
        "THUMBS_UP":     win_play_pause,
        "PEACE":         win_next,
        "POINTER":       win_prev,
        "OPEN_PALM":     win_vol_up,
        "FIST":          win_vol_down,
        "MIDDLE_FINGER": win_close,
    }
else:
    ACTIONS_MAP = {
        "THUMBS_UP":     linux_play_pause,
        "PEACE":         linux_next,
        "POINTER":       linux_prev,
        "OPEN_PALM":     linux_vol_up,
        "FIST":          linux_vol_down,
        "MIDDLE_FINGER": linux_close,
    }

# ─────────────────────────────────────────────
# Thread-safe feedback + async action dispatch
# ─────────────────────────────────────────────
_feedback_lock  = threading.Lock()
_feedback_text  = ""
_action_running = False

def _run_action(fn):
    global _action_running

    def _worker():
        global _feedback_text, _action_running
        try:
            result = fn()
        except Exception as e:
            result = f"Error: {e}"
        with _feedback_lock:
            _feedback_text  = result
            _action_running = False

    with _feedback_lock:
        if _action_running:
            return
        _action_running = True

    threading.Thread(target=_worker, daemon=True).start()

def get_feedback() -> str:
    with _feedback_lock:
        return _feedback_text

# ─────────────────────────────────────────────
# Landmark indices
# ─────────────────────────────────────────────
THUMB_TIP,  THUMB_MCP  =  4,  2
INDEX_TIP,  INDEX_MCP  =  8,  5
MIDDLE_TIP, MIDDLE_MCP = 12,  9
RING_TIP,   RING_MCP   = 16, 13
PINKY_TIP,  PINKY_MCP  = 20, 17

# ─────────────────────────────────────────────
# Gesture recognition
# ─────────────────────────────────────────────

def recognize_gesture(landmarks: list[NormalizedLandmark]) -> str:
    def finger_up(tip: int, mcp: int) -> bool:
        return landmarks[tip].y < landmarks[mcp].y

    def thumb_up_mirrored() -> bool:
        return landmarks[THUMB_TIP].x < landmarks[THUMB_MCP].x

    index_ext  = finger_up(INDEX_TIP,  INDEX_MCP)
    middle_ext = finger_up(MIDDLE_TIP, MIDDLE_MCP)
    ring_ext   = finger_up(RING_TIP,   RING_MCP)
    pinky_ext  = finger_up(PINKY_TIP,  PINKY_MCP)
    thumb_ext  = thumb_up_mirrored()

    if thumb_ext and not index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "THUMBS_UP"
    if not thumb_ext and index_ext and middle_ext and not ring_ext and not pinky_ext:
        return "PEACE"
    if not thumb_ext and index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "POINTER"
    if thumb_ext and index_ext and middle_ext and ring_ext and pinky_ext:
        return "OPEN_PALM"
    if not thumb_ext and not index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "FIST"
    if not thumb_ext and not index_ext and middle_ext and not ring_ext and not pinky_ext:
        return "MIDDLE_FINGER"

    return "DETECTING"

# ─────────────────────────────────────────────
# Gesture labels
# ─────────────────────────────────────────────
GESTURE_LABELS = {
    "THUMBS_UP":     "Thumbs Up",
    "PEACE":         "Peace / Victory",
    "POINTER":       "Pointer",
    "OPEN_PALM":     "Open Palm",
    "FIST":          "Fist",
    "MIDDLE_FINGER": "Middle Finger",
    "DETECTING":     "Detecting...",
}

# ─────────────────────────────────────────────
# MediaPipe Hand Landmarker
# ─────────────────────────────────────────────
base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
options = mp_vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
    running_mode=mp_vision.RunningMode.VIDEO,
)
landmarker = mp_vision.HandLandmarker.create_from_options(options)

# ─────────────────────────────────────────────
# Hand skeleton drawing
# ─────────────────────────────────────────────
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

def draw_hand(frame, landmarks, h, w):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
    for x, y in pts:
        cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

# ─────────────────────────────────────────────
# Cooldown + stable-gesture config
# ─────────────────────────────────────────────
COOLDOWN_SECONDS = 2.0
STABLE_FRAMES    = 4      # frames a gesture must be held before firing

last_trigger_time      = 0.0
last_triggered_gesture = None
gesture_hold_count     = 0
prev_raw_gesture       = None

LEGEND = [
    "GESTURE CONTROLS",
    "Thumbs Up   ->  Play / Pause",
    "Peace       ->  Next Track",
    "Pointer     ->  Prev Track",
    "Open Palm   ->  Volume Up",
    "Fist        ->  Volume Down",
]

# ─────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    sys.exit(1)

frame_idx = 0
plat_label = (
    "pyautogui media keys" if PLATFORM == "win32"
    else "AppleScript" if PLATFORM == "darwin"
    else "playerctl"
)
print(f"[Platform] {PLATFORM} — using {plat_label}")
print("Open Spotify desktop app and press Play, then make gestures.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]
    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image     = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC)) or frame_idx * 33
    result       = landmarker.detect_for_video(mp_image, timestamp_ms)
    frame_idx   += 1

    current_gesture = "NO_HAND"
    now = time.time()

    if result.hand_landmarks:
        landmarks       = result.hand_landmarks[0]
        draw_hand(frame, landmarks, h, w)
        current_gesture = recognize_gesture(landmarks)

        if current_gesture == prev_raw_gesture:
            gesture_hold_count += 1
        else:
            gesture_hold_count = 1
        prev_raw_gesture = current_gesture

        if (
            current_gesture in ACTIONS_MAP
            and gesture_hold_count >= STABLE_FRAMES
        ):
            gesture_changed  = current_gesture != last_triggered_gesture
            cooldown_elapsed = (now - last_trigger_time) >= COOLDOWN_SECONDS

            if gesture_changed or cooldown_elapsed:
                _run_action(ACTIONS_MAP[current_gesture])
                last_trigger_time      = now
                last_triggered_gesture = current_gesture
    else:
        gesture_hold_count = 0
        prev_raw_gesture   = None

    # ── HUD ──────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 55), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    display_label = GESTURE_LABELS.get(current_gesture, current_gesture)
    cv2.putText(frame, f"Gesture: {display_label}", (10, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

    feedback = get_feedback()
    if feedback:
        cv2.putText(frame, feedback, (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 100), 2, cv2.LINE_AA)

    legend_y_start = h - (len(LEGEND) * 22 + 15)
    legend_overlay = frame.copy()
    cv2.rectangle(legend_overlay, (0, legend_y_start - 8), (370, h), (0, 0, 0), -1)
    cv2.addWeighted(legend_overlay, 0.45, frame, 0.55, 0, frame)
    for i, line in enumerate(LEGEND):
        y      = legend_y_start + i * 22
        color  = (255, 255, 0) if i == 0 else (200, 200, 200)
        size   = 0.55 if i == 0 else 0.48
        weight = 2 if i == 0 else 1
        cv2.putText(frame, line, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, size, color, weight, cv2.LINE_AA)

    cv2.imshow("Hand Gesture -> Spotify Control  (press Q to quit)", frame)
    if cv2.waitKey(5) & 0xFF == ord("q"):
        break

landmarker.close()
cap.release()
cv2.destroyAllWindows()
