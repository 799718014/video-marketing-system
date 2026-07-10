"""
历史记录与模板库 API 接口测试

测试范围:
1. 历史记录API (history路由)
2. 模板库API (template路由)
3. 参数验证
4. 错误处理
5. 集成测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app
from database.db import Database

client = TestClient(app)


# ==================== Fixtures ====================

@pytest.fixture
def clean_db():
    """清理测试数据库"""
    db = Database()
    # 使用临时数据库路径进行测试
    import tempfile
    import os
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_path = temp_file.name
    temp_file.close()

    # 替换全局db
    import database.db as db_module
    original_db = db_module.db
    db_module.db = Database(db_path=temp_path)
    db_module.db.init_system_templates()

    yield db_module.db

    # 恢复原始db
    db_module.db = original_db

    # 清理
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_script_data():
    """示例脚本数据"""
    return {
        'title': '测试产品视频',
        'total_duration': 30,
        'style': '活力',
        'scenes': [
            {
                'scene_no': 1,
                'duration': 5,
                'visual': '产品展示',
                'narration': '旁白',
                'subtitle': '字幕'
            }
        ],
        'full_prompt': '测试提示词'
    }


@pytest.fixture
def sample_product_info():
    """示例产品信息"""
    return {
        'name': '测试产品',
        'brand': '测试品牌',
        'keywords': ['关键词1', '关键词2'],
        'price': '99.99',
        'description': '产品描述',
        'features': ['功能1', '功能2'],
        'target_audience': '目标用户'
    }


# ==================== 测试 1: 历史记录API ====================

class TestHistoryAPI:
    """测试历史记录API"""

    def test_get_history_list_empty(self, clean_db):
        """测试获取空的历史记录列表"""
        response = client.get("/api/history/list")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_history_list_with_limit(self, clean_db):
        """测试带limit参数的历史记录列表"""
        # 先保存一些数据
        clean_db.save_script_history(
            title='测试1',
            script_data={'title': '测试1', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        clean_db.save_script_history(
            title='测试2',
            script_data={'title': '测试2', 'scenes': []},
            product_info={'name': '产品2', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        response = client.get("/api/history/list?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_history_list_favorite_only(self, clean_db):
        """测试只获取收藏的历史记录"""
        # 保存一条收藏和一条未收藏
        clean_db.save_script_history(
            title='收藏的脚本',
            script_data={'title': '收藏的脚本', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=True
        )

        clean_db.save_script_history(
            title='未收藏的脚本',
            script_data={'title': '未收藏的脚本', 'scenes': []},
            product_info={'name': '产品2', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        response = client.get("/api/history/list?favorite_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['title'] == '收藏的脚本'
        assert data[0]['is_favorite'] == True

    def test_get_history_detail_success(self, clean_db):
        """测试获取历史记录详情"""
        history_id = clean_db.save_script_history(
            title='测试脚本',
            script_data={'title': '测试脚本', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        response = client.get(f"/api/history/detail/{history_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == history_id
        assert data['title'] == '测试脚本'
        assert 'script_data' in data

    def test_get_history_detail_not_found(self, clean_db):
        """测试获取不存在的历史记录详情"""
        response = client.get("/api/history/detail/999999")
        assert response.status_code == 404
        assert "不存在" in response.json()['detail']

    def test_search_history(self, clean_db):
        """测试搜索历史记录"""
        clean_db.save_script_history(
            title='抖音爆款产品',
            script_data={'title': '抖音爆款产品', 'scenes': []},
            product_info={'name': '抖音爆款产品', 'keywords': ['抖音', '爆款'], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        clean_db.save_script_history(
            title='小红书生活',
            script_data={'title': '小红书生活', 'scenes': []},
            product_info={'name': '小红书生活', 'keywords': ['小红书'], 'style': '温情', 'duration': 30, 'platform': '小红书'},
            style='温情',
            duration=30,
            platform='小红书',
            is_favorite=False
        )

        response = client.get("/api/history/search?keyword=抖音")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any('抖音' in item['title'] or '抖音' in item['product_name'] or '抖音' in str(item['keywords']) for item in data)

    def test_update_favorite_true(self, clean_db):
        """测试设置为收藏"""
        history_id = clean_db.save_script_history(
            title='测试脚本',
            script_data={'title': '测试脚本', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        response = client.put(f"/api/history/favorite/{history_id}", json={"is_favorite": True})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['is_favorite'] == True

    def test_update_favorite_false(self, clean_db):
        """测试取消收藏"""
        history_id = clean_db.save_script_history(
            title='测试脚本',
            script_data={'title': '测试脚本', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=True
        )

        response = client.put(f"/api/history/favorite/{history_id}", json={"is_favorite": False})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['is_favorite'] == False

    def test_update_favorite_not_found(self, clean_db):
        """测试更新不存在记录的收藏状态"""
        response = client.put("/api/history/favorite/999999", json={"is_favorite": True})
        assert response.status_code == 404

    def test_delete_history_success(self, clean_db):
        """测试删除历史记录"""
        history_id = clean_db.save_script_history(
            title='待删除脚本',
            script_data={'title': '待删除脚本', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        response = client.delete(f"/api/history/{history_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

        # 验证已删除
        response = client.get(f"/api/history/detail/{history_id}")
        assert response.status_code == 404

    def test_delete_history_not_found(self, clean_db):
        """测试删除不存在的历史记录"""
        response = client.delete("/api/history/999999")
        assert response.status_code == 404

    def test_get_history_stats(self, clean_db):
        """测试获取历史记录统计信息"""
        clean_db.save_script_history(
            title='测试1',
            script_data={'title': '测试1', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=True
        )

        clean_db.save_script_history(
            title='测试2',
            script_data={'title': '测试2', 'scenes': []},
            product_info={'name': '产品2', 'keywords': [], 'style': '专业', 'duration': 30, 'platform': '小红书'},
            style='专业',
            duration=30,
            platform='小红书',
            is_favorite=False
        )

        response = client.get("/api/history/stats")
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 2
        assert data['favorite_count'] == 1
        assert '活力' in data['style_stats']
        assert '专业' in data['style_stats']
        assert '抖音' in data['platform_stats']
        assert '小红书' in data['platform_stats']

    def test_save_history(self, clean_db, sample_script_data, sample_product_info):
        """测试保存历史记录"""
        response = client.post("/api/history/save", json={
            "title": "新脚本",
            "script_data": sample_script_data,
            "product_info": sample_product_info,
            "style": "活力",
            "duration": 30,
            "platform": "抖音",
            "is_favorite": False
        })

        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['success'] == True


# ==================== 测试 2: 模板库API ====================

class TestTemplateAPI:
    """测试模板库API"""

    def test_get_template_list(self, clean_db):
        """测试获取模板列表"""
        response = client.get("/api/template/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5  # 至少5个系统模板

    def test_get_template_list_with_category(self, clean_db):
        """测试按分类获取模板"""
        response = client.get("/api/template/list?category=产品展示")
        assert response.status_code == 200
        data = response.json()
        assert all(item['category'] == '产品展示' for item in data)

    def test_get_template_list_system_only(self, clean_db):
        """测试只获取系统模板"""
        response = client.get("/api/template/list?is_system=true")
        assert response.status_code == 200
        data = response.json()
        assert all(item['is_system'] for item in data)

    def test_get_template_categories(self, clean_db):
        """测试获取模板分类"""
        response = client.get("/api/template/categories")
        assert response.status_code == 200
        data = response.json()
        assert 'categories' in data
        assert len(data['categories']) > 0
        expected_categories = ['产品展示', '生活分享', '品牌宣传', '电商营销', '美妆时尚']
        for cat in expected_categories:
            assert cat in data['categories']

    def test_get_template_detail_success(self, clean_db):
        """测试获取模板详情"""
        templates = clean_db.get_templates()
        if templates:
            template_id = templates[0]['id']

            response = client.get(f"/api/template/detail/{template_id}")
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == template_id
            assert 'script_data' in data

    def test_get_template_detail_not_found(self, clean_db):
        """测试获取不存在的模板详情"""
        response = client.get("/api/template/detail/999999")
        assert response.status_code == 404
        assert "不存在" in response.json()['detail']

    def test_search_templates(self, clean_db):
        """测试搜索模板"""
        response = client.get("/api/template/search?keyword=抖音")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_search_templates_with_category(self, clean_db):
        """测试带分类的搜索"""
        response = client.get("/api/template/search?keyword=展示&category=产品展示")
        assert response.status_code == 200
        data = response.json()
        assert all(item['category'] == '产品展示' for item in data)

    def test_create_template_success(self, clean_db):
        """测试创建模板"""
        response = client.post("/api/template/create", json={
            "name": "自定义模板",
            "category": "测试分类",
            "description": "测试描述",
            "product_name": "测试产品",
            "keywords": ["关键词1", "关键词2"],
            "style": "活力",
            "duration": 30,
            "platform": "抖音",
            "script_data": {
                "title": "测试",
                "total_duration": 30,
                "style": "活力",
                "scenes": [],
                "full_prompt": "测试"
            }
        })

        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['success'] == True

    def test_update_template_success(self, clean_db):
        """测试更新模板"""
        # 先创建一个模板
        template_id = clean_db.save_template(
            name='原始名称',
            category='测试',
            description='原始描述',
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            script_data={'title': '测试', 'scenes': []},
            is_system=False,
            created_by='user'
        )

        # 更新名称
        response = client.put(f"/api/template/update/{template_id}", json={
            "name": "新名称"
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

    def test_update_template_not_found(self, clean_db):
        """测试更新不存在的模板"""
        response = client.put("/api/template/update/999999", json={"name": "新名称"})
        assert response.status_code == 404

    def test_delete_template_success(self, clean_db):
        """测试删除模板"""
        # 先创建一个用户模板
        template_id = clean_db.save_template(
            name='待删除模板',
            category='测试',
            description='测试',
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            script_data={'title': '测试', 'scenes': []},
            is_system=False,
            created_by='user'
        )

        response = client.delete(f"/api/template/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

    def test_delete_system_template(self, clean_db):
        """测试系统模板不可删除"""
        system_templates = clean_db.get_templates(is_system=True)
        if system_templates:
            template_id = system_templates[0]['id']

            response = client.delete(f"/api/template/{template_id}")
            assert response.status_code == 404  # 系统模板被视为不存在或不可删除

    def test_use_template_success(self, clean_db):
        """测试使用模板"""
        # 先创建一个模板
        template_id = clean_db.save_template(
            name='测试模板',
            category='测试',
            description='测试',
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            script_data={'title': '测试', 'scenes': []},
            is_system=False,
            created_by='user'
        )

        # 获取初始使用计数
        template = clean_db.get_template_detail(template_id)
        initial_count = template['usage_count']

        # 使用模板
        response = client.post(f"/api/template/use/{template_id}")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

        # 验证计数增加
        template = clean_db.get_template_detail(template_id)
        assert template['usage_count'] == initial_count + 1

    def test_use_template_not_found(self, clean_db):
        """测试使用不存在的模板"""
        response = client.post("/api/template/use/999999")
        assert response.status_code == 404

    def test_save_template_to_history(self, clean_db):
        """测试保存模板到历史记录"""
        # 先创建一个模板
        template_id = clean_db.save_template(
            name='测试模板',
            category='测试',
            description='测试',
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            script_data={'title': '测试', 'scenes': []},
            is_system=False,
            created_by='user'
        )

        # 保存到历史记录
        response = client.post(f"/api/template/save-to-history/{template_id}", params={
            "title": "从模板创建的脚本",
            "is_favorite": False
        })

        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['success'] == True


# ==================== 测试 3: 参数验证 ====================

class TestParameterValidation:
    """测试参数验证"""

    def test_history_list_invalid_limit(self, clean_db):
        """测试无效的limit参数"""
        response = client.get("/api/history/list?limit=-1")
        # 应该返回200但返回空列表
        assert response.status_code in [200, 422]

    def test_history_list_invalid_offset(self, clean_db):
        """测试无效的offset参数"""
        response = client.get("/api/history/list?offset=-1")
        assert response.status_code in [200, 422]

    def test_template_list_invalid_limit(self, clean_db):
        """测试模板列表的无效limit参数"""
        response = client.get("/api/template/list?limit=abc")
        assert response.status_code in [200, 422]

    def test_search_empty_keyword(self, clean_db):
        """测试空关键词搜索"""
        response = client.get("/api/history/search?keyword=")
        assert response.status_code == 200

    def test_create_template_missing_fields(self, clean_db):
        """测试创建模板缺少字段"""
        response = client.post("/api/template/create", json={
            "name": "测试"
        })
        # Pydantic验证应该返回422
        assert response.status_code == 422


# ==================== 测试 4: 并发请求 ====================

class TestConcurrentRequests:
    """测试并发请求"""

    def test_concurrent_history_requests(self, clean_db):
        """测试并发获取历史记录"""
        import threading

        results = []

        def get_history():
            response = client.get("/api/history/list")
            results.append(response.status_code)

        threads = [threading.Thread(target=get_history) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有请求都应该成功
        assert all(status == 200 for status in results)

    def test_concurrent_template_requests(self, clean_db):
        """测试并发获取模板列表"""
        import threading

        results = []

        def get_templates():
            response = client.get("/api/template/list")
            results.append(response.status_code)

        threads = [threading.Thread(target=get_templates) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(status == 200 for status in results)


# ==================== 测试 5: 集成测试 ====================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, clean_db):
        """测试完整工作流：保存历史 → 搜索 → 收藏 → 创建模板"""
        # 1. 保存脚本到历史
        history_id = clean_db.save_script_history(
            title='工作流测试',
            script_data={'title': '工作流测试', 'scenes': []},
            product_info={'name': '产品', 'keywords': ['关键词'], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        assert history_id > 0

        # 2. 通过API获取历史列表
        response = client.get("/api/history/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        # 3. 搜索历史记录
        response = client.get("/api/history/search?keyword=工作流")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        # 4. 收藏历史记录
        response = client.put(f"/api/history/favorite/{history_id}", json={"is_favorite": True})
        assert response.status_code == 200

        # 5. 创建模板
        response = client.post("/api/template/create", json={
            "name": "从历史创建的模板",
            "category": "测试",
            "description": "从历史记录创建",
            "product_name": "产品",
            "keywords": ["关键词"],
            "style": "活力",
            "duration": 30,
            "platform": "抖音",
            "script_data": {
                "title": "工作流测试",
                "total_duration": 30,
                "style": "活力",
                "scenes": [],
                "full_prompt": "测试"
            }
        })
        assert response.status_code == 200
        template_id = response.json()['id']

        # 6. 使用模板
        response = client.post(f"/api/template/use/{template_id}")
        assert response.status_code == 200

        # 7. 保存模板到历史记录
        response = client.post(f"/api/template/save-to-history/{template_id}", params={
            "title": "从模板再次创建",
            "is_favorite": False
        })
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])