<!--  this is a task file for the algorithm compiler set -->

# purpose
通过指定compile模板，批量将外部算法源文件编译为CFED保护的算法源文件和无保护的算法源文件， 并将生成的文件分别保存到指定目录， 包括Edges、RTL_Protected、RTL_Unprotected。

# task
1. 参考cfed_basic/academiccasestudies/CRC/makefile， 编写compile模板
2. 参考cfed_basic/academiccasestudies/CRC/algorithms/crc32.cpp和main.cpp， 编写算法源文件
3. 撰写脚本，自动生成plugin_config.mak文件, 并根据plugin_config.mak文件， 生成CFED保护的算法源文件和无保护的算法源文件
4. 将编译的文件分别保存到指定目录， 包括Edges、RTL_Protected、RTL_Unprotected

# expected output
1. 生成的CFED保护的算法源文件
2. 生成的无保护的算法源文件
3. 生成的CFED保护的算法源文件和无保护的算法源文件的目录


