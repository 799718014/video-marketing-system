# 历史记录与模板库功能文档

## 功能概述

历史记录与模板库功能让用户能够：
- 自动保存所有生成的脚本到历史记录
- 查看、搜索、收藏和删除历史记录
- 访问系统预设模板和自定义模板
- 从模板库快速启动视频生成
- 将历史记录保存为自定义模板

---

## 后端实现

### 数据库设计

使用 SQLite 进行数据持久化，数据文件位置：`./data/history.db`

#### 表结构

**1. script_history - 脚本历史记录表**
```sql
CREATE TABLE script_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    product_name TEXT,
    brand TEXT,
    keywords TEXT,           -- JSON 数组
    style TEXT,
    duration INTEGER,
    platform TEXT,
    script_data TEXT NOT NULL, -- JSON 对象
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_favorite BOOLEAN DEFAULT 0
)
```

**2. video_history - 视频生成历史表**
```sql
CREATE TABLE video_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id INTEGER,
    task_id TEXT,
    model TEXT,
    aspect_ratio TEXT,
    status TEXT,
    video_url TEXT,
    cover_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (history_id) REFERENCES script_history (id) ON DELETE CASCADE
)
```

**3. batch_video_history - 批量视频历史表**
```sql
CREATE TABLE batch_video_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id INTEGER,
    batch_id TEXT,
    segments_count INTEGER,
    status TEXT,
    merged_video_url TEXT,
    merged_cover_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (history_id) REFERENCES script_history (id) ON DELETE CASCADE
)
```

**4. templates - 模板库表**
```sql
CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    product_name TEXT,
    keywords TEXT,           -- JSON 数组
    style TEXT,
    duration INTEGER,
    platform TEXT,
    script_data TEXT NOT NULL, -- JSON 对象
    is_system BOOLEAN DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    UNIQUE(name, category)
)
```

### API 接口

#### 历史记录 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/history/list` | 获取历史记录列表 |
| GET | `/api/history/detail/{id}` | 获取历史记录详情 |
| GET | `/api/history/search` | 搜索历史记录 |
| PUT | `/api/history/favorite/{id}` | 更新收藏状态 |
| DELETE | `/api/history/{id}` | 删除历史记录 |
| GET | `/api/history/stats` | 获取统计信息 |
| POST | `/api/history/save` | 保存到历史记录 |

#### 模板库 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/template/list` | 获取模板列表 |
| GET | `/api/template/categories` | 获取所有分类 |
| GET | `/api/template/detail/{id}` | 获取模板详情 |
| GET | `/api/template/search` | 搜索模板 |
| POST | `/api/template/create` | 创建新模板 |
| PUT | `/api/template/update/{id}` | 更新模板 |
| DELETE | `/api/template/{id}` | 删除模板 |
| POST | `/api/template/use/{id}` | 使用模板（增加计数） |
| POST | `/api/template/save-to-history/{id}` | 保存模板到历史记录 |

### 文件结构

```
backend/
├── database/
│   ├── __init__.py
│   └── db.py                 # 数据库管理类
├── routers/
│   ├── history.py            # 历史记录路由
│   └── template.py           # 模板库路由
└── main.py                   # 主应用（已更新）
```

---

## 前端实现

### 页面组件

1. **History.tsx** - 历史记录页面
   - 历史记录列表展示
   - 搜索和筛选功能
   - 收藏/取消收藏
   - 查看详情
   - 删除记录
   - 统计信息展示

2. **TemplateLibrary.tsx** - 模板库页面
   - 模板卡片展示
   - 分类筛选
   - 搜索功能
   - 查看模板详情
   - 使用模板
   - 保存到历史记录

### 类型定义

```typescript
// 历史记录
export interface ScriptHistory {
  id: number
  title: string
  product_name: string
  brand: string | null
  keywords: string[]
  style: string
  duration: number
  platform: string
  created_at: string
  is_favorite: boolean
}

// 模板
export interface Template {
  id: number
  name: string
  category: string
  description: string
  product_name: string
  keywords: string[]
  style: string
  duration: number
  platform: string
  is_system: boolean
  created_by: string | null
  created_at: string
  usage_count: number
}
```

### 导航

新增顶部导航，支持三个页面切换：
- 视频生成
- 历史记录 (🕐)
- 模板库 (📋)

---

## 系统预设模板

首次启动时自动初始化以下系统模板：

| 模板名称 | 分类 | 风格 | 时长 | 平台 | 描述 |
|---------|------|------|------|------|------|
| 抖音爆款产品展示 | 产品展示 | 活力 | 15秒 | 抖音 | 适用于抖音平台的爆款产品展示视频脚本模板 |
| 小红书生活分享 | 生活分享 | 温情 | 30秒 | 小红书 | 适用于小红书平台的生活分享视频脚本模板 |
| 企业品牌宣传 | 品牌宣传 | 专业 | 60秒 | 企业官网 | 适用于企业品牌宣传的专业视频脚本模板 |
| 电商促销活动 | 电商营销 | 搞笑 | 30秒 | 淘宝 | 适用于电商促销活动的搞笑视频脚本模板 |
| 美妆产品展示 | 美妆时尚 | 活力 | 30秒 | 抖音 | 适用于美妆产品的专业展示视频脚本模板 |

---

## 使用说明

### 历史记录功能

1. 脚本生成成功后自动保存到历史记录
2. 点击顶部"历史记录"进入历史记录页面
3. 支持按标题、产品名称、关键词搜索
4. 点击"⭐"图标收藏/取消收藏
5. 点击"查看"按钮查看脚本详情
6. 点击"删除"按钮删除历史记录

### 模板库功能

1. 点击顶部"模板库"进入模板库页面
2. 浏览系统预设模板和自定义模板
3. 使用分类筛选或搜索找到合适的模板
4. 点击模板卡片查看详情
5. 点击"使用此模板"将模板应用到视频生成
6. 点击"保存到历史"将模板保存到历史记录

### 创建自定义模板

1. 先生成一个脚本
2. 在历史记录中找到该脚本
3. 点击"创建模板"按钮（开发中）
4. 填写模板名称和分类
5. 保存到模板库

---

## 后续优化建议

### 功能增强
- [ ] 支持将历史记录直接生成视频
- [ ] 支持批量操作（批量删除、批量收藏）
- [ ] 添加导出功能（导出脚本为文本/PDF）
- [ ] 添加分享功能（分享脚本链接）
- [ ] 支持标签系统，方便分类管理

### 性能优化
- [ ] 添加分页加载
- [ ] 添加缓存机制
- [ ] 优化大量数据时的渲染性能

### 用户体验
- [ ] 添加拖拽排序功能
- [ ] 添加快速预览功能
- [ ] 支持模板预览视频
- [ ] 添加收藏夹页面