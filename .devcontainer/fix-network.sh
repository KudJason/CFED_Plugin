#!/bin/bash
# 修复Docker网络和MongoDB连接问题的脚本

echo "======================================================"
echo "CFED开发环境网络问题修复工具"
echo "======================================================"

# 确保使用sudo权限
if [ "$EUID" -ne 0 ]; then
  echo "请使用sudo运行此脚本"
  echo "用法: sudo $0"
  exit 1
fi

echo "1. 检查MongoDB容器状态..."
MONGO_CONTAINER=$(docker ps -q -f name=cfed-mongodb)

if [ -z "$MONGO_CONTAINER" ]; then
  echo "MongoDB容器未运行，尝试启动..."
  docker-compose -f $(dirname "$0")/docker-compose.yml up -d mongodb
  sleep 5
  MONGO_CONTAINER=$(docker ps -q -f name=cfed-mongodb)
  
  if [ -z "$MONGO_CONTAINER" ]; then
    echo "错误: 无法启动MongoDB容器。"
    exit 1
  fi
  echo "MongoDB容器已启动"
else
  echo "MongoDB容器正在运行: $MONGO_CONTAINER"
fi

echo "2. 验证网络连接..."
NETWORK=$(docker network ls -q -f name=cfed-network)

if [ -z "$NETWORK" ]; then
  echo "cfed-network网络不存在，创建中..."
  docker network create cfed-network
  echo "网络创建完成"
else
  echo "cfed-network网络存在: $NETWORK"
  
  # 检查容器是否连接到网络
  if ! docker network inspect $NETWORK | grep -q "cfed-mongodb"; then
    echo "将MongoDB容器连接到网络..."
    docker network connect $NETWORK $MONGO_CONTAINER
  fi
  
  DEV_CONTAINER=$(docker ps -q -f name=cfed-dev-container)
  if [ -n "$DEV_CONTAINER" ] && ! docker network inspect $NETWORK | grep -q "cfed-dev-container"; then
    echo "将开发容器连接到网络..."
    docker network connect $NETWORK $DEV_CONTAINER
  fi
fi

echo "3. 检查MongoDB服务状态..."
if ! docker exec $MONGO_CONTAINER mongosh --quiet --eval "db.adminCommand('ping')" --port 27017 -u admin -p password --authenticationDatabase admin; then
  echo "MongoDB服务无法响应，尝试重启..."
  docker restart $MONGO_CONTAINER
  echo "等待服务启动..."
  sleep 10
  
  if ! docker exec $MONGO_CONTAINER mongosh --quiet --eval "db.adminCommand('ping')" --port 27017 -u admin -p password --authenticationDatabase admin; then
    echo "错误: MongoDB服务无法响应，请手动检查配置"
  else
    echo "MongoDB服务已恢复"
  fi
else
  echo "MongoDB服务运行正常"
fi

echo "4. 修复权限问题..."
docker exec -u root $MONGO_CONTAINER chown -R mongodb:mongodb /data/db

echo "======================================================"
echo "修复操作完成。如果仍然存在问题，请尝试重建容器："
echo "1. docker-compose -f $(dirname "$0")/docker-compose.yml down"
echo "2. docker-compose -f $(dirname "$0")/docker-compose.yml up -d"
echo "======================================================" 