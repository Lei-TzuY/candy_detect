"""
Jetson TX2 性能基准测试脚本
测试不同模型格式的推理速度和资源占用
"""
from ultralytics import YOLO
import cv2
import time
import numpy as np
from pathlib import Path
import psutil
import os

def get_gpu_memory():
    """获取 GPU 内存使用（Jetson 专用）"""
    try:
        with open('/proc/driver/nvidia/gpuinfo', 'r') as f:
            info = f.read()
            # 这是简化版本，实际需要解析更多信息
            return "GPU Info Available"
    except:
        return "N/A"

def benchmark_model(model_path, num_frames=100):
    """
    对模型进行基准测试
    
    Args:
        model_path: 模型路径
        num_frames: 测试帧数
    
    Returns:
        dict: 性能指标
    """
    print(f"\n{'='*60}")
    print(f"测试模型: {model_path}")
    print(f"{'='*60}")
    
    if not Path(model_path).exists():
        print(f"❌ 模型不存在: {model_path}")
        return None
    
    # 加载模型
    print("加载模型...")
    load_start = time.time()
    model = YOLO(model_path)
    load_time = time.time() - load_start
    print(f"✅ 模型加载时间: {load_time:.2f}s")
    
    # 创建测试图像
    test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    # 预热
    print("预热中...")
    for _ in range(10):
        _ = model.predict(test_image, verbose=False, device=0)
    
    # 基准测试
    print(f"运行 {num_frames} 帧基准测试...")
    inference_times = []
    cpu_usage = []
    memory_usage = []
    
    process = psutil.Process(os.getpid())
    
    for i in range(num_frames):
        # CPU 和内存监控
        cpu_usage.append(psutil.cpu_percent(interval=None))
        memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        
        # 推理
        start_time = time.time()
        results = model.predict(test_image, verbose=False, device=0, conf=0.3)
        inference_time = (time.time() - start_time) * 1000  # ms
        inference_times.append(inference_time)
        
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{num_frames}")
    
    # 计算统计
    results = {
        'model_path': model_path,
        'model_format': Path(model_path).suffix,
        'load_time': load_time,
        'avg_inference': np.mean(inference_times),
        'std_inference': np.std(inference_times),
        'min_inference': np.min(inference_times),
        'max_inference': np.max(inference_times),
        'avg_fps': 1000 / np.mean(inference_times),
        'avg_cpu': np.mean(cpu_usage),
        'avg_memory': np.mean(memory_usage),
        'p50_inference': np.percentile(inference_times, 50),
        'p95_inference': np.percentile(inference_times, 95),
        'p99_inference': np.percentile(inference_times, 99),
    }
    
    # 打印结果
    print(f"\n📊 性能指标:")
    print(f"  模型格式: {results['model_format']}")
    print(f"  加载时间: {results['load_time']:.2f}s")
    print(f"  平均推理: {results['avg_inference']:.2f}ms ± {results['std_inference']:.2f}ms")
    print(f"  延迟范围: {results['min_inference']:.2f}ms ~ {results['max_inference']:.2f}ms")
    print(f"  P50 延迟: {results['p50_inference']:.2f}ms")
    print(f"  P95 延迟: {results['p95_inference']:.2f}ms")
    print(f"  P99 延迟: {results['p99_inference']:.2f}ms")
    print(f"  平均 FPS: {results['avg_fps']:.2f}")
    print(f"  CPU 使用: {results['avg_cpu']:.1f}%")
    print(f"  内存使用: {results['avg_memory']:.1f}MB")
    
    return results

def main():
    """测试所有可用的模型格式"""
    # 可能的模型路径
    model_candidates = [
        'best.pt',
        'best.onnx',
        'best.torchscript',
        'yolov8n_candy_fp16.engine',
        'best_fp16.engine'
    ]
    
    all_results = []
    
    print("🚀 Jetson TX2 YOLOv8n 性能基准测试")
    print("=" * 60)
    
    # 系统信息
    print("\n💻 系统信息:")
    print(f"  CPU: {psutil.cpu_count()} 核")
    print(f"  内存: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f}GB")
    print(f"  可用内存: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.1f}GB")
    
    # 测试每个模型
    for model_path in model_candidates:
        if Path(model_path).exists():
            result = benchmark_model(model_path, num_frames=100)
            if result:
                all_results.append(result)
        else:
            print(f"\n⏭️  跳过: {model_path} (不存在)")
    
    # 对比结果
    if all_results:
        print("\n" + "=" * 60)
        print("📈 性能对比总结")
        print("=" * 60)
        
        # 按 FPS 排序
        all_results.sort(key=lambda x: x['avg_fps'], reverse=True)
        
        print(f"\n{'格式':<15} {'平均推理':<12} {'FPS':<8} {'内存':<10}")
        print("-" * 60)
        for r in all_results:
            format_name = r['model_format']
            print(f"{format_name:<15} {r['avg_inference']:>8.2f}ms   {r['avg_fps']:>6.2f}   {r['avg_memory']:>7.1f}MB")
        
        print("\n💡 推荐:")
        best = all_results[0]
        print(f"  最快模型: {best['model_format']} ({best['avg_fps']:.2f} FPS)")
        print(f"  预期性能: {1000/best['avg_inference']:.1f} FPS 实时检测")
        
        # 保存结果
        import json
        with open('jetson_benchmark_results.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n✅ 详细结果已保存到: jetson_benchmark_results.json")
    else:
        print("\n❌ 未找到任何可测试的模型")
        print("\n请先运行 export_for_jetson.py 导出模型")

if __name__ == '__main__':
    main()
