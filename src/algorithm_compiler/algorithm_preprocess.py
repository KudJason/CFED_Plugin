import os
import tempfile
import shutil
import re
from typing import Optional

# 定义常量
COMMON_CODE = """#define XSTR(x) #x
#define STR(x) XSTR(x)"""

PLUGIN_MARK = """__attribute__((CFED(STR(TECHNIQUE), STR(TECH_TYPE), SEL_LEVEL))) """

def get_default_output_file(algorithm_file: str) -> str:
    """根据输入文件路径生成默认输出文件路径"""
    directory = os.path.dirname(algorithm_file)
    return os.path.join(directory, "temp_algorithm.cpp")

def preprocess_algorithm(algorithm_file: str, algorithm_output_file: Optional[str] = None) -> bool:
    """
    使用LibClang库分析和修改C++代码，确保代码构建正常
    
    Args:
        algorithm_file: 输入的算法文件路径
        algorithm_output_file: 输出文件路径，默认为输入文件同目录下的temp_algorithm.cpp
        
    Returns:
        bool: 处理是否成功
    """
    if algorithm_output_file is None:
        algorithm_output_file = get_default_output_file(algorithm_file)
        
    try:
        import clang.cindex
        from clang.cindex import CursorKind
    except ImportError:
        print("请安装libclang: pip install libclang")
        return False
    
    # 读取原始文件内容
    with open(algorithm_file, 'r') as f:
        content = f.read()
    
    # 创建临时文件以防修改失败
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    
    # 使用LibClang解析代码
    index = clang.cindex.Index.create()
    try:
        # 解析C++文件
        tu = index.parse(algorithm_file)
        
        # 找到所有include语句的最后位置
        include_end_line = 0
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
                line = cursor.location.line
                if line > include_end_line:
                    include_end_line = line
        
        # 添加common_code到includes之后
        lines = content.split('\n')
        if include_end_line > 0:
            lines.insert(include_end_line, COMMON_CODE)
        else:
            # 如果没有include语句，添加到文件开头
            lines.insert(0, COMMON_CODE)
        
        # 找到所有函数定义并添加plugin_mark
        modified_content = '\n'.join(lines)
        functions = []
        
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == CursorKind.FUNCTION_DECL and not cursor.is_definition():
                continue
                
            if cursor.kind in [CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD]:
                if cursor.is_definition() and cursor.location.file and cursor.location.file.name == algorithm_file:
                    functions.append((cursor.location.line, cursor.displayname))
        
        # 按行号降序排序，以便从后向前插入（避免位置偏移）
        functions.sort(reverse=True)
        
        # 从后向前插入plugin_mark
        for line_num, func_name in functions:
            if line_num <= len(lines):
                # 找到函数定义的确切位置
                line_index = line_num - 1
                # 向前查找函数定义的开始
                while line_index > 0 and not (lines[line_index].strip().endswith('{') and func_name.split('(')[0] in lines[line_index]):
                    line_index -= 1
                
                if line_index >= 0:
                    lines.insert(line_index, PLUGIN_MARK.strip())
        
        modified_content = '\n'.join(lines)
        
        # 先写入临时文件
        with open(temp_file.name, 'w') as f:
            f.write(modified_content)
            
        # 验证修改后的代码是否可以被解析
        test_tu = index.parse(temp_file.name)
        if len(list(test_tu.diagnostics)) > 0:
            print("警告：修改后的代码可能有语法错误:")
            for diag in test_tu.diagnostics:
                print(f" - {diag.spelling}")
            print("尝试使用更保守的正则表达式方法...")
            return _preprocess_algorithm_regex(algorithm_file, algorithm_output_file)
        
        # 如果没有错误，将临时文件复制回原始文件
        shutil.copy(temp_file.name, algorithm_output_file)
        return True, algorithm_output_file
        
    except Exception as e:
        print(f"使用LibClang处理失败: {str(e)}")
        print("回退到正则表达式方法...")
        return _preprocess_algorithm_regex(algorithm_file, algorithm_output_file)
    finally:
        # 清理临时文件
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

def _preprocess_algorithm_regex(algorithm_file: str, algorithm_output_file: str) -> bool:
    """使用正则表达式的备用方法"""
    # 读取原始文件
    with open(algorithm_file, 'r') as f:
        content = f.read()
    
    # 添加common_code到includes之后
    include_pattern = r'(#\s*include\s+[<"].*?[>"]\s*\n)'
    last_include = list(re.finditer(include_pattern, content))
    
    if last_include:
        pos = last_include[-1].end()
        content = content[:pos] + "\n" + COMMON_CODE + "\n" + content[pos:]
    else:
        # 如果没有include语句，添加到文件开头
        content = COMMON_CODE + "\n" + content
    
    # 使用更精确的函数定义模式，匹配返回类型和函数名之间的位置
    function_pattern = r'((?:^|\n)(?:[\w:]+\s+)+)([\w:]+)\s*\([^{;]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:final\s*)?(?:=\s*default\s*)?(?:=\s*delete\s*)?(?:=\s*0\s*)?\s*{'
    
    # 从后向前添加plugin_mark
    matches = list(re.finditer(function_pattern, content))
    for match in reversed(matches):
        pos = match.start(2)  # 使用第二个捕获组的位置（函数名开始的位置）
        # 确保不在注释或字符串中
        if not _is_in_comment_or_string(content, pos):
            content = content[:pos] + PLUGIN_MARK + content[pos:]
    
    # 写回文件
    with open(algorithm_output_file, 'w') as f:
        f.write(content)
    
    return True, algorithm_output_file

def _is_in_comment_or_string(content: str, pos: int) -> bool:
    """检查位置是否在注释或字符串中"""
    # 简单检查 - 可以进一步改进
    line_start = content.rfind('\n', 0, pos) + 1
    line = content[line_start:pos]
    
    # 检查是否在行注释中
    if '//' in line:
        return True
    
    # 检查是否在块注释中
    comment_start = content.rfind('/*', 0, pos)
    if comment_start != -1 and content.find('*/', comment_start, pos) == -1:
        return True
    # 检查引号 - 简化版
    quote_count = line.count('"') - line.count('\\"')
    if quote_count % 2 == 1:
        return True
    
    return False 