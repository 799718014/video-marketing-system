import { useState, useEffect } from 'react'
import { getTemplateList, getTemplateCategories, getTemplateDetail, searchTemplates, saveTemplateToHistory, type Template, type TemplateDetail } from '../api'

export default function TemplateLibrary() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [showSystemOnly, setShowSystemOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const data = await getTemplateList({
        category: selectedCategory || undefined,
        is_system: showSystemOnly ? true : undefined,
        limit: 100
      })
      setTemplates(data)
    } catch (error) {
      console.error('加载模板失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      const data = await getTemplateCategories()
      setCategories(data.categories)
    } catch (error) {
      console.error('加载分类失败:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      loadTemplates()
      return
    }
    setLoading(true)
    try {
      const data = await searchTemplates(searchKeyword, selectedCategory || undefined, 100)
      setTemplates(data)
    } catch (error) {
      console.error('搜索失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetail = async (template: Template) => {
    try {
      const detail = await getTemplateDetail(template.id)
      setSelectedTemplate(detail)
      setShowDetailModal(true)
    } catch (error) {
      console.error('获取模板详情失败:', error)
    }
  }

  const handleUseTemplate = async () => {
    if (!selectedTemplate) return
    try {
      await fetch(`/api/template/use/${selectedTemplate.id}`, { method: 'POST' })
      // TODO: 导航到生成页面并填充数据
      alert('模板已应用！请前往生成页面')
      setShowDetailModal(false)
    } catch (error) {
      console.error('应用模板失败:', error)
    }
  }

  const handleSaveToHistory = async () => {
    if (!selectedTemplate) return
    try {
      const result = await saveTemplateToHistory(selectedTemplate.id, selectedTemplate.name, false)
      if (result.success) {
        alert(`已保存到历史记录！ID: ${result.id}`)
        setShowDetailModal(false)
      }
    } catch (error) {
      console.error('保存失败:', error)
      alert('保存失败，请稍后重试')
    }
  }

  useEffect(() => {
    loadTemplates()
    loadCategories()
  }, [selectedCategory, showSystemOnly])

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">模板库</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          + 创建模板
        </button>
      </div>

      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 mb-4">
          <input
            type="text"
            placeholder="搜索模板..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1 px-4 py-2 border rounded-lg"
          />
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            搜索
          </button>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">分类:</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1 border rounded-lg"
            >
              <option value="">全部</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={showSystemOnly}
              onChange={(e) => setShowSystemOnly(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-600">只看系统模板</span>
          </label>
        </div>
      </div>

      {/* 模板列表 */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">加载中...</div>
      ) : templates.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          暂无模板
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <div
              key={template.id}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleViewDetail(template)}
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold text-lg">{template.name}</h3>
                  {template.is_system && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                      系统
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                  {template.description}
                </p>
                <div className="flex flex-wrap gap-2 mb-3">
                  <span className="px-2 py-1 bg-gray-100 text-xs rounded">
                    {template.category}
                  </span>
                  <span className="px-2 py-1 bg-gray-100 text-xs rounded">
                    {template.style}
                  </span>
                  <span className="px-2 py-1 bg-gray-100 text-xs rounded">
                    {template.duration}秒
                  </span>
                  <span className="px-2 py-1 bg-gray-100 text-xs rounded">
                    {template.platform}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>使用次数: {template.usage_count}</span>
                  <span>{new Date(template.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 详情弹窗 */}
      {showDetailModal && selectedTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold">{selectedTemplate.name}</h2>
                  <div className="flex gap-2 mt-2">
                    {selectedTemplate.is_system && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                        系统模板
                      </span>
                    )}
                    <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">
                      {selectedTemplate.category}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="mb-4">
                <p className="text-gray-600">{selectedTemplate.description}</p>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-gray-500 text-sm">产品名称</label>
                  <div className="font-medium">{selectedTemplate.product_name}</div>
                </div>
                <div>
                  <label className="text-gray-500 text-sm">关键词</label>
                  <div className="flex flex-wrap gap-2">
                    {selectedTemplate.keywords.map((keyword, index) => (
                      <span key={index} className="px-2 py-1 bg-gray-100 rounded text-sm">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-gray-500 text-sm">风格</label>
                    <div className="font-medium">{selectedTemplate.style}</div>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm">时长</label>
                    <div className="font-medium">{selectedTemplate.duration}秒</div>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm">平台</label>
                    <div className="font-medium">{selectedTemplate.platform}</div>
                  </div>
                </div>

                {/* 场景预览 */}
                <div>
                  <label className="text-gray-500 text-sm">场景预览</label>
                  <div className="mt-2 space-y-2">
                    {selectedTemplate.script_data.scenes?.map((scene, index) => (
                      <div key={index} className="p-3 bg-gray-50 rounded">
                        <div className="font-medium text-sm">场景 {scene.scene_no} ({scene.duration}秒)</div>
                        <div className="text-sm text-gray-600">{scene.visual}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>使用次数: {selectedTemplate.usage_count}</span>
                  <span>
                    {selectedTemplate.created_by === 'system' ? '系统创建' : `创建者: ${selectedTemplate.created_by}`}
                  </span>
                  <span>{new Date(selectedTemplate.created_at).toLocaleString()}</span>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  关闭
                </button>
                <button
                  onClick={handleSaveToHistory}
                  className="px-4 py-2 border border-blue-500 text-blue-500 rounded-lg hover:bg-blue-50"
                >
                  保存到历史
                </button>
                <button
                  onClick={handleUseTemplate}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  使用此模板
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 创建模板弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
            <h2 className="text-xl font-bold mb-4">创建自定义模板</h2>
            <p className="text-gray-600 mb-4">
              从历史记录中选择一个脚本，将其保存为模板
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  // TODO: 实现创建模板逻辑
                  alert('创建模板功能开发中...')
                }}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                去选择
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}