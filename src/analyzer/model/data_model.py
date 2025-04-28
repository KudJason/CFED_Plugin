from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class PluginFile:
    content: str
    function_name: str  # Function name part before "/"
    doc_name: str      # Document name part after "/"

@dataclass 
class DataModel:
    id: str
    algorithm_name: str
    algorithm_path: str
    technique: str
    technique_type: str
    selective_level: int
    archive_timestamp: datetime
    plugin_files: Dict[str, PluginFile]

    @classmethod
    def from_dict(cls, data: dict) -> 'DataModel':
        return cls(
            id=data['_id'],
            algorithm_name=data['algorithm_name'], 
            algorithm_path=data['algorithm_path'],
            technique=data['technique'],
            technique_type=data['technique_type'],
            selective_level=data['selective_level'],
            archive_timestamp=data.get('archive_timestamp', datetime.now()),
            plugin_files={
                k: PluginFile(
                    content=v['content'],
                    function_name=k.split('/')[0],
                    doc_name=k.split('/')[1]
                ) 
                for k, v in data['plugin_files'].items()
            }
        )
