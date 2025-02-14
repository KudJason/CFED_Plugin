#!/bin/bash

# 启动 SSH 服务器（如果需要远程调试）
service ssh start

# 进入开发目录
cd /home/developer/workspace

# 开启交互式 Bash
exec bash
