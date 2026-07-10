"""
历史记录与模板库功能测试用例

测试范围:
1. 数据库操作 (Database类)
2. 历史记录API
3. 模板库API
4. 系统模板初始化
5. 边界条件和错误处理
"""
import pytest
import tempfile
import os
from datetime import datetime
from database.db import Database


# ==================== 测试配置 ====================

@pytest.fixture
def temp_db():
    """创建临时测试数据库"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_path = temp_file.name
    temp_file.close()

    db = Database(db_path=temp_path)
    db.init_system_templates()  # 初始化系统模板

    yield db

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
                'visual': '产品展示场景1',
                'narration': '旁白1',
                'subtitle': '字幕1'
            },
            {
                'scene_no': 2,
                'duration': 5,
                'visual': '产品展示场景2',
                'narration': '旁白2',
                'subtitle': '字幕2'
            }
        ],
        'full_prompt': '测试产品视频提示词'
    }


@pytest.fixture
def sample_product_info():
    """示例产品信息"""
    return {
        'name': '测试产品',
        'keywords': ['测试', '产品', '视频'],
        'style': '活力',
        'duration': 30,
        'platform': '抖音'
    }


# ==================== 测试 1: 数据库初始化 ====================

class TestDatabaseInit:
    """测试数据库初始化"""

    def test_tables_created(self, temp_db):
        """验证所有表都被创建"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            tables = [
                'script_history',
                'video_history',
                'batch_video_history',
                'templates'
            ]

            for table in tables:
                cursor.execute(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table}'
                """)
                result = cursor.fetchone()
                assert result is not None, f"表 {table} 未创建"

    def test_system_templates_initialized(self, temp_db):
        """验证系统模板被初始化"""
        templates = temp_db.get_templates(is_system=True)
        assert len(templates) == 5, "应该有5个系统模板"

        # 验证模板分类
        categories = temp_db.get_template_categories()
        expected_categories = ['产品展示', '生活分享', '品牌宣传', '电商营销', '美妆时尚']
        for cat in expected_categories:
            assert cat in categories, f"缺少分类: {cat}"

    def test_indexes_created(self, temp_db):
        """验证索引被创建"""
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='script_history'
            """)
            indexes = [row['name'] for row in cursor.fetchall()]
            assert 'idx_history_created' in indexes


# ==================== 测试 2: 历史记录功能 ====================

class TestScriptHistory:
    """测试脚本历史记录功能"""

    def test_save_script_history(self, temp_db, sample_script_data, sample_product_info):
        """测试保存脚本历史记录"""
        history_id = temp_db.save_script_history(
            title=sample_script_data['title'],
            script_data=sample_script_data,
            product_info=sample_product_info,
            style=sample_product_info['style'],
            duration=sample_product_info['duration'],
            platform=sample_product_info['platform'],
            is_favorite=False
        )

        assert history_id > 0, "应该返回有效的历史记录ID"

        # 验证数据被保存
        history = temp_db.get_script_detail(history_id)
        assert history is not None
        assert history['title'] == sample_script_data['title']
        assert history['product_name'] == sample_product_info['name']
        assert history['style'] == sample_product_info['style']
        assert history['is_favorite'] == False

    def test_save_with_favorite(self, temp_db, sample_script_data, sample_product_info):
        """测试保存收藏的脚本"""
        history_id = temp_db.save_script_history(
            title=sample_script_data['title'],
            script_data=sample_script_data,
            product_info=sample_product_info,
            style=sample_product_info['style'],
            duration=sample_product_info['duration'],
            platform=sample_product_info['platform'],
            is_favorite=True
        )

        history = temp_db.get_script_detail(history_id)
        assert history['is_favorite'] == True

    def test_get_script_history_list(self, temp_db, sample_script_data, sample_product_info):
        """测试获取历史记录列表"""
        # 保存多条记录
        for i in range(5):
            temp_db.save_script_history(
                title=f'测试脚本{i}',
                script_data=sample_script_data,
                product_info=sample_product_info,
                style=sample_product_info['style'],
                duration=sample_product_info['duration'],
                platform=sample_product_info['platform'],
                is_favorite=(i % 2 == 0)  # 偶数收藏
            )

        # 获取全部记录
        histories = temp_db.get_script_history(limit=20)
        assert len(histories) == 5

        # 只获取收藏的
        favorites = temp_db.get_script_history(favorite_only=True, limit=20)
        assert len(favorites) == 3  # 0, 2, 4

    def test_get_script_history_with_pagination(self, temp_db, sample_script_data, sample_product_info):
        """测试分页获取历史记录"""
        # 保存10条记录
        for i in range(10):
            temp_db.save_script_history(
                title=f'测试脚本{i}',
                script_data=sample_script_data,
                product_info=sample_product_info,
                style=sample_product_info['style'],
                duration=sample_product_info['duration'],
                platform=sample_product_info['platform'],
                is_favorite=False
            )

        # 第一页
        page1 = temp_db.get_script_history(limit=5, offset=0)
        assert len(page1) == 5

        # 第二页
        page2 = temp_db.get_script_history(limit=5, offset=5)
        assert len(page2) == 5

        # 验证顺序（最新在前）
        assert page1[0]['title'] == '测试脚本9'

    def test_get_script_detail(self, temp_db, sample_script_data, sample_product_info):
        """测试获取历史记录详情"""
        history_id = temp_db.save_script_history(
            title=sample_script_data['title'],
            script_data=sample_script_data,
            product_info=sample_product_info,
            style=sample_product_info['style'],
            duration=sample_product_info['duration'],
            platform=sample_product_info['platform'],
            is_favorite=False
        )

        detail = temp_db.get_script_detail(history_id)
        assert detail is not None
        assert detail['id'] == history_id
        assert detail['script_data'] == sample_script_data

    def test_get_nonexistent_history(self, temp_db):
        """测试获取不存在的历史记录"""
        detail = temp_db.get_script_detail(999999)
        assert detail is None

    def test_update_favorite(self, temp_db, sample_script_data, sample_product_info):
        """测试更新收藏状态"""
        history_id = temp_db.save_script_history(
            title=sample_script_data['title'],
            script_data=sample_script_data,
            product_info=sample_product_info,
            style=sample_product_info['style'],
            duration=sample_product_info['duration'],
            platform=sample_product_info['platform'],
            is_favorite=False
        )

        # 设置为收藏
        success = temp_db.update_favorite(history_id, True)
        assert success == True

        detail = temp_db.get_script_detail(history_id)
        assert detail['is_favorite'] == True

        # 取消收藏
        success = temp_db.update_favorite(history_id, False)
        assert success == True

        detail = temp_db.get_script_detail(history_id)
        assert detail['is_favorite'] == False

    def test_delete_script_history(self, temp_db, sample_script_data, sample_product_info):
        """测试删除历史记录"""
        history_id = temp_db.save_script_history(
            title=sample_script_data['title'],
            script_data=sample_script_data,
            product_info=sample_product_info,
            style=sample_product_info['style'],
            duration=sample_product_info['duration'],
            platform=sample_product_info['platform'],
            is_favorite=False
        )

        # 验证记录存在
        detail = temp_db.get_script_detail(history_id)
        assert detail is not None

        # 删除记录
        success = temp_db.delete_script_history(history_id)
        assert success == True

        # 验证记录已删除
        detail = temp_db.get_script_detail(history_id)
        assert detail is None

    def test_delete_nonexistent_history(self, temp_db):
        """测试删除不存在的历史记录"""
        success = temp_db.delete_script_history(999999)
        assert success == False

    def test_search_history(self, temp_db, sample_script_data, sample_product_info):
        """测试搜索历史记录"""
        # 保存多条记录
        titles = ['抖音爆款', '小红书分享', '企业宣传', '电商促销', '美妆展示']
        for title in titles:
            temp_db.save_script_history(
                title=title,
                script_data=sample_script_data,
                product_info={**sample_product_info, 'name': title},
                style=sample_product_info['style'],
                duration=sample_product_info['duration'],
                platform=sample_product_info['platform'],
                is_favorite=False
            )

        # 搜索抖音
        results = temp_db.search_history('抖音')
        assert len(results) == 1
        assert '抖音' in results[0]['title']

        # 搜索产品
        results = temp_db.search_history('爆款')
        assert len(results) == 1

        # 搜索关键词
        temp_db.save_script_history(
            title='测试',
            script_data=sample_script_data,
            product_info={**sample_product_info, 'keywords': ['测试', '关键词']},
            style=sample_product_info['style'],
            duration=sample_product_info['duration'],
            platform=sample_product_info['platform'],
            is_favorite=False
        )

        results = temp_db.search_history('关键词')
        assert len(results) > 0

    def test_get_history_stats(self, temp_db, sample_script_data, sample_product_info):
        """测试获取历史记录统计信息"""
        # 保存多条记录
        styles = ['活力', '专业', '温情', '活力']
        platforms = ['抖音', '小红书', '企业官网', '抖音']

        for i, (style, platform) in enumerate(zip(styles, platforms)):
            temp_db.save_script_history(
                title=f'测试{i}',
                script_data=sample_script_data,
                product_info=sample_product_info,
                style=style,
                duration=sample_product_info['duration'],
                platform=platform,
                is_favorite=(i == 0 or i == 2)  # 收藏第1和第3条
            )

        stats = temp_db.get_history_stats()

        assert stats['total'] == 4
        assert stats['favorite_count'] == 2
        assert stats['style_stats']['活力'] == 2
        assert stats['style_stats']['专业'] == 1
        assert stats['style_stats']['温情'] == 1
        assert stats['platform_stats']['抖音'] == 2
        assert stats['platform_stats']['小红书'] == 1
        assert stats['platform_stats']['企业官网'] == 1

    def test_empty_history_stats(self, temp_db):
        """测试空历史记录的统计信息"""
        stats = temp_db.get_history_stats()
        assert stats['total'] == 0
        assert stats['favorite_count'] == 0
        assert stats['style_stats'] == {}
        assert stats['platform_stats'] == {}


# ==================== 测试 3: 模板库功能 ====================

class TestTemplateLibrary:
    """测试模板库功能"""

    def test_get_all_templates(self, temp_db):
        """测试获取所有模板"""
        templates = temp_db.get_templates()
        assert len(templates) >= 5  # 至少5个系统模板

    def test_get_templates_by_category(self, temp_db):
        """测试按分类获取模板"""
        templates = temp_db.get_templates(category='产品展示')
        assert all(t['category'] == '产品展示' for t in templates)

    def test_get_system_templates_only(self, temp_db):
        """测试只获取系统模板"""
        system_templates = temp_db.get_templates(is_system=True)
        assert all(t['is_system'] for t in system_templates)

    def test_get_user_templates_only(self, temp_db):
        """测试只获取用户模板"""
        # 先创建一个用户模板
        temp_db.save_template(
            name='用户自定义模板',
            category='自定义',
            description='用户创建的模板',
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            script_data={'title': '测试', 'scenes': []},
            is_system=False,
            created_by='user'
        )

        user_templates = temp_db.get_templates(is_system=False)
        assert all(not t['is_system'] for t in user_templates)
        assert any('用户自定义' in t['name'] for t in user_templates)

    def test_get_template_detail(self, temp_db):
        """测试获取模板详情"""
        templates = temp_db.get_templates(is_system=True)
        if templates:
            template_id = templates[0]['id']
            detail = temp_db.get_template_detail(template_id)

            assert detail is not None
            assert detail['id'] == template_id
            assert 'script_data' in detail
            assert 'scenes' in detail['script_data']

    def test_get_nonexistent_template(self, temp_db):
        """测试获取不存在的模板"""
        detail = temp_db.get_template_detail(999999)
        assert detail is None

    def test_create_custom_template(self, temp_db, sample_script_data, sample_product_info):
        """测试创建自定义模板"""
        template_id = temp_db.save_template(
            name='我的模板',
            category='自定义',
            description='自定义模板描述',
            product_info=sample_product_info,
            script_data=sample_script_data,
            is_system=False,
            created_by='test_user'
        )

        assert template_id > 0

        # 验证模板被创建
        template = temp_db.get_template_detail(template_id)
        assert template is not None
        assert template['name'] == '我的模板'
        assert template['is_system'] == False
        assert template['created_by'] == 'test_user'
        assert template['usage_count'] == 0

    def test_duplicate_template_name(self, temp_db, sample_script_data, sample_product_info):
        """测试创建重复名称的模板（同一分类下）"""
        temp_db.save_template(
            name='重复名称',
            category='测试',
            description='第一个模板',
            product_info=sample_product_info,
            script_data=sample_script_data,
            is_system=False,
            created_by='user'
        )

        # 尝试创建同名同分类模板（应该失败）
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            temp_db.save_template(
                name='重复名称',
                category='测试',
                description='第二个模板',
                product_info=sample_product_info,
                script_data=sample_script_data,
                is_system=False,
                created_by='user'
            )

    def test_update_template(self, temp_db, sample_script_data, sample_product_info):
        """测试更新模板"""
        template_id = temp_db.save_template(
            name='原始名称',
            category='测试',
            description='原始描述',
            product_info=sample_product_info,
            script_data=sample_script_data,
            is_system=False,
            created_by='user'
        )

        # 更新名称
        success = temp_db.update_template(
            template_id=template_id,
            name='新名称'
        )
        assert success == True

        # 验证更新
        template = temp_db.get_template_detail(template_id)
        assert template['name'] == '新名称'

        # 更新描述
        success = temp_db.update_template(
            template_id=template_id,
            description='新描述'
        )
        assert success == True

        template = temp_db.get_template_detail(template_id)
        assert template['description'] == '新描述'

    def test_update_nonexistent_template(self, temp_db):
        """测试更新不存在的模板"""
        success = temp_db.update_template(
            template_id=999999,
            name='新名称'
        )
        assert success == False

    def test_delete_template(self, temp_db, sample_script_data, sample_product_info):
        """测试删除模板"""
        template_id = temp_db.save_template(
            name='待删除模板',
            category='测试',
            description='测试模板',
            product_info=sample_product_info,
            script_data=sample_script_data,
            is_system=False,
            created_by='user'
        )

        # 验证模板存在
        template = temp_db.get_template_detail(template_id)
        assert template is not None

        # 删除模板
        success = temp_db.delete_template(template_id)
        assert success == True

        # 验证模板已删除
        template = temp_db.get_template_detail(template_id)
        assert template is None

    def test_delete_system_template(self, temp_db):
        """测试系统模板不可删除"""
        system_templates = temp_db.get_templates(is_system=True)
        if system_templates:
            system_template_id = system_templates[0]['id']

            # 尝试删除系统模板（应该失败）
            success = temp_db.delete_template(system_template_id)
            assert success == False

            # 验证系统模板仍然存在
            template = temp_db.get_template_detail(system_template_id)
            assert template is not None

    def test_use_template(self, temp_db, sample_script_data, sample_product_info):
        """测试使用模板（增加计数）"""
        template_id = temp_db.save_template(
            name='测试模板',
            category='测试',
            description='测试描述',
            product_info=sample_product_info,
            script_data=sample_script_data,
            is_system=False,
            created_by='user'
        )

        # 初始使用计数
        template = temp_db.get_template_detail(template_id)
        initial_count = template['usage_count']
        assert initial_count == 0

        # 使用模板
        temp_db.use_template(template_id)

        # 验证计数增加
        template = temp_db.get_template_detail(template_id)
        assert template['usage_count'] == initial_count + 1

        # 再次使用
        temp_db.use_template(template_id)
        template = temp_db.get_template_detail(template_id)
        assert template['usage_count'] == initial_count + 2

    def test_use_nonexistent_template(self, temp_db):
        """测试使用不存在的模板"""
        success = temp_db.use_template(999999)
        assert success == False

    def test_search_templates(self, temp_db, sample_script_data, sample_product_info):
        """测试搜索模板"""
        # 创建多个模板
        temp_db.save_template(
            name='抖音爆款模板',
            category='产品展示',
            description='适用于抖音平台',
            product_info={**sample_product_info, 'name': '产品'},
            script_data=sample_script_data,
            is_system=False,
            created_by='user'
        )

        temp_db.save_template(
            name='小红书模板',
            category='生活分享',
            description='适用于小红书平台',
            product_info={**sample_product_info, 'name': '产品2'},
            script_data=sample_script_data,
            is_system=False,
            created_by='user'
        )

        # 搜索抖音
        results = temp_db.search_templates('抖音')
        assert len(results) >= 1
        assert any('抖音' in r['name'] or '抖音' in r['description'] for r in results)

        # 按分类搜索
        results = temp_db.search_templates('模板', category='产品展示')
        assert all(r['category'] == '产品展示' for r in results)

    def test_get_template_categories(self, temp_db):
        """测试获取所有分类"""
        categories = temp_db.get_template_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert '产品展示' in categories


# ==================== 测试 4: 边界条件 ====================

class TestEdgeCases:
    """测试边界条件"""

    def test_empty_product_info(self, temp_db, sample_script_data):
        """测试空产品信息"""
        product_info = {
            'name': '',
            'keywords': [],
            'style': '活力',
            'duration': 30,
            'platform': '抖音'
        }

        history_id = temp_db.save_script_history(
            title='测试',
            script_data=sample_script_data,
            product_info=product_info,
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        assert history_id > 0
        history = temp_db.get_script_detail(history_id)
        assert history['product_name'] == ''
        assert history['keywords'] == []

    def test_large_keywords_list(self, temp_db, sample_script_data):
        """测试大量关键词"""
        keywords = [f'关键词{i}' for i in range(100)]
        product_info = {
            'name': '产品',
            'keywords': keywords,
            'style': '活力',
            'duration': 30,
            'platform': '抖音'
        }

        history_id = temp_db.save_script_history(
            title='测试',
            script_data=sample_script_data,
            product_info=product_info,
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        history = temp_db.get_script_detail(history_id)
        assert len(history['keywords']) == 100

    def test_limit_zero(self, temp_db):
        """测试limit=0"""
        histories = temp_db.get_script_history(limit=0)
        assert len(histories) == 0

    def test_large_offset(self, temp_db):
        """测试大偏移量"""
        histories = temp_db.get_script_history(limit=10, offset=999999)
        assert len(histories) == 0

    def test_special_characters_in_search(self, temp_db, sample_script_data, sample_product_info):
        """测试特殊字符搜索"""
        special_title = '测试!@#$%^&*()_+'

        temp_db.save_script_history(
            title=special_title,
            script_data=sample_script_data,
            product_info=sample_product_info,
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        results = temp_db.search_history('测试!')
        assert len(results) >= 1


# ==================== 测试 5: 数据一致性 ====================

class TestDataConsistency:
    """测试数据一致性"""

    def test_foreign_key_cascade(self, temp_db):
        """测试外键级联删除"""
        # 保存历史记录
        history_id = temp_db.save_script_history(
            title='测试',
            script_data={'title': '测试', 'scenes': []},
            product_info={'name': '产品', 'keywords': [], 'style': '活力', 'duration': 30, 'platform': '抖音'},
            style='活力',
            duration=30,
            platform='抖音',
            is_favorite=False
        )

        # 保存视频历史
        video_history_id = temp_db.save_video_history(
            history_id=history_id,
            task_id='video_task_123',
            model='kling-v1',
            aspect_ratio='9:16',
            status='succeed',
            video_url='http://example.com/video.mp4'
        )

        assert video_history_id > 0

        # 删除脚本历史（应该级联删除视频历史）
        temp_db.delete_script_history(history_id)

        # 验证视频历史也被删除
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM video_history WHERE history_id = ?", (history_id,))
            count = cursor.fetchone()['count']
            assert count == 0

    def test_concurrent_writes(self, temp_db, sample_script_data, sample_product_info):
        """测试并发写入"""
        import threading

        results = []
        errors = []

        def save_record(index):
            try:
                history_id = temp_db.save_script_history(
                    title=f'并发测试{index}',
                    script_data=sample_script_data,
                    product_info=sample_product_info,
                    style='活力',
                    duration=30,
                    platform='抖音',
                    is_favorite=False
                )
                results.append(history_id)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=save_record, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # SQLite默认是串行的，所以不会有真正的并发问题
        # 但测试应该能正常运行
        assert len(errors) == 0, f"并发写入出错: {errors}"
        assert len(results) == 10

        # 验证所有记录都被保存
        histories = temp_db.get_script_history(limit=100)
        assert len(histories) >= 10


# ==================== 测试 6: 性能测试 ====================

class TestPerformance:
    """性能测试"""

    def test_bulk_insert_performance(self, temp_db, sample_script_data, sample_product_info):
        """测试批量插入性能"""
        import time

        start = time.time()

        for i in range(100):
            temp_db.save_script_history(
                title=f'性能测试{i}',
                script_data=sample_script_data,
                product_info=sample_product_info,
                style='活力',
                duration=30,
                platform='抖音',
                is_favorite=False
            )

        elapsed = time.time() - start

        # 100条记录应该在1秒内完成
        assert elapsed < 1.0, f"批量插入耗时: {elapsed}秒"

    def test_search_performance(self, temp_db, sample_script_data, sample_product_info):
        """测试搜索性能"""
        import time

        # 插入100条记录
        for i in range(100):
            temp_db.save_script_history(
                title=f'搜索测试{i}',
                script_data=sample_script_data,
                product_info=sample_product_info,
                style='活力',
                duration=30,
                platform='抖音',
                is_favorite=False
            )

        # 测试搜索性能
        start = time.time()
        results = temp_db.search_history('搜索')
        elapsed = time.time() - start

        assert len(results) >= 100
        assert elapsed < 0.1, f"搜索耗时: {elapsed}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])