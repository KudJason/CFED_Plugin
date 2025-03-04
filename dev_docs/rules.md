# Actionable Detection Rules for CFE and RACFE

## Control Flow Error Detection (CFED) Rules
English:
The CFED technique maintains a state variable that tracks execution through basic blocks, ensuring that the control flow follows a predefined path. Each basic block has a unique identifier, and the state variable is checked and updated during program execution.

中文：
CFED 技术维护一个状态变量，跟踪通过基本块的执行，确保控制流遵循预定义的路径。每个基本块都有一个唯一标识符，程序执行期间会检查和更新状态变量。

```
Inserted Instructions:
SETUP (1):
    Var = #initial_value
    FUNC_FIRST_ORIG_INSTR

BEGIN (3):
    Compare(Var, #BB_ID)
    NEQ <error>
    Var += #random_val
    BB_FIRST_ORIG_INSTR

MIDDLE (0):
    BB_MIDDLE_ORIG_INSTR

END (...):
    CASE BB is COND_JUMP (2):
        Var -= #update_val_true
        BB_LAST_ORIG_INSTR
        Var -= #update_val_false
    DEFAULT (1):
        Var -= #update_val
        BB_LAST_ORIG_INSTR

INTRA (0):
    BB_ORIG_INSTR

Value Properties:
    0 < #initial_value < 15
    #BB_ID[BB] is UNIQUE
    #random_val[BB] is RANDOM
    #update_val_true[BB] = #BB_ID[BB] + #random_val[BB] - #BB_ID[BB.true]
    #update_val_false[BB] = #BB_ID[BB] + #random_val[BB] - #BB_ID[BB.false]
    #update_val[BB] = #BB_ID[BB] + #random_val[BB] - #BB_ID[BB.next]
```

## Randomized Accumulated Control Flow Error Detection (RACFED) Rules
English:
The RACFED technique enhances CFED by using signature-based validation with randomization. It maintains a state variable that is updated with unique, random values across basic blocks. The technique validates the state at the beginning of each block and handles different control flow paths accordingly.

中文：
RACFED 技术通过使用基于签名的验证和随机化来增强 CFED。它维护一个状态变量，该变量在各个基本块中使用唯一的随机值进行更新。该技术在每个块的开始处验证状态，并相应地处理不同的控制流路径。

```
Inserted Instructions:
SETUP (1):
    S = #initVal
    FUNC_FIRST_ORIG_INSTR

BEGIN (3):
    S -= #SubRanPrevVal
    Compare(S, #Sig)
    NEQ <error>
    BB_FIRST_ORIG_INSTR

MIDDLE (0):
    BB_MIDDLE_ORIG_INSTR

END (...):
    CASE BB is COND_JUMP (2):
        S += #AdjustVal_True
        BB_LAST_ORIG_INSTR
        S += #AdjustVal_False
    CASE BB is EXIT and BB_ORIG_INSTR[BB].size > 1 (3):
        S += #AdjustVal_Exit
        Compare(S, #ExitVal)
        NEQ <error>
        BB_EXIT_ORIG_INSTR
    DEFAULT (1):
        S += #AdjustVal
        BB_LAST_ORIG_INSTR

INTRA (...):
    CASE BB_ORIG_INSTR[BB].size > 2 (1):
        BB_ORIG_INSTR
        S += #IntraVal
    DEFAULT (0):
        BB_ORIG_INSTR

Value Properties:
    #initVal = #Sig[BB0] + #SubRanPrevVal[BB0]
    #Sig[BB] is UNIQUE, RANDOM
    #SubRanPrevVal[BB] is RANDOM
    (#Sig[BB] + #SubRanPrevVal[BB]) is UNIQUE
    #AdjustVal_True[BB] = (#Sig[BB] + #IntraVal[BB].sum) - (#Sig[BB.true] + #SubRanPrevVal[BB.true])
    #AdjustVal_False[BB] = (#Sig[BB] + #IntraVal[BB].sum) - (#Sig[BB.false] + #SubRanPrevVal[BB.false])
    #AdjustVal[BB] = (#Sig[BB] + #IntraVal[BB].sum) - (#Sig[BB.next] + #SubRanPrevVal[BB.next])
    #ExitVal[BB] is RANDOM
    #AdjustVal_Exit = (#Sig[BB] + #IntraVal[BB].sum) - #ExitVal[BB]
    #IntraVal is RANDOM
```