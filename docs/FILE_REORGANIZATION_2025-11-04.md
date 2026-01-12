# 项目文件结构整理记录

**日期**: 2025-11-04
**任务**: 对项目所有文件进行归类整理

## 整理原则

遵循Linus的三个核心问题：
1. **这是真实问题吗？** → 是的，项目根目录混乱，需要清理
2. **有更简单的方法吗？** → 按功能分类，移动到对应目录
3. **会破坏什么吗？** → 不会，只是移动文件位置，不改变功能

## 执行的操作

### 1. 移动Docker管理脚本
- `docker-up.sh` → `scripts/docker-up.sh`
- `docker-down.sh` → `scripts/docker-down.sh`

**原因**: 这两个是Docker快捷管理脚本，应与其他运维脚本统一放在scripts/目录

### 2. 删除冗余配置文件
- 删除根目录的 `filter_config.json`

**原因**: `backend/filter_config.json` 包含更完整的配置（包含多个过滤器），根目录的版本已过时

### 3. 保留在根目录的文件
以下文件应保留在根目录（符合项目规范）：
- `.env` - 环境变量配置
- `.env.example` - 环境变量模板
- `.gitignore` - Git忽略规则
- `README.md` - 项目说明

## 最终目录结构

```
Task_feishu/
├── archive/          # 归档的旧代码和部署配置
├── backend/          # 后端Python代码
├── backup/           # 数据备份
├── data/             # 数据文件
├── docker/           # Docker配置文件
│   ├── docker-compose.yml
│   ├── docker-compose.mysql.yml
│   ├── docker-compose.frontend.yml
│   └── nginx/        # Nginx配置
├── docs/             # 项目文档
├── frontend/         # 前端React代码
├── scripts/          # 运维脚本
│   ├── docker-up.sh     ✅ 新增
│   ├── docker-down.sh   ✅ 新增
│   ├── deploy.sh
│   └── ...
├── tests/            # 测试文件
├── .env              # 环境配置
├── .env.example      # 环境配置模板
├── .gitignore        # Git配置
└── README.md         # 项目说明
```

## 效果评估

### ✅ 优点
1. **根目录清爽**: 只保留必要的配置文件
2. **分类清晰**: 所有文件按功能归类
3. **易于维护**: 开发者可以快速找到所需文件

### ⚠️ 注意事项
1. 如果有脚本引用了根目录的 `docker-up.sh` 或 `docker-down.sh`，需要更新路径为 `scripts/docker-up.sh`
2. 删除了根目录的 `filter_config.json`，所有配置应使用 `backend/filter_config.json`

## Git状态

已暂存的变更包括：
- 82个文件重命名/移动（deploy→archive, 根目录→docker/docs/scripts/tests）
- 2个新增脚本（scripts/docker-up.sh, scripts/docker-down.sh）
- 1个删除文件（filter_config.json）

## 后续建议

1. **创建README**: 在各子目录添加README说明目录用途
2. **更新文档**: 确保所有文档中的路径引用正确
3. **CI/CD检查**: 如有CI/CD流程，确认路径变更不影响构建

---

**整理完成时间**: 2025-11-04 10:08
