# 选择更小的 Debian 版本
FROM debian:bookworm-slim

# 避免交互模式
ENV DEBIAN_FRONTEND=noninteractive

# 安装基础依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++-7 \
    gcc-arm-none-eabi \
    gdb \
    make \
    cmake \
    build-essential \
    git \
    python3 \
    python3-pip \
    clang \
    vim \
    wget \
    sudo \
    openssh-server \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 创建开发用户
RUN useradd -ms /bin/bash developer && echo "developer:developer" | chpasswd && adduser developer sudo

# 启动 SSH 服务器（如果需要）
RUN mkdir /var/run/sshd

# 设置默认工作目录
WORKDIR /home/developer/workspace

# 复制并设置 entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 启动 Bash
ENTRYPOINT ["/entrypoint.sh"]
