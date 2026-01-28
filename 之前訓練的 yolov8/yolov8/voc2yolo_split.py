#!/usr/bin/env python3
"""
Convert Pascal VOC XML labels to YOLO format and split into train/val.
Supports two modes:
  - "abnormal_only": keep only 'abnormal' objects (single-class detector)
  - "binary": keep both classes 'abnormal' (0) and 'normal' (1)

Usage:
  python voc2yolo_split.py --src /path/to/train_folder --out ./dataset --mode abnormal_only --val 0.2

The script expects the source folder to contain images and their matching .xml files
with the same filename stem (e.g., foo.jpg + foo.xml). Images without XML are skipped.
"""
import json
import argparse
import random
import shutil
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

def voc_box_to_yolo(xmin, ymin, xmax, ymax, iw, ih):
    # Clamp to image bounds just in case
    xmin = max(0, min(xmin, iw))
    xmax = max(0, min(xmax, iw))
    ymin = max(0, min(ymin, ih))
    ymax = max(0, min(ymax, ih))
    w = xmax - xmin
    h = ymax - ymin
    cx = xmin + w / 2.0
    cy = ymin + h / 2.0
    # Normalize
    return cx / iw, cy / ih, w / iw, h / ih

def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    size = root.find("size")
    iw = int(size.findtext("width"))
    ih = int(size.findtext("height"))
    objects = []
    for obj in root.findall("object"):
        name = obj.findtext("name").strip()
        bnd = obj.find("bndbox")
        xmin = float(bnd.findtext("xmin"))
        ymin = float(bnd.findtext("ymin"))
        xmax = float(bnd.findtext("xmax"))
        ymax = float(bnd.findtext("ymax"))
        cx, cy, w, h = voc_box_to_yolo(xmin, ymin, xmax, ymax, iw, ih)
        objects.append((name, (cx, cy, w, h)))
    return iw, ih, objects

def write_label_yolo(label_path, objects, mode):
    """
    mode == 'abnormal_only' -> only class 'abnormal' kept as class 0
    mode == 'binary' -> classes: 0:'abnormal', 1:'normal'
    """
    lines = []
    for name, (cx, cy, w, h) in objects:
        if mode == "abnormal_only":
            if name.lower() == "abnormal":
                cls = 0
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        else:  # binary
            if name.lower() == "abnormal":
                cls = 0
            elif name.lower() == "normal":
                cls = 1
            else:
                # unknown class -> skip
                continue
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    # If no objects in abnormal_only mode, we intentionally create an empty file (background image)
    label_path.write_text("\n".join(lines))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Folder containing images + VOC XMLs")
    ap.add_argument("--out", default="dataset", help="Output dataset root")
    ap.add_argument("--mode", choices=["abnormal_only", "binary"], default="abnormal_only")
    ap.add_argument("--val", type=float, default=0.2, help="Validation fraction per class")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    img_out_train = out / "images" / "train"
    img_out_val   = out / "images" / "val"
    lbl_out_train = out / "labels" / "train"
    lbl_out_val   = out / "labels" / "val"
    for p in [img_out_train, img_out_val, lbl_out_train, lbl_out_val]:
        p.mkdir(parents=True, exist_ok=True)

    # Gather images with matching XML
    image_items = []
    for img_path in src.iterdir():
        if img_path.suffix.lower() in IMG_EXTS:
            xml_path = img_path.with_suffix(".xml")
            if xml_path.exists():
                image_items.append((img_path, xml_path))

    if not image_items:
        print("No (image, xml) pairs found in:", src, file=sys.stderr)
        sys.exit(1)

    # Split by presence of 'abnormal' object
    positives, negatives = [], []
    for img_path, xml_path in image_items:
        try:
            _, _, objs = parse_xml(xml_path)
        except Exception as e:
            print(f"[WARN] Failed to parse {xml_path.name}: {e}", file=sys.stderr)
            continue
        has_abnormal = any(o[0].lower() == "abnormal" for o in objs)
        if has_abnormal:
            positives.append((img_path, xml_path))
        else:
            negatives.append((img_path, xml_path))

    random.seed(args.seed)
    random.shuffle(positives)
    random.shuffle(negatives)

    def split_list(lst, frac):
        n_val = max(1, round(len(lst) * frac)) if lst else 0
        return lst[n_val:], lst[:n_val]

    train_pos, val_pos = split_list(positives, args.val)
    train_neg, val_neg = split_list(negatives, args.val)

    train_pairs = train_pos + train_neg
    val_pairs   = val_pos + val_neg

    random.shuffle(train_pairs)
    random.shuffle(val_pairs)

    # Convert + copy
    def process(pairs, img_dst, lbl_dst):
        for img_path, xml_path in pairs:
            # parse objects
            try:
                _, _, objs = parse_xml(xml_path)
            except Exception as e:
                print(f"[WARN] Skip {xml_path.name}: {e}", file=sys.stderr)
                continue
            # write label
            lbl_path = lbl_dst / (img_path.stem + ".txt")
            write_label_yolo(lbl_path, objs, args.mode)
            # copy image
            shutil.copy2(img_path, img_dst / img_path.name)

    process(train_pairs, img_out_train, lbl_out_train)
    process(val_pairs,   img_out_val,   lbl_out_val)

    # Summary
    summary = {
        "mode": args.mode,
        "total_pairs": len(image_items),
        "positives_with_abnormal": len(positives),
        "negatives_without_abnormal": len(negatives),
        "train_images": len(train_pairs),
        "val_images": len(val_pairs),
        "train_pos": len(train_pos),
        "train_neg": len(train_neg),
        "val_pos": len(val_pos),
        "val_neg": len(val_neg),
        "notes": "In abnormal_only mode, normal objects are dropped and normal-only images get empty label files."
    }
    print(json.dumps(summary, indent=2))

    # Also emit recommended data.yaml
    names = ["abnormal"] if args.mode == "abnormal_only" else ["abnormal", "normal"]
    data_yaml = out / ("data_abnormal.yaml" if args.mode == "abnormal_only" else "data_binary.yaml")
    data_yaml.write_text(
        "train: " + str((out / "images" / "train").resolve()) + "\n" +
        "val: "   + str((out / "images" / "val").resolve())   + "\n" +
        f"nc: {len(names)}\n" +
        "names: " + str(names) + "\n"
    )
    print(f"Wrote {data_yaml}")

if __name__ == "__main__":
    main()
