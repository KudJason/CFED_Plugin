import json
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# 定义知识蒸馏架构模型
class ProtectionVariable(BaseModel):
    name: str
    scope: str  # GLOBAL, LOCAL
    init: str
    updates: Dict[str, Any]  # 使用字典来存储更新模式

class ProtectionCheck(BaseModel):
    block_id: int
    location: str  # BEGIN, END
    expression: str
    handling: str  # ABORT, RECOVER, LOG

class Randomization(BaseModel):
    block_id: int
    signature: str
    properties: List[str]
    state_updates: Dict[str, str]

class BlockNode(BaseModel):
    id: int
    range: List[int]
    pattern: str  # BRANCH, SEQUENCE, LOOP
    successors: List[Dict[str, Any]]

class ProtectionSchema(BaseModel):
    metadata: Dict[str, Any]
    cfg: Dict[str, Any]
    protection: Dict[str, Any]

# 主要的分析函数
def load_record_data(file_path: str) -> Dict[str, Any]:
    """加载record.json数据"""
    with open(file_path, 'r') as f:
        return json.load(f)

def extract_features_from_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """从记录中提取关键特征"""
    features = {
        "algorithm_name": record.get("algorithm_name", ""),
        "technique": record.get("technique", ""),
        "technique_type": record.get("technique_type", ""),
        "selective_level": record.get("selective_level", ""),
        "platform": record.get("platform", ""),
    }
    return features

def analyze_protection_patterns(record: Dict[str, Any]) -> Dict[str, Any]:
    """分析保护模式"""
    # 这里可以根据record中的数据分析保护模式
    # 例如判断是CFE还是RACFE，以及使用了哪些保护策略
    
    protection_analysis = {
        "protection_type": "CFE" if "CFE" in record.get("technique", "") else "RACFE",
        "patterns": [],
        "effectiveness": 0.0
    }
    
    # 可以根据实际情况添加更多分析逻辑
    
    return protection_analysis

def generate_protection_schema(record: Dict[str, Any]) -> ProtectionSchema:
    """生成统一的保护模式"""
    # 这是一个示例，实际实现需要根据record的具体内容来填充
    schema = ProtectionSchema(
        metadata={
            "id": record.get("_id", ""),
            "files": {
                "protected": "",
                "unprotected": ""
            },
            "protection_type": "CFE" if "CFE" in record.get("technique", "") else "RACFE"
        },
        cfg={
            "blocks": [
                # 示例块，实际应根据record内容构建
                {
                    "id": 1,
                    "range": [0, 0],
                    "pattern": "BRANCH",
                    "successors": []
                }
            ],
            "entry": 1,
            "exit": [1]
        },
        protection={
            "variables": [],
            "checks": [],
            "randomization": []
        }
    )
    return schema

def create_training_data(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """创建用于模型微调的训练数据"""
    training_data = []
    
    for record in records:
        features = extract_features_from_record(record)
        protection_analysis = analyze_protection_patterns(record)
        
        # 合并特征和分析结果
        training_item = {**features, **protection_analysis}
        training_data.append(training_item)
    
    return pd.DataFrame(training_data)

def visualize_protection_patterns(df: pd.DataFrame) -> None:
    """可视化保护模式的分布"""
    if len(df) == 0:
        print("没有数据可视化")
        return
    
    # 示例：技术类型的分布
    plt.figure(figsize=(10, 6))
    technique_counts = df['technique_type'].value_counts()
    technique_counts.plot(kind='bar')
    plt.title('Protection Technique Types Distribution')
    plt.xlabel('Technique Type')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig('protection_techniques_distribution.png')
    
    # 可以添加更多可视化图表

def cluster_protection_patterns(df: pd.DataFrame, n_clusters: int = 3) -> np.ndarray:
    """对保护模式进行聚类"""
    if len(df) < n_clusters:
        print(f"数据集太小 ({len(df)} 条记录), 无法分为 {n_clusters} 个簇")
        return np.zeros(len(df))
    
    # 使用TF-IDF向量化算法名和技术
    vectorizer = TfidfVectorizer()
    
    # 组合文本特征
    text_features = df['algorithm_name'] + " " + df['technique']
    X = vectorizer.fit_transform(text_features)
    
    # 使用PCA降维
    pca = PCA(n_components=min(X.shape[1], 2))
    X_pca = pca.fit_transform(X.toarray())
    
    # K-means聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(X_pca)
    
    # 可视化聚类结果
    plt.figure(figsize=(10, 8))
    for i in range(n_clusters):
        plt.scatter(
            X_pca[clusters == i, 0], 
            X_pca[clusters == i, 1],
            label=f'Cluster {i}'
        )
    plt.legend()
    plt.title('Protection Patterns Clusters')
    plt.xlabel('PCA Component 1')
    plt.ylabel('PCA Component 2')
    plt.tight_layout()
    plt.savefig('protection_clusters.png')
    
    return clusters

def prepare_finetuning_dataset(df: pd.DataFrame, output_file: str = 'finetuning_data.jsonl') -> None:
    """准备用于模型微调的数据集"""
    finetuning_data = []
    
    for _, row in df.iterrows():
        # 创建输入提示
        prompt = f"""
分析以下算法的保护模式:
算法名称: {row['algorithm_name']}
技术: {row['technique']}
技术类型: {row['technique_type']}
选择级别: {row['selective_level']}
平台: {row['platform']}
        """
        
        # 创建期望的响应 (根据保护类型创建适当的模板)
        if row.get('protection_type') == 'CFE':
            response = """
{
  "protection_type": "CFE",
  "analysis": {
    "variables": [
      {
        "name": "S",
        "scope": "GLOBAL",
        "init": "#BB_ID[1]",
        "updates": {
          "pattern": "CONDITIONAL",
          "blocks": {
            "1": {"true": "S+#BB_ID[2]", "false": "S+#BB_ID[3]"}
          }
        }
      }
    ],
    "checks": [
      {
        "block_id": 1,
        "location": "BEGIN",
        "expression": "S == #BB_ID",
        "handling": "ABORT"
      }
    ]
  }
}
            """
        else:  # RACFE
            response = """
{
  "protection_type": "RACFE",
  "analysis": {
    "randomization": [
      {
        "block_id": 1,
        "signature": "#Sig",
        "properties": ["UNIQUE"],
        "state_updates": {
          "begin": "S -= #SubRanPrevVal",
          "end": "S += #Sig - #NextSig"
        }
      }
    ]
  }
}
            """
        
        # 添加到微调数据集
        finetuning_data.append({
            "messages": [
                {"role": "system", "content": "你是一个专门分析CFE和RACFE保护模式的AI助手。根据给定的算法信息，分析并生成相应的保护模式结构。"},
                {"role": "user", "content": prompt.strip()},
                {"role": "assistant", "content": response.strip()}
            ]
        })
    
    # 保存为JSONL格式
    with open(output_file, 'w') as f:
        for item in finetuning_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"已生成微调数据集: {output_file}")

def main():
    # 加载数据
    record_path = 'src/analyzer/record.json'
    records = [load_record_data(record_path)]  # 如果record.json不是数组，则包装成数组
    
    print(f"加载了 {len(records)} 条记录")
    
    # 创建训练数据
    df = create_training_data(records)
    print(f"创建了 {len(df)} 条训练数据")
    
    # 可视化保护模式
    visualize_protection_patterns(df)
    
    # 如果有足够的数据，进行聚类
    if len(df) >= 3:
        clusters = cluster_protection_patterns(df)
        df['cluster'] = clusters
    
    # 准备微调数据集
    prepare_finetuning_dataset(df)
    
    print("分析完成。")

if __name__ == "__main__":
    main() 