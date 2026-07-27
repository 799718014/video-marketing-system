import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { Download, Film, Image as ImageIcon, Loader2, RefreshCw, Video } from 'lucide-react'
import { getDownloadUrl, getVideoList } from '../api'
import type { VideoListItem, VideoTaskType } from '../types'

const PAGE_SIZE = 12

const STATUS_LABEL: Record<string, string> = {
  submitted: '已提交',
  processing: '生成中',
  succeed: '已完成',
  succeeded: '已完成',
  failed: '生成失败',
}

const STATUS_STYLE: Record<string, string> = {
  submitted: 'bg-blue-50 text-blue-700',
  processing: 'bg-amber-50 text-amber-700',
  succeed: 'bg-emerald-50 text-emerald-700',
  succeeded: 'bg-emerald-50 text-emerald-700',
  failed: 'bg-red-50 text-red-700',
}

const requestError = (error: unknown) => {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return error instanceof Error ? error.message : '加载视频列表失败，请稍后重试'
}

const formatTime = (timestamp?: number) => {
  if (!timestamp) return '时间未知'
  return new Date(timestamp).toLocaleString('zh-CN', { hour12: false })
}

export default function VideoLibrary() {
  const [taskType, setTaskType] = useState<VideoTaskType>('text2video')
  const [page, setPage] = useState(1)
  const [items, setItems] = useState<VideoListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getVideoList(taskType, page, PAGE_SIZE)
      setItems(result.items)
    } catch (err) {
      setItems([])
      setError(requestError(err))
    } finally {
      setLoading(false)
    }
  }, [page, taskType])

  useEffect(() => {
    void load()
  }, [load])

  const switchType = (nextType: VideoTaskType) => {
    setTaskType(nextType)
    setPage(1)
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="card mb-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Film size={21} className="text-brand-500" />
              可灵视频库
            </h2>
            <p className="text-sm text-gray-600 mt-2">
              查看可灵账号中的历史生成任务，成功视频可直接预览并下载转存。视频链接可能过期，请及时下载。
            </p>
          </div>
          <button onClick={() => void load()} disabled={loading} className="btn-secondary flex items-center gap-2 shrink-0">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            刷新
          </button>
        </div>
        <div className="flex gap-2 mt-5">
          <button
            onClick={() => switchType('text2video')}
            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${taskType === 'text2video' ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            <Video size={16} /> 文生视频
          </button>
          <button
            onClick={() => switchType('image2video')}
            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${taskType === 'image2video' ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
          >
            <ImageIcon size={16} /> 图生视频
          </button>
        </div>
      </div>

      {error && <div className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="py-20 flex justify-center text-brand-600"><Loader2 className="animate-spin" size={28} /></div>
      ) : items.length === 0 ? (
        <div className="card py-16 text-center text-sm text-gray-500">暂无可灵视频任务</div>
      ) : (
        <>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => <VideoCard key={item.task_id} item={item} />)}
          </div>
          <div className="flex justify-center items-center gap-3 mt-8">
            <button onClick={() => setPage(page - 1)} disabled={page === 1} className="btn-secondary text-sm disabled:opacity-50">上一页</button>
            <span className="text-sm text-gray-600">第 {page} 页</span>
            <button onClick={() => setPage(page + 1)} disabled={items.length < PAGE_SIZE} className="btn-secondary text-sm disabled:opacity-50">下一页</button>
          </div>
        </>
      )}
    </div>
  )
}

function VideoCard({ item }: { item: VideoListItem }) {
  const completed = item.status === 'succeed' || item.status === 'succeeded'
  return (
    <article className="card overflow-hidden p-0">
      {completed && item.video_url ? (
        <video src={item.video_url} poster={item.cover_url} controls preload="metadata" className="w-full aspect-video bg-black object-contain" />
      ) : (
        <div className="w-full aspect-video bg-slate-100 text-slate-400 flex items-center justify-center">
          {item.status === 'processing' || item.status === 'submitted' ? <Loader2 className="animate-spin" size={28} /> : <Video size={28} />}
        </div>
      )}
      <div className="p-4">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_STYLE[item.status] ?? 'bg-slate-100 text-slate-600'}`}>
            {STATUS_LABEL[item.status] ?? item.status}
          </span>
          {item.duration && <span className="text-xs text-gray-500">{item.duration} 秒</span>}
        </div>
        <p className="font-mono text-xs text-gray-500 mt-3 truncate" title={item.task_id}>任务：{item.task_id}</p>
        <p className="text-xs text-gray-500 mt-1">创建于：{formatTime(item.created_at)}</p>
        {item.error && <p className="text-xs text-red-600 mt-2 line-clamp-2">{item.error}</p>}
        {completed && item.video_url && (
          <a href={getDownloadUrl(item.task_id, item.task_type)} className="btn-primary mt-4 w-full justify-center flex items-center gap-2 text-sm">
            <Download size={16} /> 下载并转存
          </a>
        )}
      </div>
    </article>
  )
}
