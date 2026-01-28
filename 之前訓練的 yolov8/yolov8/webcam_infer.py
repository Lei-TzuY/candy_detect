#!/usr/bin/env python3
from ultralytics import YOLO
import cv2

# Change to your trained weights path
WEIGHTS = "runs/detect/train/weights/best.pt"
CONF = 0.5

def main():
    model = YOLO(WEIGHTS)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Cannot open camera 0")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        results = model(frame, conf=CONF, verbose=False)
        annotated = results[0].plot()
        cv2.imshow("YOLOv8 - Webcam", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
