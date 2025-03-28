import os

def list_subfolders(path):
    # 检查路径是否存在
    if not os.path.exists(path):
        print("路径不存在")
        return []
    
    # 遍历指定路径下的所有内容，筛选出文件夹
    subfolders = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    return subfolders


