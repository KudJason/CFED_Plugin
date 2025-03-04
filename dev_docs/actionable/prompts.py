"""
Templates for staged RTL protection analysis with minimal token usage
"""

# Stage 1: CFG Extraction - First API call
CFG_EXTRACTION = """
# 第一阶段：控制流图提取
# 功能：从RTL代码中提取控制流图结构
# 输入：受保护和未受保护的RTL文件
# 输出：JSON格式的控制流图，包含基本块、入口点、出口点和块间关系
Extract the control flow graph from:
Protected RTL: {protected_file}
Unprotected RTL: {unprotected_file}

Return ONLY the JSON CFG containing:
- Basic blocks with IDs and ranges
- Entry/exit points
- Successors with conditions
- Block patterns (SEQUENCE/BRANCH/LOOP)

JSON output should match this schema:
{
  "blocks": [
    {
      "id": int,
      "range": [start_line, end_line],
      "pattern": "SEQUENCE|BRANCH|LOOP",
      "successors": [{"id": int, "condition": "condition_str"}]
    }
  ],
  "entry": int,
  "exit": [int]
}
"""

# Stage 2: Pattern Detection - Second API call
PATTERN_DETECTION = """
# 第二阶段：保护模式检测
# 功能：通过比较受保护和未受保护的代码，识别保护模式
# 输入：RTL文件和控制流图
# 输出：JSON格式的保护模式集合，包含模式类型、模板和参数
Identify protection patterns by comparing:
Protected RTL: {protected_file}
Unprotected RTL: {unprotected_file}
CFG: {cfg_json}

Group blocks by common protection patterns.
For each pattern, provide:
1. Pattern type (VARIABLE_CHECK, SIGNATURE_VALIDATION, etc.)
2. Template expression (using S, BB_ID, etc. as variables)
3. Blocks that share this pattern
4. Parameters that vary between blocks

Return JSON matching:
{
  "protection_type": "CFE|RACFE|BOTH",
  "patterns": [
    {
      "type": "pattern_name",
      "template": "mathematical_formula",
      "blocks": [block_ids],
      "parameters": {"param1": "value1"}
    }
  ]
}
"""

# Stage 3: Protection Schema - Final API call
PROTECTION_SCHEMA = """
# 第三阶段：保护模式生成
# 功能：基于控制流图和检测到的模式，生成完整的保护机制
# 输入：控制流图和保护模式
# 输出：JSON格式的完整保护模式，包含变量、更新规则和检查点
Create complete protection schema by applying patterns:
CFG: {cfg_json}
Patterns: {patterns_json}

For each variable and block, generate:
1. Concrete initialization expressions
2. Update expressions at each transition
3. Check expressions at specified locations

Return final JSON matching:
{
  "variables": [
    {
      "name": "var_name",
      "init": "init_expr",
      "updates": {
        "block_id": {
          "expression": "default_expr",
          "conditions": {"cond1": "expr1"}
        }
      }
    }
  ],
  "checks": [
    {
      "block_id": int,
      "location": "BEGIN|END",
      "expression": "check_expr"
    }
  ],
  "randomization": {} # If RACFE is used
}
"""

# Optional stage for detailed block analysis if needed
BLOCK_ANALYSIS = """
# 可选阶段：详细块分析
# 功能：深入分析特定块中的保护实现细节
# 输入：特定块的受保护和未受保护代码
# 输出：JSON格式的块级保护实现细节
Analyze the specific implementation of protection in block {block_id}:
Protected code:
{protected_block}

Unprotected code:
{unprotected_block}

Identify:
1. Variable modifications
2. Check expressions
3. Protection mechanism details

Return only the specific implementation details as JSON.
"""

# Batch processing prompt to handle multiple blocks at once
BATCH_PROCESSING = """
# 批量处理阶段
# 功能：同时处理多个具有相同保护模式的块
# 输入：块ID列表、模式类型和模板
# 输出：JSON格式的块级实现映射
Process the following {pattern_type} blocks together: {block_ids}

For each block, apply the template:
{template}

With parameters:
{parameters}

Return all block-specific implementations as a JSON mapping from block ID to implementation.
"""
