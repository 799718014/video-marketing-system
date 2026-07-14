import { CheckCircle2, Loader2, XCircle, Play, RefreshCw, Download } from 'lucide-react'
import type { VideoSegment } from '../types'

interface Props {
  segment: VideoSegment
  onPreview?: () => void
  onRetry?: () => void
}

const STATUS_CONFIG = {
  pending: { icon: Loader2, color: 'text-gray-400', bg: 'bg-gray-100', label: '等待中', animate: false },
  processing: { icon: Loader2, color: 'text-blue-600', bg: 'bg-blue-50', label: '生成中', animate: true },
  succeed: { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50', label: '已完成' },
  failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50', label: '失败' },
}

export default function SegmentProgress({ segment, onPreview, onRetry }: Props) {
  const config = STATUS_CONFIG[segment.status]
  const Icon = config.icon

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
      {/* 状态图标 */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${config.bg}`}>
        <Icon size={16} className={config.color + (config.animate ? ' animate-spin' : '')} />
      </div>

      {/* 片段信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">片段 {segment.segment_no}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${config.color} ${config.bg}`}>
            {config.label}
          </span>
        </div>
        <p className="text-xs text-gray-500 truncate mt-0.5">
          {segment.duration}秒 · 对应场景 {segment.scene_index + 1}
          {segment.retry_count > 0 && ` · 已重试 ${segment.retry_count} 次`}
        </p>
        {/* Prompt 预览 */}
        <p className="text-xs text-gray-400 truncate max-w-md" title={segment.prompt}>
          {segment.prompt}
        </p>
        {segment.error && (
          <div className="mt-1 p-1.5 bg-red-50 rounded border border-red-100">
            <p className="text-xs text-red-600 break-words" title={segment.error}>{segment.error}</p>
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center gap-2">
        {segment.status === 'succeed' && onPreview && (
          <button
            onClick={onPreview}
            className="p-2 rounded-lg hover:bg-gray-200 text-gray-600 transition-colors"
            title="预览"
          >
            <Play size={16} />
          </button>
        )}
        {(segment.status === 'failed' || segment.status === 'succeed') && onRetry && (
          <button
            onClick={onRetry}
            className={`p-2 rounded-lg hover:bg-gray-200 transition-colors ${
              segment.status === 'failed' ? 'text-red-600 hover:bg-red-50' : 'text-gray-600'
            }`}
            title={segment.status === 'failed' ? '重试' : '重新生成'}
          >
            <RefreshCw size={16} />
          </button>
        )}
        {segment.status === 'succeed' && segment.video_url && (
          <a
            href={segment.video_url}
            download
            className="p-2 rounded-lg hover:bg-gray-200 text-gray-600 transition-colors"
            title="下载"
          >
            <Download size={16} />
          </a>
        )}
      </div>
    </div>
  )
}