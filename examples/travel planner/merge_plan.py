import json
import pandas as pd
from pathlib import Path
import chardet

def detect_encoding(file_path):
    """
    检测文件的编码格式
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def read_plan_file(file_path):
    """
    读取单个plan JSON文件，自动处理编码
    """
    try:
        # 首先尝试直接用utf-8读取
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)['plan']
    except UnicodeDecodeError:
        # 如果utf-8失败，则检测编码并重试
        encoding = detect_encoding(file_path)
        print(f"Detected encoding for {file_path}: {encoding}")
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return json.load(f)['plan']
        except Exception as e:
            # 如果还是失败，尝试其他常见编码
            for enc in ['gbk', 'gb2312', 'gb18030', 'latin1', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        return json.load(f)['plan']
                except Exception:
                    continue
            # 如果所有尝试都失败，抛出原始错误
            raise e

def merge_travel_plans():
    """
    合并所有travel plans并添加对应的query
    """
    # 读取Excel文件中的queries
    try:
        df = pd.read_excel('travel_planner_val.xlsx')
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return
    
    # 记录错误文件
    error_files = []
    success_count = 0
    
    # 直接写入文件，一次处理一个plan
    with open('merged_plans.jsonl', 'w', encoding='utf-8') as outfile:
        # 遍历所有可能的plan文件
        for idx in range(180):  # 从plan0.json到plan179.json
            plan_file = f'plan{idx}.json'
            
            # 检查文件是否存在
            if not Path(plan_file).exists():
                print(f"Warning: {plan_file} not found, skipping...")
                continue
                
            try:
                # 读取plan文件
                plan_data = read_plan_file(plan_file)
                
                # 获取对应的query
                if idx < len(df):
                    query = df.iloc[idx]['query']
                else:
                    print(f"Warning: No query found for index {idx}")
                    query = ""
                
                # 创建完整的数据结构
                plan_entry = {
                    "idx": idx,
                    "query": query,
                    "plan": plan_data
                }
                
                # 将单个plan写入文件，不带缩进，确保每个plan占一行
                json_line = json.dumps(plan_entry, ensure_ascii=False)
                outfile.write(json_line + '\n')
                
                success_count += 1
                print(f"Successfully processed {plan_file}")
                
            except Exception as e:
                error_msg = f"Error processing {plan_file}: {str(e)}"
                print(error_msg)
                error_files.append({"file": plan_file, "error": str(e)})
    
    # 打印处理摘要
    print(f"\nSummary:")
    print(f"Successfully processed {success_count} plans into merged_plans.jsonl")
    
    if error_files:
        print("\nFiles with errors:")
        for error in error_files:
            print(f"- {error['file']}: {error['error']}")

if __name__ == "__main__":
    merge_travel_plans()