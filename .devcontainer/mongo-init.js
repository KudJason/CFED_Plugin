// MongoDB初始化脚本
// 这个脚本将在MongoDB首次启动时执行

// 创建应用程序数据库和用户
db = db.getSiblingDB('cfed');

// 创建用户
db.createUser({
  user: 'cfed_user',
  pwd: 'cfed_password',
  roles: [
    { role: 'readWrite', db: 'cfed' },
    { role: 'dbAdmin', db: 'cfed' }
  ]
});

// 创建一些初始集合
db.createCollection('devices');
db.createCollection('configs');
db.createCollection('logs');

// 插入一些示例数据
db.devices.insertMany([
  {
    name: '设备1',
    type: 'sensor',
    status: 'active',
    lastUpdate: new Date()
  },
  {
    name: '设备2',
    type: 'controller',
    status: 'inactive',
    lastUpdate: new Date()
  }
]);

// 创建索引
db.devices.createIndex({ name: 1 }, { unique: true });
db.logs.createIndex({ timestamp: 1 });

print('MongoDB 初始化完成: 创建了cfed数据库和用户'); 