"""
Module to archive and manage CFED build outputs using MongoDB
"""

from pymongo import MongoClient
from datetime import datetime
import os
import hashlib
import logging
from dotenv import load_dotenv
from bson.binary import Binary

# Load environment variables from .env file
load_dotenv("/workspace/data/.db_env")

# Get MongoDB connection string from environment variables
# DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
MONGO_USER = os.getenv("MONGO_APP_USER")
MONGO_PASSWORD = os.getenv("MONGO_APP_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")


MONGO_APP_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}/{MONGO_DATABASE}"
print(MONGO_APP_URI)
# Construct MongoDB connection string
if MONGO_APP_URI:
    MONGO_URI = MONGO_APP_URI
else:
    print("MONGO_APP_URI is not set")
    

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BuildArchiver:
    """Class to handle archiving and retrieving CFED build outputs"""
    
    def __init__(self, mongo_uri=None):
        """
        Initialize MongoDB connection
        
        Args:
            mongo_uri: MongoDB connection URI string (optional, uses env vars if not provided)
        """
        try:
            self.client = MongoClient(mongo_uri or MONGO_URI)
            self.db = self.client.cfed
            
            # Create indexes for faster querying
            self.db.builds.create_index([
                ("algorithm_name", 1),
                ("function_name", 1),
                ("technique", 1),
                ("build_timestamp", -1)  # Added timestamp index for recent builds
            ])
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def calculate_file_hash(self, file_path):
        """
        Calculate SHA256 hash of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            raise

    def archive_build(self, build_dir, algorithm_info, compilation_params):
        """
        Archive build metadata to MongoDB (without archiving files from the root build dir)
        
        Args:
            build_dir: Path to BUILD directory
            algorithm_info: Dictionary containing algorithm metadata
            compilation_params: Dictionary containing compilation parameters
        """
        # build_files dictionary remains empty as we are not archiving files from the root BUILD dir
        build_files = {} 
        
        try:
            # Create build directory if it doesn't exist
            os.makedirs(build_dir, exist_ok=True)
            plugin_output_path = os.path.join(build_dir, 'GCC_Plugin_Output')
            os.makedirs(plugin_output_path, exist_ok=True)
            
            # Set proper permissions (optional, consider security implications)
            # os.chmod(build_dir, 0o777) # Commented out for potentially better security practices
            # os.chmod(plugin_output_path, 0o777) # Commented out for potentially better security practices

            # Verify build directory exists
            if not os.path.exists(build_dir):
                raise FileNotFoundError(f"Build directory not found: {build_dir}")

            # The loop collecting files from the root build_dir is removed.
            # build_files remains empty.

            # Create build document (metadata only)
            build_doc = {
                # Algorithm metadata
                'algorithm_name': algorithm_info['filename'],
                'algorithm_path': algorithm_info['path'],
                
                # Compilation parameters
                'technique': compilation_params.get('technique', 'unknown'),
                'technique_type': compilation_params.get('technique_type', 'unknown'),
                'selective_level': compilation_params.get('selective_level', 0),
                
                # Build metadata
                'build_timestamp': datetime.utcnow(),
                'build_files': build_files,
                
                # Additional metadata
                'compiler_version': self._get_compiler_version(),
                'plugin_version': self._get_plugin_version(),
                
                # System info
                'platform': os.uname().sysname,
                'hostname': os.uname().nodename
            }
            
            
            
            # 如果提供了 function_name，则添加到文档中
            if 'function_name' in compilation_params:
                build_doc['protected_function'] = compilation_params['function_name']
            
            # Insert into MongoDB
            result = self.db.builds.insert_one(build_doc)
            logger.info(f"Successfully archived build with ID: {result.inserted_id}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Failed to archive build: {e}")
            raise

    def list_builds(self, limit=10):
        """List recent builds with basic information"""
        try:
            # Only include the fields we want (instead of excluding build_files)
            # 从数据库中查询构建记录，只返回指定的字段
            # Query builds from database, returning only specified fields
            builds = self.db.builds.find(
                {},
                {
                    '_id': 1,
                    'algorithm_name': 1,
                    'protected_function': 1,
                    'technique': 1,
                    'build_timestamp': 1
                }
            ).sort('build_timestamp', -1).limit(limit).allow_disk_use(True)
            
            return list(builds)
        except Exception as e:
            logger.error(f"Failed to list builds: {e}")
            raise

    def get_build_stats(self):
        """Get statistics about archived builds"""
        try:
            stats = {
                'total_builds': self.db.builds.count_documents({}),
                'total_size': sum(doc.get('size', 0) for doc in self.db.builds.find({}, {'size': 1})),
                'techniques_used': list(self.db.builds.distinct('technique')),
                'algorithms': list(self.db.builds.distinct('algorithm_name'))
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get build stats: {e}")
            raise

    def retrieve_build(self, query_params):
        """
        Retrieve a build from MongoDB based on query parameters
        
        Args:
            query_params: Dictionary containing search criteria
            e.g. {
                'algorithm_name': 'bubble_sort.cpp',
                'protected_function': 'bubbleSort',
                'technique': 'CFCSS'
            }
            
        Returns:
            dict: Build document from MongoDB
        """
        try:
            build = self.db.builds.find_one(query_params)
            if build:
                logger.info(f"Found build for query: {query_params}")
                return build
            else:
                logger.warning(f"No build found for query: {query_params}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve build: {e}")
            raise

    def restore_build(self, build_id, output_dir):
        """
        Restore a build from MongoDB to the filesystem
        
        Args:
            build_id: MongoDB ObjectId of the build
            output_dir: Directory to restore files to
            
        Returns:
            str: Path to the restored build directory
        """
        try:
            build = self.db.builds.find_one({'_id': build_id})
            if not build:
                raise ValueError(f"Build {build_id} not found")
                
            os.makedirs(output_dir, exist_ok=True)
            
            # Restore each file
            for filename, file_info in build['build_files'].items():
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(file_info['content'])
                    
                # Verify file hash
                restored_hash = self.calculate_file_hash(file_path)
                if restored_hash != file_info['hash']:
                    raise ValueError(f"Hash mismatch for restored file: {filename}")
                    
            logger.info(f"Successfully restored build to: {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Failed to restore build: {e}")
            raise

    def _get_compiler_version(self):
        """Get the compiler version used"""
        try:
            import subprocess
            result = subprocess.run(['gcc', '--version'], capture_output=True, text=True)
            return result.stdout.split('\n')[0]
        except:
            return "unknown"
        
    def _get_plugin_version(self):
        """Get the CFED plugin version"""
        # This should be implemented based on how version information
        # is stored in your CFED plugin
        return "cfed-plugin-version-unknown"

    def archive_plugin_output(self, build_dir, algorithm_info, compilation_params=None):
        """
        Archive .txt files from GCC_Plugin_Output directory to MongoDB
        
        Args:
            build_dir: Path to BUILD directory
            algorithm_info: Dictionary containing algorithm metadata
        """
        plugin_output_dir = os.path.join(build_dir, "GCC_Plugin_Output")
        if not os.path.exists(plugin_output_dir):
            # It might be okay if the directory doesn't exist, log a warning instead of raising error
            logger.warning(f"GCC_Plugin_Output directory not found: {plugin_output_dir}, skipping plugin output archiving.")
            return None # Indicate that nothing was archived

        plugin_files = {}
        
        try:
            # 遍历 GCC_Plugin_Output 下的所有子目录
            for root, dirs, files in os.walk(plugin_output_dir):
                for filename in files:
                    # Only process .txt files
                    if filename.endswith('.txt'):
                        file_path = os.path.join(root, filename)
                        # 计算相对路径，用于在数据库中组织文件结构
                        rel_path = os.path.relpath(file_path, plugin_output_dir)
                        
                        # 计算文件哈希
                        file_hash = self.calculate_file_hash(file_path)
                        
                        # 读取文件内容并转换为 Binary 用于 MongoDB 存储
                        with open(file_path, 'rb') as f:
                            content = Binary(f.read())
                        
                        # 获取文件统计信息
                        file_stats = os.stat(file_path)
                        
                        # 获取文件扩展名 (we know it's txt, but keep for consistency)
                        ext = os.path.splitext(filename)[1]
                        
                        # 存储文件信息
                        plugin_files[rel_path] = {
                            'content': content,
                            'size': file_stats.st_size,
                            'hash': file_hash,
                            'type': ext.lstrip('.') if ext else 'unknown',
                            'modified_time': datetime.fromtimestamp(file_stats.st_mtime)
                        }
            
            # Only create a document if there are .txt files to archive
            if not plugin_files:
                logger.info(f"No .txt files found in {plugin_output_dir} to archive.")
                return None

            # 创建插件输出文档
            plugin_doc = {
                'algorithm_name': algorithm_info['filename'],
                'algorithm_path': algorithm_info['path'],
                'technique': compilation_params.get('technique', 'unknown'),
                'technique_type': compilation_params.get('technique_type', 'unknown'),
                'selective_level': compilation_params.get('selective_level', 0),
                'archive_timestamp': datetime.utcnow(),
                'plugin_files': plugin_files,
                'platform': os.uname().sysname,
                'hostname': os.uname().nodename
            }
            
            # 插入到 MongoDB
            result = self.db.plugin_outputs.insert_one(plugin_doc)
            logger.info(f"Successfully archived plugin output with ID: {result.inserted_id}")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Failed to archive plugin output: {e}")
            raise

    def list_plugin_outputs(self, limit=10):
        """
        List recent plugin outputs with basic information
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            list: List of dictionaries containing basic plugin output information
        """
        try:
            # 查询最近的插件输出记录
            outputs = self.db.plugin_outputs.find(
                {},
                {
                    '_id': 1,
                    'algorithm_name': 1,
                    'algorithm_path': 1,
                    'archive_timestamp': 1,
                    'plugin_files': 1
                }
            ).sort('archive_timestamp', -1).limit(limit).allow_disk_use(True)
            
            # 处理结果，计算每个记录的文件统计信息
            formatted_outputs = []
            for output in outputs:
                files_info = {
                    'total_files': len(output['plugin_files']),
                    'total_size': sum(f['size'] for f in output['plugin_files'].values()),
                    'file_types': set(f['type'] for f in output['plugin_files'].values()),
                    'files': [{'path': path, 'size': info['size'], 'type': info['type']} 
                             for path, info in output['plugin_files'].items()]
                }
                
                formatted_output = {
                    'id': output['_id'],
                    'algorithm_name': output['algorithm_name'],
                    'algorithm_path': output['algorithm_path'],
                    'archive_timestamp': output['archive_timestamp'],
                    'files_info': files_info
                }
                formatted_outputs.append(formatted_output)
            
            # 打印信息
            print("\nRecent Plugin Outputs:")
            for output in formatted_outputs:
                print(f"\nOutput ID: {output['id']}")
                print(f"Algorithm: {output['algorithm_name']}")
                print(f"Archived at: {output['archive_timestamp']}")
                print(f"Total files: {output['files_info']['total_files']}")
                print(f"Total size: {output['files_info']['total_size']} bytes")
                print(f"File types: {', '.join(output['files_info']['file_types'])}")
                print("\nFiles:")
                for file in output['files_info']['files']:
                    print(f"  - {file['path']} ({file['size']} bytes)")
                print("-" * 80)
            
            return formatted_outputs
            
        except Exception as e:
            logger.error(f"Failed to list plugin outputs: {e}")
            raise

    def clean_archive(self, force=False):
        """
        Clean all archived data from MongoDB
        
        Args:
            force: If True, skip confirmation prompt
            
        Returns:
            dict: Statistics about deleted documents
        """
        try:
            # 获取当前归档统计信息
            stats = {
                'plugin_outputs': self.db.plugin_outputs.count_documents({}),
                'builds': self.db.builds.count_documents({})
            }
            
            if not force:
                # 显示当前归档统计信息
                print("\nCurrent Archive Statistics:")
                print(f"Plugin Outputs: {stats['plugin_outputs']} documents")
                print(f"Builds: {stats['builds']} documents")
                
                # 请求确认
                confirmation = input("\nAre you sure you want to delete all archived data? (yes/no): ")
                if confirmation.lower() != 'yes':
                    print("Operation cancelled.")
                    return None
            
            # 删除所有文档
            plugin_result = self.db.plugin_outputs.delete_many({})
            builds_result = self.db.builds.delete_many({})
            
            # 获取删除结果
            result = {
                'plugin_outputs_deleted': plugin_result.deleted_count,
                'builds_deleted': builds_result.deleted_count,
                'total_deleted': plugin_result.deleted_count + builds_result.deleted_count
            }
            
            # 打印删除结果
            print("\nCleanup Results:")
            print(f"Plugin Outputs deleted: {result['plugin_outputs_deleted']}")
            print(f"Builds deleted: {result['builds_deleted']}")
            print(f"Total documents deleted: {result['total_deleted']}")
            
            logger.info(f"Successfully cleaned archive. Deleted {result['total_deleted']} documents.")
            return result
            
        except Exception as e:
            logger.error(f"Failed to clean archive: {e}")
            raise

def main_test():
    """Run tests for BuildArchiver"""
    test_archive_plugin_output()
    return 0

def main():
    """Example usage of BuildArchiver"""
    try:
        # Initialize archiver
        archiver = BuildArchiver()
        
        # Example algorithm info
        algorithm_info = {
            'filename': 'sha256.c',
            'path': '/workspace/data/C-Plus-Plus/cryptography/sha256.c'
        }
        
        # Archive GCC_Plugin_Output
        plugin_output_id = archiver.archive_plugin_output(
            build_dir="/workspace/src/algorithm_compiler/BUILD",
            algorithm_info=algorithm_info
        )
        
        logger.info(f"Successfully archived plugin output with ID: {plugin_output_id}")
        
        # 显示已保存的插件输出信息
        archiver.list_plugin_outputs(5)
        
        # 如果需要清空归档，取消下面的注释并设置 force=True
        # archiver.clean_archive(force=True)
        
        # 运行测试函数
        main_test()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1
        
    return 0

def test_archive_plugin_output():
    from pymongo import MongoClient
    uri = "mongodb://cfed_user:neifa93@mongodb:27017/cfed"
    client = MongoClient(uri)
    db = client.cfed
    count = db.plugin_outputs.count_documents({})
    print(f"Plugin outputs in database: {count}")
    # 打印所有插件输出
    outputs = db.plugin_outputs.find({})
    # 分门别类地打印出Outputs中各个txt文件的行数
    print("\n=== 各文件行数统计 ===")
    file_line_counts = {}
    for output in outputs:
        print(f"Output Number: {output['algorithm_name']}")
        # 检查数据结构
        print(f"Output structure: {list(output.keys())}")
        
        # 检查plugin_files字段的格式
        if 'plugin_files' in output:
            if isinstance(output['plugin_files'], dict):
                print(f"Found {len(output['plugin_files'])} files in this output")
                for filename, file_info in output['plugin_files'].items():
                    # 验证文件信息结构
                    if not isinstance(file_info, dict) or 'content' not in file_info:
                        print(f"Invalid file info structure for {filename}: {type(file_info)}")
                        continue
                        
                    # 获取文件内容
                    content = file_info['content']
                    line_count = 0
                    
                    # Binary类型的内容处理（BSON的Binary类型）
                    if hasattr(content, 'data') and callable(getattr(content, 'data', None)):
                        try:
                            # 尝试将Binary对象转换为文本并计算行数
                            text_content = content.decode('utf-8', errors='ignore')
                            line_count = len(text_content.split('\n'))
                        except Exception as e:
                            print(f"Error decoding content for {filename}: {e}")
                            # 退而求其次，使用字节长度除以平均行长度估算行数
                            line_count = len(content) // 40  # 假设平均每行40个字符
                    elif isinstance(content, bytes):
                        try:
                            text_content = content.decode('utf-8', errors='ignore')
                            line_count = len(text_content.split('\n'))
                        except Exception as e:
                            print(f"Error decoding bytes for {filename}: {e}")
                            line_count = len(content) // 40
                    elif isinstance(content, str):
                        line_count = len(content.split('\n'))
                    else:
                        print(f"Unexpected content type for {filename}: {type(content)}")
                        continue
                        
                    # 记录行数统计信息
                    if filename not in file_line_counts:
                        file_line_counts[filename] = []
                    file_line_counts[filename].append(line_count)
                    
                    # 打印一些文件基本信息，例如大小
                    print(f"File: {filename}, Size: {file_info.get('size', 'unknown')} bytes, Lines: {line_count}")
            else:
                print(f"Plugin files field has unexpected type: {type(output['plugin_files'])}")
        else:
            print("没有找到任何plugin_files记录，请检查输出数据结构是否正确。")
    
    # 打印每种文件的行数统计
    for filename, counts in sorted(file_line_counts.items()):
        avg_lines = sum(counts) / len(counts) if counts else 0
        print(f"{filename}: 共{len(counts)}个文件, 平均行数: {avg_lines:.1f}, 最小行数: {min(counts) if counts else 0}, 最大行数: {max(counts) if counts else 0}")
    
    if not file_line_counts:
        print("没有找到任何plugin_files记录")



if __name__ == '__main__':
    # exit(main()) 
    main()
    test_archive_plugin_output()
    