"""
修复 labelImg 在 Python 3.13 上的兼容性问题
"""
import os
import sys

def fix_labelimg():
    """修复 labelImg 的 setValue float 错误"""
    
    print("=" * 70)
    print("🔧 修复 labelImg 兼容性问题")
    print("=" * 70)
    
    # 找到 labelImg 安装路径
    try:
        import labelImg
        labelimg_dir = os.path.dirname(labelImg.__file__)
        labelimg_file = os.path.join(labelimg_dir, 'labelImg.py')
        
        print(f"\n📁 labelImg 路径: {labelimg_file}")
        
        if not os.path.exists(labelimg_file):
            print("❌ 找不到 labelImg.py")
            return False
        
        # 读取文件
        print("\n🔄 读取文件...")
        with open(labelimg_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复 scroll_request 函数中的 float 问题
        original = "bar.setValue(bar.value() + bar.singleStep() * units)"
        fixed = "bar.setValue(int(bar.value() + bar.singleStep() * units))"
        
        if original in content:
            print(f"✅ 找到需要修复的代码")
            content = content.replace(original, fixed)
            
            # 备份原文件
            backup_file = labelimg_file + '.backup'
            if not os.path.exists(backup_file):
                print(f"💾 创建备份: {backup_file}")
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content.replace(fixed, original))
            
            # 写入修复后的文件
            print(f"✍️  写入修复...")
            with open(labelimg_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("\n" + "=" * 70)
            print("✅ 修复完成！")
            print("=" * 70)
            print("\n现在可以运行:")
            print('  labelImg "d:\\專案\\candy\\datasets\\candy_merged_20260116_154158\\images" "d:\\專案\\candy\\models\\classes.txt"')
            return True
        else:
            print("⚠️  代码已经被修复过或版本不同")
            return False
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

if __name__ == '__main__':
    fix_labelimg()
