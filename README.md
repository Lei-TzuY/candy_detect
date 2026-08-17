# Candy Defect Detection System

A real-time visual inspection prototype for candy / small-product defect detection, built around YOLOv8 / YOLO11, multi-camera capture, model management, recording, annotation support and production-style reporting workflows.

> **Scope:** engineering prototype for inspection workflow experiments. It is not presented as a certified industrial safety or quality-control system.

## What this repository demonstrates

- multi-camera capture and live inference
- YOLO model switching and training workflow integration
- camera parameters such as exposure / focus and relay-delay configuration
- recording and annotation-assisted data collection
- defect statistics, history and CSV reporting
- Flask-based local web interface for operators / experiments

The value of the project is the end-to-end workflow around the model — capture, inference, configuration, review and reporting — rather than the YOLO call alone.

## System flow

```text
Camera(s)
   |
   v
Capture / configuration
   |
   v
YOLO inference
   |
   +------------------+
   |                  |
   v                  v
Live UI          Record / annotate
   |                  |
   +---------+--------+
             v
       Statistics / CSV
```

## Quick start

### Requirements

- Windows 10 / 11
- Python 3.9+
- NVIDIA GPU + CUDA recommended for real-time inference
- USB camera(s) compatible with the configured capture backend

### Install

```bash
git clone https://github.com/Lei-TzuY/candy_detect.git
cd candy_detect

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

start_all.bat
```

The startup script launches the Flask application and opens the local interface. Model availability / downloads depend on the current project configuration and installed Ultralytics dependencies.

## Main components

```text
src/
  web_app.py          Flask application / API wiring
  run_detector.py     inference path
  video_recorder.py   recording workflow
  yolov8_trainer.py   training integration

candy_detector/
  config.py           configuration
  models.py           data models
  logger.py           logging

static/               frontend assets
templates/            HTML templates
tools/                diagnostic / utility tools
scripts/              batch helpers
docs/                 project documentation
config.ini            runtime configuration
requirements.txt      Python dependencies
start_all.bat         Windows startup entrypoint
```

## Camera configuration

Example `config.ini` section:

```ini
[Camera1]
camera_index = 0
frame_width = 1280
frame_height = 720
default_focus = 128
exposure_value = -7
relay_delay_ms = 1600
```

Actual camera behavior depends on the device driver and supported controls, so exposure / focus values may need per-device calibration.

## Model workflow

The project supports a workflow around multiple YOLO model variants rather than hard-coding one checkpoint:

- choose / switch model variants
- run live inference
- collect or record new samples
- assist annotation / dataset preparation
- launch training workflows
- review defect counts and trends

Model quality is dataset-dependent. This repository should not be interpreted as claiming a fixed real-world defect-detection accuracy without a documented dataset, test split and evaluation protocol.

## Troubleshooting

### Camera cannot be opened

- check whether another application owns the camera
- verify the configured camera index
- confirm driver / capture-backend support
- use the diagnostic utilities under `tools/`

### Port 5000 is occupied

```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Model fails to load

- verify the model path / checkpoint
- check dependency versions
- inspect logs for the underlying error
- confirm CUDA / PyTorch compatibility when GPU inference is enabled

## What would strengthen this further

For a research or production-facing version, the next high-value evidence would be:

- a documented train / validation / test dataset split
- precision / recall / mAP by defect class
- inference latency and throughput on named hardware
- false-positive / false-negative examples
- camera-to-actuator timing measurements
- reproducible evaluation scripts in CI

Those metrics are intentionally not invented here; they should be added only when measured.

## License

See [LICENSE](LICENSE).

## Author

[@Lei-TzuY](https://github.com/Lei-TzuY)

---

## 中文簡介

這是一個以 YOLOv8 / YOLO11 為核心的即時視覺品檢原型，除了模型推論，也涵蓋多鏡頭、參數設定、錄影、標註輔助、模型管理與報表流程。

目前定位為工程與研究原型；若要主張實際產線準確率或工業部署能力，應再補上公開且可重現的資料集切分、mAP / precision / recall、延遲與誤判分析等量化證據。
