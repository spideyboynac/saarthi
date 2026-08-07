import os
import pandas as pd
from huggingface_hub import snapshot_download

def main():
    base_dir = r"c:\Users\91740\Desktop\github\MyProjects\IIIT Pune"
    data_dir = os.path.join(base_dir, "data")
    output_dir = os.path.join(base_dir, "output")
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print("Downloading dataset to:", data_dir)
    snapshot_download(repo_id="L-NLProc/NyayaAnumana-Explanation-Data", repo_type="dataset", local_dir=data_dir)
    
    data_files = []
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith(('.csv', '.json', '.parquet', '.jsonl')):
                data_files.append(os.path.join(root, file))
    
    if not data_files:
        print("No data files found.")
        return

    target_file = data_files[0]
    for f in data_files:
        if 'train' in f:
            target_file = f
            break
            
    print("Loading file:", target_file)
    if target_file.endswith('.csv'):
        df = pd.read_csv(target_file)
    elif target_file.endswith('.json') or target_file.endswith('.jsonl'):
        try:
            df = pd.read_json(target_file, lines=True)
        except:
            df = pd.read_json(target_file)
    elif target_file.endswith('.parquet'):
        df = pd.read_parquet(target_file)
    else:
        print("Unsupported format")
        return

    total_row_count = len(df)
    columns = list(df.columns)
    first_3 = df.head(3).to_markdown()

    def word_count(text):
        if pd.isna(text):
            return 0
        return len(str(text).split())

    col1 = 'Case Description'
    col2 = 'Official Reasoning'
    
    stats_md = ""
    for target_col in [col1, col2]:
        actual_col = next((c for c in df.columns if target_col.lower().replace(' ', '') in c.lower().replace('_', '').replace(' ', '')), None)
        if actual_col:
            word_counts = df[actual_col].apply(word_count)
            stats = word_counts.describe().to_frame(name='Word Count').to_markdown()
            stats_md += f"### Stats for {actual_col}\n{stats}\n\n"
        else:
            stats_md += f"### Stats for {target_col}\nColumn not found in dataset.\n\n"

    output_content = f"""# Dataset Inspection

## Total Row Count
{total_row_count}

## Column Names
{', '.join(columns)}

## First 3 Rows
{first_3}

## Text Length Statistics
{stats_md}
"""
    out_path = os.path.join(output_dir, "dataset_inspection.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_content)
    print(f"Inspection output saved to {out_path}")

if __name__ == "__main__":
    main()
