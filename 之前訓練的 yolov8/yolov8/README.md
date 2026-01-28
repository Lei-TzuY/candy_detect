# Candy Defect PoC (Webcam + YOLOv8)

This starter gives you a **one-click path** to:
1) Convert your Pascal VOC XML labels into YOLO format
2) Split into train/val with class-aware logic
3) Train YOLOv8
4) Run a webcam demo

## 0) Create environment
```bash
conda create -n yolov8 python=3.10 -y
conda activate yolov8
pip install ultralytics opencv-python
```

## 1) Convert + Split

You said you have a single folder, e.g. `train/`, containing images and `.xml` files.
Run the converter in **abnormal-only** mode (recommended for PoC):
```bash
python voc2yolo_split.py --src /path/to/train --out ./dataset --mode abnormal_only --val 0.2
```
This produces:
```
dataset/
  images/{train,val}/
  labels/{train,val}/
  data_abnormal.yaml
```
If you prefer a **binary detector** (both `abnormal` and `normal` boxes):
```bash
python voc2yolo_split.py --src /path/to/train --out ./dataset --mode binary --val 0.2
```
This produces `data_binary.yaml` accordingly.

> Tip: In `abnormal_only` mode, normal boxes are dropped and normal-only images get **empty label files** (valid background).

## 2) Train
Start small (Nano) and increase if needed:
```bash
yolo detect train data=dataset/data_abnormal.yaml model=yolov8n.pt epochs=50 imgsz=640 batch=16
# or binary:
# yolo detect train data=dataset/data_binary.yaml model=yolov8n.pt epochs=50 imgsz=640 batch=16
```

Optional knobs:
- `imgsz=800` for a bit more detail (needs more VRAM)
- `workers=8` for faster dataloading
- `patience=20` for early stopping

## 3) Evaluate
ultralytics already reports Precision / Recall / mAP on the val set. Aim for **≥70% Recall** for PoC.

## 4) Webcam demo
Update the weights path in `webcam_infer.py` then run:
```bash
python webcam_infer.py
```
Press `q` to quit.

## Class imbalance advice (35 abnormal vs 527 normal)
- For PoC, **abnormal-only** detector is simpler and avoids labeling normal as a class.
- Increase positive variety: shoot more defect poses/lighting, or augment with different angles/backgrounds.
- YOLOv8 already does mosaic, flips, HSV jitter. If recall is low, try `imgsz=800` and `epochs=100`.

## Folder expectation
Your source `--src` folder should look like:
```
train/
  image1.jpg
  image1.xml
  image2.jpg
  image2.xml
  ...
```
Only image files with a matching `.xml` are used.

---
**Short checklist to finish PoC:**
1. Run converter (abnormal-only).
2. Train with `yolov8n.pt` 50 epochs.
3. Run webcam demo and record a short clip.
