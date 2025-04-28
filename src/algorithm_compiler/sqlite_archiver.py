"""
Module to archive and manage CFED build outputs using SQLite
"""

import sqlite3
from datetime import datetime
import os
import hashlib
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SQLiteBuildArchiver:
    """Class to handle archiving and retrieving CFED build outputs using SQLite"""
    
    def __init__(self, db_path=None):
        """
        Initialize SQLite connection
        
        Args:
            db_path: Path to SQLite database file (optional, defaults to cfed_builds.db)
        """
        try:
            if db_path is None:
                db_path = os.path.join("/workspace/data/database", 'cfed_builds.db')
            
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row  # Enable row name access
            
            # Create tables
            self._create_tables()
            
            logger.info(f"Successfully connected to SQLite database: {db_path}")
            
        except Exception as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        try:
            cursor = self.conn.cursor()
            
            # Create builds table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS builds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algorithm_name TEXT NOT NULL,
                    algorithm_path TEXT NOT NULL,
                    protected_function TEXT,
                    technique TEXT,
                    technique_type TEXT,
                    selective_level INTEGER,
                    build_timestamp DATETIME NOT NULL,
                    compiler_version TEXT,
                    plugin_version TEXT,
                    platform TEXT,
                    hostname TEXT,
                    metadata TEXT  -- JSON string for additional metadata
                )
            ''')
            
            # Create build_files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS build_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_content BLOB,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_type TEXT,
                    modified_time DATETIME,
                    FOREIGN KEY (build_id) REFERENCES builds (id)
                )
            ''')
            
            # Create plugin_outputs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plugin_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algorithm_name TEXT NOT NULL,
                    algorithm_path TEXT NOT NULL,
                    archive_timestamp DATETIME NOT NULL,
                    platform TEXT,
                    hostname TEXT,
                    metadata TEXT  -- JSON string for additional metadata
                )
            ''')
            
            # Create plugin_files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plugin_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_output_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_content BLOB,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_type TEXT,
                    modified_time DATETIME,
                    FOREIGN KEY (plugin_output_id) REFERENCES plugin_outputs (id)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_builds_timestamp ON builds(build_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_builds_algorithm ON builds(algorithm_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugin_outputs_timestamp ON plugin_outputs(archive_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_plugin_outputs_algorithm ON plugin_outputs(algorithm_name)')
            
            self.conn.commit()
            logger.info("Database tables and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of a file"""
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
        """Archive a build directory to SQLite"""
        try:
            cursor = self.conn.cursor()
            
            # Insert build record
            cursor.execute('''
                INSERT INTO builds (
                    algorithm_name, algorithm_path, protected_function,
                    technique, technique_type, selective_level,
                    build_timestamp, compiler_version, plugin_version,
                    platform, hostname, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                algorithm_info['filename'],
                algorithm_info['path'],
                compilation_params.get('function_name'),
                compilation_params.get('technique', 'unknown'),
                compilation_params.get('technique_type', 'unknown'),
                compilation_params.get('selective_level', 0),
                datetime.utcnow(),
                self._get_compiler_version(),
                self._get_plugin_version(),
                os.uname().sysname,
                os.uname().nodename,
                json.dumps(compilation_params)
            ))
            
            build_id = cursor.lastrowid
            
            # Archive build files
            for filename in os.listdir(build_dir):
                file_path = os.path.join(build_dir, filename)
                if os.path.isfile(file_path):
                    file_hash = self.calculate_file_hash(file_path)
                    file_stats = os.stat(file_path)
                    ext = os.path.splitext(filename)[1]
                    
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    cursor.execute('''
                        INSERT INTO build_files (
                            build_id, filename, file_content,
                            file_size, file_hash, file_type,
                            modified_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        build_id,
                        filename,
                        file_content,
                        file_stats.st_size,
                        file_hash,
                        ext.lstrip('.') if ext else 'unknown',
                        datetime.fromtimestamp(file_stats.st_mtime)
                    ))
            
            self.conn.commit()
            logger.info(f"Successfully archived build with ID: {build_id}")
            return build_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to archive build: {e}")
            raise

    def archive_plugin_output(self, build_dir, algorithm_info):
        """Archive GCC_Plugin_Output directory to SQLite"""
        try:
            cursor = self.conn.cursor()
            plugin_output_dir = os.path.join(build_dir, "GCC_Plugin_Output")
            
            if not os.path.exists(plugin_output_dir):
                raise FileNotFoundError(f"GCC_Plugin_Output directory not found: {plugin_output_dir}")
            
            # Insert plugin output record
            cursor.execute('''
                INSERT INTO plugin_outputs (
                    algorithm_name, algorithm_path,
                    archive_timestamp, platform, hostname
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                algorithm_info['filename'],
                algorithm_info['path'],
                datetime.utcnow(),
                os.uname().sysname,
                os.uname().nodename
            ))
            
            plugin_output_id = cursor.lastrowid
            
            # Archive plugin files
            for root, dirs, files in os.walk(plugin_output_dir):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, plugin_output_dir)
                    
                    file_hash = self.calculate_file_hash(file_path)
                    file_stats = os.stat(file_path)
                    ext = os.path.splitext(filename)[1]
                    
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    cursor.execute('''
                        INSERT INTO plugin_files (
                            plugin_output_id, file_path,
                            file_content, file_size,
                            file_hash, file_type,
                            modified_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        plugin_output_id,
                        rel_path,
                        file_content,
                        file_stats.st_size,
                        file_hash,
                        ext.lstrip('.') if ext else 'unknown',
                        datetime.fromtimestamp(file_stats.st_mtime)
                    ))
            
            self.conn.commit()
            logger.info(f"Successfully archived plugin output with ID: {plugin_output_id}")
            return plugin_output_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to archive plugin output: {e}")
            raise

    def list_builds(self, limit=10):
        """List recent builds with basic information"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, algorithm_name, protected_function,
                       technique, build_timestamp
                FROM builds
                ORDER BY build_timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            builds = cursor.fetchall()
            
            print("\nRecent Builds:")
            for build in builds:
                print(f"\nBuild ID: {build['id']}")
                print(f"Algorithm: {build['algorithm_name']}")
                print(f"Protected Function: {build['protected_function'] or 'N/A'}")
                print(f"Technique: {build['technique']}")
                print(f"Build Time: {build['build_timestamp']}")
                print("-" * 80)
            
            return builds
            
        except Exception as e:
            logger.error(f"Failed to list builds: {e}")
            raise

    def list_plugin_outputs(self, limit=10):
        """List recent plugin outputs with basic information"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT po.id, po.algorithm_name, po.archive_timestamp,
                       COUNT(pf.id) as total_files,
                       SUM(pf.file_size) as total_size
                FROM plugin_outputs po
                LEFT JOIN plugin_files pf ON po.id = pf.plugin_output_id
                GROUP BY po.id
                ORDER BY po.archive_timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            outputs = cursor.fetchall()
            
            print("\nRecent Plugin Outputs:")
            for output in outputs:
                print(f"\nOutput ID: {output['id']}")
                print(f"Algorithm: {output['algorithm_name']}")
                print(f"Archived at: {output['archive_timestamp']}")
                print(f"Total files: {output['total_files']}")
                print(f"Total size: {output['total_size']} bytes")
                
                # Get file types
                cursor.execute('''
                    SELECT DISTINCT file_type
                    FROM plugin_files
                    WHERE plugin_output_id = ?
                ''', (output['id'],))
                file_types = [row['file_type'] for row in cursor.fetchall()]
                print(f"File types: {', '.join(file_types)}")
                
                # List files
                cursor.execute('''
                    SELECT file_path, file_size
                    FROM plugin_files
                    WHERE plugin_output_id = ?
                ''', (output['id'],))
                files = cursor.fetchall()
                print("\nFiles:")
                for file in files:
                    print(f"  - {file['file_path']} ({file['file_size']} bytes)")
                print("-" * 80)
            
            return outputs
            
        except Exception as e:
            logger.error(f"Failed to list plugin outputs: {e}")
            raise

    def restore_build(self, build_id, output_dir):
        """Restore a build from SQLite to the filesystem"""
        try:
            cursor = self.conn.cursor()
            
            # Verify build exists
            cursor.execute('SELECT * FROM builds WHERE id = ?', (build_id,))
            build = cursor.fetchone()
            if not build:
                raise ValueError(f"Build {build_id} not found")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Restore files
            cursor.execute('''
                SELECT filename, file_content, file_hash
                FROM build_files
                WHERE build_id = ?
            ''', (build_id,))
            
            for file in cursor.fetchall():
                file_path = os.path.join(output_dir, file['filename'])
                with open(file_path, 'wb') as f:
                    f.write(file['file_content'])
                
                # Verify file hash
                restored_hash = self.calculate_file_hash(file_path)
                if restored_hash != file['file_hash']:
                    raise ValueError(f"Hash mismatch for restored file: {file['filename']}")
            
            logger.info(f"Successfully restored build to: {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Failed to restore build: {e}")
            raise

    def clean_archive(self, force=False):
        """Clean all archived data from SQLite"""
        try:
            cursor = self.conn.cursor()
            
            # Get current statistics
            cursor.execute('SELECT COUNT(*) as count FROM builds')
            builds_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM plugin_outputs')
            plugin_outputs_count = cursor.fetchone()['count']
            
            if not force:
                print("\nCurrent Archive Statistics:")
                print(f"Builds: {builds_count} records")
                print(f"Plugin Outputs: {plugin_outputs_count} records")
                
                confirmation = input("\nAre you sure you want to delete all archived data? (yes/no): ")
                if confirmation.lower() != 'yes':
                    print("Operation cancelled.")
                    return None
            
            # Delete all data
            cursor.execute('DELETE FROM build_files')
            cursor.execute('DELETE FROM builds')
            cursor.execute('DELETE FROM plugin_files')
            cursor.execute('DELETE FROM plugin_outputs')
            
            self.conn.commit()
            
            result = {
                'builds_deleted': builds_count,
                'plugin_outputs_deleted': plugin_outputs_count,
                'total_deleted': builds_count + plugin_outputs_count
            }
            
            print("\nCleanup Results:")
            print(f"Builds deleted: {result['builds_deleted']}")
            print(f"Plugin Outputs deleted: {result['plugin_outputs_deleted']}")
            print(f"Total records deleted: {result['total_deleted']}")
            
            logger.info(f"Successfully cleaned archive. Deleted {result['total_deleted']} records.")
            return result
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to clean archive: {e}")
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
        return "cfed-plugin-version-unknown"

    def __del__(self):
        """Close database connection when object is destroyed"""
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    """Example usage of SQLiteBuildArchiver"""
    try:
        # Initialize archiver
        archiver = SQLiteBuildArchiver()
        
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
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1
        
    return 0

if __name__ == '__main__':
    exit(main()) 