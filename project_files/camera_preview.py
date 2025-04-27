import cv2
import numpy as np
import time
import json
from picamera2 import Picamera2

# Emotion color mapping
color_to_emotion = {
    "red": "Frustrated",
    "green": "Confident",
    "blue": "Relieved",
    "yellow": "Overwhelmed",
    "orange": "Skeptical",
    "purple": "Satisfied"
}

# Load HSV color ranges from file
with open("project_files/hsv_ranges.json", "r") as f:
    hsv_ranges = json.load(f)

# Detection memory for stability
detection_counter = {}

# Camera setup
picam2 = Picamera2()
picam2.preview_configuration.main.size = (1240, 1280)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()
time.sleep(2)

try:
    while True:
        full_frame = picam2.capture_array()

        # Tray mask region
        y1, y2 = 150, 800
        x1, x2 = 100,1140
        tray_roi = full_frame[y1:y2, x1:x2]

        # Build tray mask
        tray_mask = np.zeros(full_frame.shape[:2], dtype=np.uint8)
        tray_mask[y1:y2, x1:x2] = 255

        # Convert to HSV and apply tray mask
        hsv = cv2.cvtColor(full_frame, cv2.COLOR_BGR2HSV)
        masked_hsv = cv2.bitwise_and(hsv, hsv, mask=tray_mask)

        detected = []

        for color_name, bounds in hsv_ranges.items():
            # Handle red separately since it has two ranges
            if color_name == "red":
                lower1 = np.array(bounds["lower1"])
                upper1 = np.array(bounds["upper1"])
                lower2 = np.array(bounds["lower2"])
                upper2 = np.array(bounds["upper2"])
                mask1 = cv2.inRange(masked_hsv, lower1, upper1)
                mask2 = cv2.inRange(masked_hsv, lower2, upper2)
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                lower = np.array(bounds["lower"])
                upper = np.array(bounds["upper"])
                mask = cv2.inRange(masked_hsv, lower, upper)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 2500:
                    x, y, w, h = cv2.boundingRect(cnt)

                    emotion = color_to_emotion.get(color_name)
                    detection_counter[color_name] = detection_counter.get(color_name, 0) + 1

                    if detection_counter[color_name] >= 4:
                        if emotion and emotion not in detected:
                            detected.append(emotion)
                            # Draw green detection box and label
                            cv2.rectangle(full_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(full_frame, color_name, (x, y - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        break  # One match per color per frame

        if detected:
            print("Detected emotions:", detected)

        # Draw tray boundary in RED for reference
        cv2.rectangle(full_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Show full frame
        cv2.imshow("Tray View", full_frame)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cv2.destroyAllWindows()
    picam2.close()
