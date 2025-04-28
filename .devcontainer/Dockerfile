FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system packages in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    g++-multilib \
    gcc \
    gcc-multilib \
    git \
    libblas-dev \
    libffi-dev \
    libgmp3-dev \
    liblapack-dev \
    libssl-dev \
    linux-libc-dev \
    locales \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    sudo \
    vim \
    && locale-gen en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create developer user with root privileges
RUN useradd -m -s /bin/bash developer \
    && echo "developer:developer" | chpasswd \
    && adduser developer sudo \
    && echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# 设置工作目录
WORKDIR /workspace

# 创建并配置Python虚拟环境在/opt目录下（系统级目录，与工作区分开）
RUN mkdir -p /opt/venv/cfed && \
    python3 -m venv /opt/venv/cfed && \
    /opt/venv/cfed/bin/pip install --no-cache-dir pip setuptools wheel && \
    /opt/venv/cfed/bin/pip install --no-cache-dir \
        black \
        flake8 \
        ipykernel \
        ipython \
        jupyter \
        matplotlib \
        mypy \
        numpy \
        pandas \
        pylint \
        pymongo \
        pytest \
        python-dotenv \
        requests \
        scipy \
        pydantic \
        langchain \
        langchain-core \
        langchain-community \
        langchain-openai \
        langchain-text-splitters \
        langchain-chroma \
        tiktoken \
        openai \
        chromadb \
        faiss-cpu && \
    # 将虚拟环境注册为Jupyter内核
    /opt/venv/cfed/bin/python -m ipykernel install --user --name=cfed --display-name="Python (CFED)" && \
    # 确保目录权限正确
    chown -R developer:developer /opt/venv

# 创建符号链接，使VSCode可以更容易地找到Python解释器
RUN ln -sf /opt/venv/cfed/bin/python3 /usr/local/bin/python-cfed && \
    chmod +x /usr/local/bin/python-cfed

# Create helper directories and set permissions
RUN mkdir -p /home/developer/.vscode-server/extensions \
    && mkdir -p /home/developer/.config \
    && mkdir -p /home/developer/workspace \
    && mkdir -p /home/developer/.jupyter \
    && chown -R developer:developer /home/developer

# Set environment variables
ENV PYTHONPATH=/workspace \
    ARMGCC_DIR=/workspace/cfed_basic/toolchains/ARM/r5-r6 \
    ARMGCC7=/workspace/cfed_basic/toolchains/ARM/r5-r6 \
    CFED_PLUGIN_PATH=/workspace/cfed_basic/cfed_plugin \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    VIRTUAL_ENV=/opt/venv/cfed \
    PATH=/opt/venv/cfed/bin:$PATH

# 创建VSCode配置文件以自动使用正确的Python解释器
RUN mkdir -p /workspace/.vscode && \
    echo '{\n    "python.defaultInterpreterPath": "/opt/venv/cfed/bin/python",\n    "python.analysis.extraPaths": ["/workspace"],\n    "python.linting.enabled": true,\n    "python.formatting.provider": "black"\n}' > /workspace/.vscode/settings.json

# 添加一个启动脚本，确保Python解释器正确配置
RUN echo '#!/bin/bash\necho "正在检查Python环境..."\nwhich python\npython --version\necho "已安装的Python包:"\npip list\necho "环境变量:"\necho "PATH=$PATH"\necho "PYTHONPATH=$PYTHONPATH"\necho "VIRTUAL_ENV=$VIRTUAL_ENV"\necho "VSCode配置已自动设置，可在命令面板中点击\"Python: Select Interpreter\"手动选择/opt/venv/cfed/bin/python\"\necho "Jupyter内核已安装，可在Jupyter Notebook中选择Python (CFED)内核"\necho "也可以使用/usr/local/bin/python-cfed作为解释器路径"\n' > /workspace/check_env.sh && \
    chmod +x /workspace/check_env.sh

# 确保容器启动时自动激活虚拟环境并更新PYTHONPATH
RUN echo 'source /opt/venv/cfed/bin/activate' >> /home/developer/.bashrc && \
    echo 'export PYTHONPATH=$PYTHONPATH:/workspace' >> /home/developer/.bashrc && \
    echo 'echo "欢迎使用CFED开发环境! Python虚拟环境已激活(/opt/venv/cfed)。"' >> /home/developer/.bashrc && \
    echo 'echo "在VSCode中，使用命令面板(Ctrl+Shift+P)选择\"Python: Select Interpreter\"，然后点击\"Enter interpreter path\"，输入\"/opt/venv/cfed/bin/python\"或\"/usr/local/bin/python-cfed\""' >> /home/developer/.bashrc

# 创建备用虚拟环境以确保兼容性
RUN mkdir -p /home/developer/venv && \
    ln -sf /opt/venv/cfed /home/developer/venv/cfed && \
    chown -R developer:developer /home/developer/venv

# Switch to developer user by default
USER developer