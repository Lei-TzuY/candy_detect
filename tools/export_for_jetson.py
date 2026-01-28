"""
YOLOv8n 模型导出脚本 - 用于 Jetson TX2 部署
导出格式：ONNX（通用）和 TensorRT（优化）
"""
from ultralytics import YOLO
from pathlib import Path
import sys

def export_yolov8n_model():
    """导出 YOLOv8n 模型为多种格式"""
    
    # YOLOv8n 模型路径（根据 benchmark 结果）
    model_path = Path(r'd:\專案\candy\runs\detect\runs\detect\candy_yolov8n\weights\best.pt')
    
    if not model_path.exists():
        print(f"❌ 模型文件不存在: {model_path}")
        print("\n请检查以下可能的路径:")
        base_path = Path(r'd:\專案\candy\runs\detect')
        if base_path.exists():
            for pt_file in base_path.rglob('best.pt'):
                print(f"  - {pt_file}")
        sys.exit(1)
    
    print(f"✅ 找到模型: {model_path}")
    print(f"📦 模型信息:")
    print(f"   - 召回率: 0.967 (最高)")
    print(f"   - mAP50: 0.982")
    print(f"   - 参数量: 3.01M")
    print()
    
    # 加载模型
    model = YOLO(model_path)
    
    # 输出目录
    output_dir = Path(r'd:\專案\candy\models\jetson_deployment')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("开始导出模型...")
    print("=" * 60)
    
    # 1. 导出为 ONNX（推荐用于 Jetson）
    print("\n[1/3] 导出 ONNX 格式...")
    try:
        onnx_path = model.export(
            format='onnx',
            imgsz=640,
            dynamic=False,  # 固定 batch size 以提高性能
            simplify=True,  # 简化模型图
            opset=12        # ONNX opset 版本
        )
        print(f"✅ ONNX 导出成功: {onnx_path}")
    except Exception as e:
        print(f"❌ ONNX 导出失败: {e}")
    
    # 2. 导出为 TorchScript（备选）
    print("\n[2/3] 导出 TorchScript 格式...")
    try:
        torchscript_path = model.export(
            format='torchscript',
            imgsz=640
        )
        print(f"✅ TorchScript 导出成功: {torchscript_path}")
    except Exception as e:
        print(f"❌ TorchScript 导出失败: {e}")
    
    # 3. 尝试导出 TensorRT（需要 TensorRT 环境）
    print("\n[3/3] 尝试导出 TensorRT 引擎...")
    print("⚠️  注意: 这通常需要在 Jetson 上执行以获得最佳性能")
    try:
        engine_path = model.export(
            format='engine',
            imgsz=640,
            half=True,      # FP16 精度
            device=0,       # GPU
            workspace=4     # 4GB workspace
        )
        print(f"✅ TensorRT 导出成功: {engine_path}")
        print(f"💡 建议在 Jetson TX2 上重新生成 TensorRT 引擎以获得最佳性能")
    except Exception as e:
        print(f"⚠️  TensorRT 导出失败（预期行为）: {e}")
        print(f"💡 请将 ONNX 文件传输到 Jetson TX2 后使用 trtexec 转换")
    
    # 打印部署信息
    print("\n" + "=" * 60)
    print("✅ 模型导出完成！")
    print("=" * 60)
    print("\n📋 部署到 Jetson TX2 的步骤:")
    print("\n1. 传输模型文件到 Jetson:")
    print(f"   scp {onnx_path} jetson@<IP>:/home/jetson/models/")
    print("\n2. 在 Jetson TX2 上转换为 TensorRT:")
    print("   trtexec --onnx=best.onnx \\")
    print("           --saveEngine=yolov8n_candy_fp16.engine \\")
    print("           --fp16 \\")
    print("           --workspace=1024")
    print("\n3. 使用推理脚本进行检测")
    print(f"   python3 jetson_inference.py")
    print("\n📄 详细部署指南请查看: jetson_tx2_deployment.md")
    print()

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    export_yolov8n_model()
