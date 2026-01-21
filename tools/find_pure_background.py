"""
查找最接近纯背景的图片
通过分析图片的颜色分布，找到最"单调"的图片作为背景参考
"""
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from tqdm import tqdm


def calculate_color_variance(img_path):
    """
    计算图片的颜色方差
    方差越小 = 颜色越单调 = 越接近纯背景
    """
    try:
        # 读取图片
        pil_img = Image.open(img_path).convert('RGB')
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        # 转换为灰度
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 计算标准差（颜色变化程度）
        std_dev = np.std(gray)
        
        # 计算边缘密度（Canny边缘检测）
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        # 综合得分：标准差越小、边缘越少 = 越纯净
        score = std_dev + edge_density * 1000
        
        return score, std_dev, edge_density
        
    except Exception as e:
        print(f"⚠️  无法处理: {img_path.name} - {e}")
        return float('inf'), 0, 0


def find_pure_background(input_dir, top_n=5):
    """
    找出最接近纯背景的图片
    """
    input_path = Path(input_dir)
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print("找不到图片！")
        return
    
    print(f"🔍 分析 {len(image_files)} 张图片...")
    print("-" * 60)
    
    results = []
    
    for img_file in tqdm(image_files, desc="计算颜色方差"):
        score, std_dev, edge_density = calculate_color_variance(img_file)
        results.append({
            'file': img_file,
            'score': score,
            'std_dev': std_dev,
            'edge_density': edge_density
        })
    
    # 按得分排序（分数越低越纯净）
    results.sort(key=lambda x: x['score'])
    
    print("\n" + "=" * 60)
    print(f"🏆 最接近纯背景的 {top_n} 张图片:")
    print("=" * 60)
    
    for i, result in enumerate(results[:top_n], 1):
        print(f"\n{i}. {result['file'].name}")
        print(f"   综合得分: {result['score']:.2f}")
        print(f"   颜色标准差: {result['std_dev']:.2f} (越小越单调)")
        print(f"   边缘密度: {result['edge_density']:.4f} (越小越纯净)")
    
    print("\n" + "=" * 60)
    print(f"✅ 推荐使用: {results[0]['file'].name}")
    print(f"   完整路径: {results[0]['file']}")
    print("=" * 60)
    
    return results[0]['file']


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="查找最纯净的背景图片")
    parser.add_argument("--input", "-i", required=True, help="输入图片文件夹")
    parser.add_argument("--top", "-n", type=int, default=5, help="显示前 N 张最纯净的图片")
    
    args = parser.parse_args()
    
    find_pure_background(args.input, args.top)
