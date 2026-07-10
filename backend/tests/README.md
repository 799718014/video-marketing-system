# 长视频分段拼接功能测试文档

## 测试文件结构

```
backend/tests/
├── __init__.py           # 测试包初始化
├── test_batch_video.py   # 核心功能单元测试
├── test_batch_video_api.py # API接口集成测试
├── FEATURE_GAPS.md       # 功能缺失分析报告
└── README.md             # 本文件
```

## 运行测试

### 安装测试依赖

```bash
pip install -r requirements-test.txt
```

### 运行所有测试

```bash
# 基础运行
pytest tests/

# 带覆盖率报告
pytest tests/ --cov=services/batch_video_service --cov=utils/video_merge --cov-report=html

# 只运行单元测试
pytest tests/ -m unit

# 只运行API测试
pytest tests/ -m api

# 显示详细输出
pytest tests/ -v --tb=short
```

### 运行单个测试文件

```bash
pytest tests/test_batch_video.py
pytest tests/test_batch_video_api.py
```

### 运行特定测试类或方法

```bash
pytest tests/test_batch_video.py::TestScriptSplitting::test_split_by_scene_boundary
pytest tests/test_batch_video.py::TestScriptSplitting -v
```

## 测试覆盖范围

### 单元测试 (test_batch_video.py)

| 测试类 | 测试内容 | 用例数 |
|--------|---------|-------|
| TestScriptSplitting | 脚本分段算法 | 4 |
| TestSegmentGeneration | 片段生成 | 3 |
| TestBatchTaskManagement | 任务管理 | 2 |
| TestVideoMerge | 视频合并 | 2 |
| TestBatchVideoIntegration | 集成测试 | 1 |
| TestEdgeCasesAndErrors | 边界和错误 | 2 |

### API测试 (test_batch_video_api.py)

| 测试类 | 测试内容 | 用例数 |
|--------|---------|-------|
| TestCreateBatchTask | 创建任务API | 2 |
| TestGetBatchStatus | 查询状态API | 3 |
| TestCheckMergeStatus | 检查合并API | 2 |
| TestRetryFailedSegments | 重试API | 2 |
| TestCancelBatch | 取消API | 2 |
| TestDownloadEndpoints | 下载API | 3 |
| TestParameterValidation | 参数验证 | 3 |
| TestConcurrentRequests | 并发测试 | 1 |

### 前端测试 (api.test.ts)

| 测试组 | 测试内容 | 用例数 |
|--------|---------|-------|
| createBatchVideo | 创建任务 | 2 |
| getBatchStatus | 查询状态 | 2 |
| checkMergeStatus | 检查合并 | 1 |
| retryBatchSegments | 重试 | 2 |
| 下载URL生成 | URL生成 | 2 |
| 轮询逻辑 | 进度计算 | 2 |
| 数据类型验证 | 类型检查 | 2 |

## 测试用例详情

### 脚本分段测试

1. **按场景边界分段** - 验证多个场景独立分段
2. **单个长场景拆分** - 验证超长场景自动切分
3. **混合场景分段** - 验证短长场景混合处理
4. **边界情况** - 空场景、精确等于边界等

### 片段生成测试

1. **单个片段成功** - 验证正常流程
2. **失败重试** - 验证重试机制和指数退避
3. **并发控制** - 验证并发数限制

### 任务管理测试

1. **任务保存和获取** - 验证内存存储
2. **状态转换** - 验证submitted→processing→merging流程

### API接口测试

1. **创建任务** - 正常创建、长场景处理
2. **查询状态** - 正常查询、不存在任务、混合状态
3. **重试** - 正常重试、错误状态
4. **取消** - 全部取消、部分完成取消
5. **下载** - 未完成下载、片段下载
6. **参数验证** - 无效宽高比、负数并发
7. **并发请求** - 多请求同时查询

## 测试标记

- `@pytest.mark.asyncio` - 异步测试
- `@pytest.mark.slow` - 慢速测试（需要网络或大量计算）
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.unit` - 单元测试

## 已修复的问题

1. ✅ 删除了 `batch_video.py` 中重复的 `retry_segments` 函数定义
2. ✅ 补充了完整的测试用例
3. ✅ 创建了功能缺失分析文档

## 后续工作

### P0 - 立即修复

- [ ] 添加音频拼接功能
- [ ] 实现任务持久化（数据库）
- [ ] 补充帧率和分辨率统一处理

### P1 - 近期补充

- [ ] 添加进度百分比字段
- [ ] 增强临时文件清理机制
- [ ] 补充端到端测试

### P2 - 后续优化

- [ ] WebSocket 实时进度推送
- [ ] 更多转场效果
- [ ] 任务优先级队列

## 注意事项

1. 当前测试依赖 mock，真实环境需要集成测试
2. 视频合并测试需要真实视频文件或更完善的mock
3. 并发测试建议在独立环境运行
4. 覆盖率报告生成在 `htmlcov/` 目录