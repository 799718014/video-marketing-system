import { CheckCircle2, Download, RefreshCw, ExternalLink } from 'lucide-react'
import type { VideoTask } from '../types'
import { getDownloadUrl } from '../api'

interface Props {
  task: VideoTask
  onRestart: () => void
}

const PLATFORMS = [
  { name: '抖音', color: 'bg-black text-white', url: 'https://creator.douyin.com' },
  { name: '快手', color: 'bg-orange-500 text-white', url: 'https://cp.kuaishou.com' },
  { name: '小红书', color: 'bg-red-500 text-white', url: 'https://creator.xiaohongshu.com' },
  { name: 'B站', color: 'bg-blue-500 text-white', url: 'https://member.bilibili.com/platform/upload/video/frame' },
]

export default function Step4Download({ task, onRestart }: Props) {
  const downloadUrl = getDownloadUrl(task.task_id)

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* 成功状态 */}
      <div className="card text-center">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle2 size={32} className="text-green-500" />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-1">视频生成完成！</h2>
        <p className="text-sm text-gray-500">任务 ID: <span className="font-mono">{task.task_id}</span></p>
      </div>

      {/* 视频预览 */}
      {task.video_url && (
        <div className="card">
          <h3 className="text-base font-semibold text-gray-900 mb-3">视频预览</h3>
          <video
            src={task.video_url}
            controls
            className="w-full max-h-[480px] rounded-xl bg-black"
          />
          {task.cover_url && (
            <div className="mt-3 flex items-center gap-3">
              <img src={task.cover_url} alt="封面" className="w-16 h-auto rounded-lg border border-gray-200" />
              <div>
                <p className="text-xs font-medium text-gray-600">封面图</p>
                <a href={task.cover_url} target="_blank" rel="noreferrer" className="text-xs text-brand-600 hover:underline">
                  查看原图
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 下载按钮 */}
      <div className="card">
        <h3 className="text-base font-semibold text-gray-900 mb-3">下载视频</h3>
        <a
          href={downloadUrl}
          download
          className="btn-primary flex items-center gap-2 w-full justify-center"
        >
          <Download size={16} /> 下载 MP4 视频文件
        </a>
        <p className="text-xs text-gray-400 mt-2 text-center">
          视频将通过后端代理下载，保存到本地后可上传至各平台
        </p>
      </div>

      {/* 发布指引 */}
      <div className="card">
        <h3 className="text-base font-semibold text-gray-900 mb-3">前往平台发布</h3>
        <p className="text-sm text-gray-500 mb-4">下载视频后，点击以下链接前往对应平台的创作者中心上传发布：</p>
        <div className="grid grid-cols-2 gap-3">
          {PLATFORMS.map((p) => (
            <a
              key={p.name}
              href={p.url}
              target="_blank"
              rel="noreferrer"
              className={`flex items-center justify-between px-4 py-3 rounded-xl ${p.color} font-medium text-sm transition-opacity hover:opacity-90`}
            >
              {p.name} 创作者中心
              <ExternalLink size={14} />
            </a>
          ))}
        </div>
      </div>

      {/* 发布建议 */}
      <div className="card bg-brand-50 border-brand-100">
        <h3 className="text-sm font-semibold text-brand-800 mb-2">发布建议</h3>
        <ul className="space-y-1.5 text-sm text-brand-700">
          <li>• 上传视频时添加脚本中的字幕，提升完播率</li>
          <li>• 使用系统生成的标题和关键词作为视频标题/话题标签</li>
          <li>• 选择流量高峰时间段（早 8-9 点 / 晚 7-9 点）发布</li>
          <li>• 发布后主动互动评论区，加速流量推荐</li>
        </ul>
      </div>

      {/* 重新开始 */}
      <div className="flex justify-center pt-2">
        <button onClick={onRestart} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={16} /> 制作新视频
        </button>
      </div>
    </div>
  )
}
