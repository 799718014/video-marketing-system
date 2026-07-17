import { useState, useEffect } from 'react'
import { getHistoryList, getHistoryDetail, deleteHistory, updateHistoryFavorite, getHistoryStats, searchHistory } from '../api'
import type { ScriptHistory, ScriptHistoryDetail, HistoryStats } from '../types'

interface Props {
  onReuseHistory?: (history: { product_info: any; script_data: any; style: string; duration: number; platform: string }) => void
}

export default function History({ onReuseHistory }: Props) {
  const [histories, setHistories] = useState<ScriptHistory[]>([])
  const [stats, setStats] = useState<HistoryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [selectedHistory, setSelectedHistory] = useState<ScriptHistoryDetail | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)

  const loadHistories = async () => {
    setLoading(true)
    try {
      const data = await getHistoryList({
        limit: 50,
        favorite_only: favoriteOnly
      })
      setHistories(data)
    } catch (error) {
      console.error('加载历史记录失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const data = await getHistoryStats()
      setStats(data)
    } catch (error) {
      console.error('加载统计信息失败:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      loadHistories()
      return
    }
    setLoading(true)
    try {
      const results = await searchHistory(searchKeyword, 50)
      setHistories(results)
    } catch (error) {
      console.error('搜索失败:', error)
      alert('搜索失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleFavorite = async (history: ScriptHistory) => {
    try {
      await updateHistoryFavorite(history.id, !history.is_favorite)
      loadHistories()
      loadStats()
    } catch (error) {
      console.error('更新收藏状态失败:', error)
    }
  }

  const handleDelete = async (historyId: number) => {
    if (!confirm('确定要删除这条历史记录吗？')) return
    try {
      await deleteHistory(historyId)
      loadHistories()
      loadStats()
    } catch (error) {
      console.error('删除失败:', error)
    }
  }

  const handleViewDetail = async (history: ScriptHistory) => {
    try {
      const detail = await getHistoryDetail(history.id)
      setSelectedHistory(detail)
      setShowDetailModal(true)
    } catch (error) {
      console.error('获取历史详情失败:', error)
      alert('获取详情失败，请稍后重试')
    }
  }

  useEffect(() => {
    loadHistories()
    loadStats()
  }, [favoriteOnly])

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">历史记录</h1>
        <button
          onClick={loadHistories}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          刷新
        </button>
      </div>

      {/* 统计信息 */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">总记录数</div>
            <div className="text-2xl font-bold">{stats.total}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">收藏数</div>
            <div className="text-2xl font-bold">{stats.favorite_count}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">风格分布</div>
            <div className="text-sm">
              {Object.entries(stats.style_stats).map(([style, count]) => (
                <span key={style} className="inline-block mr-2">
                  {style}: {count}
                </span>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">平台分布</div>
            <div className="text-sm">
              {Object.entries(stats.platform_stats).map(([platform, count]) => (
                <span key={platform} className="inline-block mr-2">
                  {platform}: {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex gap-4">
        <input
          type="text"
          placeholder="搜索历史记录..."
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
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={favoriteOnly}
            onChange={(e) => setFavoriteOnly(e.target.checked)}
            className="w-4 h-4"
          />
          <span>只看收藏</span>
        </label>
      </div>

      {/* 历史记录列表 */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">加载中...</div>
      ) : histories.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          暂无历史记录
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">标题</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">产品</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">风格</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时长</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">平台</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">创建时间</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {histories.map((history) => (
                <tr key={history.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleFavorite(history)}
                        className="text-lg"
                      >
                        {history.is_favorite ? '⭐' : '☆'}
                      </button>
                      <span className="font-medium">{history.title}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">{history.product_name}</td>
                  <td className="px-6 py-4">{history.style}</td>
                  <td className="px-6 py-4">{history.duration}秒</td>
                  <td className="px-6 py-4">{history.platform}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(history.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleViewDetail(history)}
                        className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        查看
                      </button>
                      <button
                        onClick={() => handleDelete(history.id)}
                        className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 详情弹窗 */}
      {showDetailModal && selectedHistory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-bold">{selectedHistory.title}</h2>
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
              <div className="space-y-4 mb-6">
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <label className="text-gray-500 text-sm">产品名称</label>
                    <div className="font-medium">{selectedHistory.product_name}</div>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm">品牌</label>
                    <div className="font-medium">{selectedHistory.brand || '-'}</div>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm">风格</label>
                    <div className="font-medium">{selectedHistory.style}</div>
                  </div>
                  <div>
                    <label className="text-gray-500 text-sm">时长</label>
                    <div className="font-medium">{selectedHistory.duration}秒</div>
                  </div>
                </div>
                <div>
                  <label className="text-gray-500 text-sm">关键词</label>
                  <div className="flex flex-wrap gap-2">
                    {selectedHistory.keywords.map((keyword, index) => (
                      <span key={index} className="px-2 py-1 bg-gray-100 rounded text-sm">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-gray-500 text-sm">创建时间</label>
                  <div className="font-medium text-sm text-gray-600">
                    {new Date(selectedHistory.created_at).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* 脚本场景 */}
              <div className="border-t pt-4">
                <h3 className="font-semibold text-lg mb-3">脚本场景</h3>
                <div className="space-y-3">
                  {selectedHistory.script_data?.scenes?.map((scene: any, index: number) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg border">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="w-6 h-6 bg-brand-500 text-white text-xs rounded-full flex items-center justify-center font-medium">
                          {scene.scene_no}
                        </span>
                        <span className="font-medium text-sm">场景 {scene.scene_no}</span>
                        <span className="ml-auto text-xs text-gray-500">{scene.duration}s</span>
                      </div>
                      <div className="grid grid-cols-1 gap-2 text-sm">
                        <div>
                          <span className="text-gray-500">画面：</span>
                          <span className="text-gray-800">{scene.visual}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">旁白：</span>
                          <span className="text-gray-800">{scene.narration}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">字幕：</span>
                          <span className="text-gray-800">{scene.subtitle}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  关闭
                </button>
                <button
                  onClick={() => {
                    if (selectedHistory && onReuseHistory) {
                      onReuseHistory({
                        product_info: {
                          name: selectedHistory.product_name,
                          brand: selectedHistory.brand || '',
                          keywords: selectedHistory.keywords,
                          description: '',
                          features: [],
                          target_audience: '',
                          price: ''
                        },
                        script_data: selectedHistory.script_data,
                        style: selectedHistory.style,
                        duration: selectedHistory.duration,
                        platform: selectedHistory.platform
                      })
                    }
                    setShowDetailModal(false)
                  }}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  重新使用
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}