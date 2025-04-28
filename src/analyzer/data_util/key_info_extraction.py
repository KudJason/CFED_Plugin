import re

def extract_core_instructions(content: str) -> str:
    """
    从RTL字符串中提取核心指令，去除所有非必要信息
    
    参数:
    content - 输入的RTL内容字符串
    
    返回:
    str - 提取后的核心指令字符串，保持原始RTL格式，包含BB标记和指令内容（包括特殊的BB:-2和BB:-1块）
    """
    
    content_downsize = downsize_rtl_str(content)
    
    blocks = re.findall(r'BB: (-?\d+)(.*?)(?=\n\nBB:|\n\n--+|\Z)', content_downsize, re.DOTALL)
    
    result = []
    for bb_num, block_content in blocks:
        # Add BB marker
        result.append(f"BB: {bb_num}")
        cleaned_instructions = []
        
        instructions = re.findall(r'\(insn[^\n]*\n\s*\([^)]*\)[^\n]*', block_content)
        
        # 对于特殊块（BB:-2和BB:-1），保留所有指令
        is_special_block = bb_num in ['-2', '-1']
        
        for instr in instructions:
            cleaned_instr = re.sub(r'"\/[^"]*":\d+', '', instr)
            cleaned_instr = re.sub(r'\s*\(expr_list:REG_[^)]*\)[^\n]*', '', cleaned_instr)
            cleaned_instr = re.sub(r'\(insn \d+ \d+ \d+ \d+', '(insn', cleaned_instr)
            
            # 对于特殊块，保留所有指令；对于普通块，保留核心操作和保护相关指令
            if is_special_block:
                cleaned_instr = re.sub(r'-1\s*\n\s*\(nil\)', '', cleaned_instr).strip()
                if cleaned_instr:
                    cleaned_instructions.append(cleaned_instr)
            else:
                core_operations = [
                    # 原有的核心操作
                    'set', 'if_then_else', 'plus', 'minus', 'mult', 'div', 
                    'ashift', 'compare', 'call', 'return',
                    # CFED相关操作
                    'Var', '#BB_ID', '#random_val', '#update_val',
                    # RACFED相关操作
                    'S', '#Sig', '#SubRanPrevVal', '#AdjustVal', '#IntraVal', '#ExitVal',
                    # 通用比较操作
                    'eq', 'ne', 'gt', 'ge', 'lt', 'le'
                ]
                
                if any(op in cleaned_instr for op in core_operations):
                    cleaned_instr = re.sub(r'-1\s*\n\s*\(nil\)', '', cleaned_instr).strip()
                    if cleaned_instr:
                        cleaned_instructions.append(cleaned_instr)
        
        if cleaned_instructions:
            result.extend(cleaned_instructions)
            result.append("-" * 40)
    
    result_str = "\n".join(result)
    # print("result_str") # Removed print
    # print("-" * 40) # Removed print
    # print(result_str) # Removed print
    # print("-" * 40) # Removed print
    # print(f"原始大小: {len(content)} 字节, 提取后: {len(result_str)} 字节") # Removed print
    return result_str





def downsize_rtl_str(content):
    """
    减小RTL内容大小，去除非必要内容
    
    参数：
    content - 输入RTL内容字符串
    
    返回：
    处理后的RTL内容字符串
    """
    # 过滤1：删除所有源文件路径引用
    content = re.sub(r'"\/[^"]*":[0-9]+', '', content)
    
    # 过滤2：删除冗余空行
    content = re.sub(r'\n\s*\n+', '\n\n', content)
    
    # 过滤3：删除调试信息（REG_*相关行）
    content = re.sub(r'\(expr_list:REG_[^)]*\)[^\n]*\n', '\n', content)
    
    # 过滤4：简化nil表达式
    content = re.sub(r'\(nil\)[^\n]*\n', '(nil)\n', content)
    
    return content