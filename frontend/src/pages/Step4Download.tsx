import { useState, useEffect } from 'react'
import { CheckCircle2, Download, RefreshCw, ExternalLink, Loader2 } from 'lucide-react'
import type { VideoTask, BatchVideoTask } from '../types'
import { getDownloadUrl, getBatchDownloadUrl, checkMergeStatus } from '../api'

interface Props {
  task?: VideoTask
  batchTask?: BatchVideoTask
  onRestart: () => void
}

const PLATFORMS = [
  { name: '抖音', color: 'bg-black text-white', url: 'https://creator.douyin.com' },
  { name: '快手', color: 'bg-orange-500 text-white', url: 'https://cp.kuaishou.com' },
  { name: '小红书', color: 'bg-red-500 text-white', url: 'https://creator.xiaohongshu.com' },
  { name: 'B站', color: 'bg-blue-500 text-white', url: 'https://member.bilibili.com/platform/upload/video/frame' },
]

export default function Step4Download({ task, batchTask, onRestart }: Props) {
  const [isMerging, setIsMerging] = useState(false)
  const [mergedReady, setMergedReady] = useState(false)

  // 检查批量任务是否需要轮询合并状态
  useEffect(() => {
    if (batchTask && batchTask.status === 'merging' && !mergedReady) {
      setIsMerging(true)
      const interval = setInterval(async () => {
        try {
          const updated = await checkMergeStatus(batchTask.batch_id)
          if (updated.status === 'succeed') {
            setIsMerging(false)
            setMergedReady(true)
            clearInterval(interval)
          } else if (updated.status === 'failed') {
            setIsMerging(false)
            clearInterval(interval)
          }
        } catch {
          // 忽略错误
        }
      }, 3000)

      return () => clearInterval(interval)
    } else if (batchTask?.status === 'succeed') {
      setMergedReady(true)
      setIsMerging(false)
    }
  }, [batchTask, mergedReady])

  const isBatch = !!batchTask
  const currentTask = batchTask || task
  const taskId = isBatch ? batchTask?.batch_id : task?.task_id
  const downloadUrl = isBatch ? getBatchDownloadUrl(batchTask!.batch_id) : getDownloadUrl(task!.task_id)
  const videoUrl = isBatch ? batchTask?.merged_video_url : task?.video_url
  const totalDuration = isBatch ? batchTask?.total_duration : 5

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* 成功状态 */}
      <div className="card text-center">
        <div className="flex justify-center mb-4">
          {isMerging ? (
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <Loader2 size={32} className="text-purple-500 animate-spin" />
            </div>
          ) : (
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle2 size={32} className="text-green-500" />
            </div>
          )}
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-1">
          {isMerging ? '视频合并中...' : '视频生成完成！'}
        </h2>
        <p className="text-sm text-gray-500">
          {isBatch ? `批量任务 ID: <span className="font-mono">${batchTask?.batch_id}</span>` : `任务 ID: <span className="font-mono">${task?.task_id}</span>`}
        </p>
        {isBatch && (
          <p className="text-xs text-gray-400 mt-1">
            已合并 {batchTask?.segments.length} 个片段，总时长 {totalDuration} 秒
          </p>
        )}
      </div>

      {/* 视频预览 */}
      {videoUrl && (
        <div className="card">
          <h3 className="text-base font-semibold text-gray-900 mb-3">完整视频预览</h3>
          <video
            src={videoUrl}
            controls
            className="w-full max-h-[480px] rounded-xl bg-black"
          />
          {(isBatch ? batchTask?.merged_cover_url : task?.cover_url) && (
            <div className="mt-3 flex items-center gap-3">
              <img
                src={isBatch ? batchTask?.merged_cover_url : task?.cover_url}
                alt="封面"
                className="w-16 h-auto rounded-lg border border-gray-200"
              />
              <div>
                <p className="text-xs font-medium text-gray-600">封面图</p>
                <a
                  href={isBatch ? batchTask?.merged_cover_url : task?.cover_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-brand-600 hover:underline"
                >
                  查看原图
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 合并中提示 */}
      {isMerging && (
        <div className="card bg-purple-50 border-purple-200">
          <div className="flex items-center gap-2 text-purple-700">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">正在使用 moviepy 合并视频片段，请稍候...</span>
          </div>
        </div>
      )}

      {/* 下载按钮 */}
      <div className="card">
        <h3 className="text-base font-semibold text-gray-900 mb-3">下载视频</h3>
        <a
          href={downloadUrl}
          download
          className={`btn-primary flex items-center gap-2 w-full justify-center ${isMerging ? 'opacity-50 cursor-not-allowed' : ''}`}
          onClick={(e) => {
            if (isMerging) e.preventDefault()
          }}
        >
          <Download size={16} /> 下载 {isBatch ? '完整' : ''} MP4 视频文件 ({totalDuration}秒)
        </a>
        {isBatch && (
          <div className="mt-3">
            <h4 className="text-sm font-medium text-gray-700 mb-2">单独下载片段</h4>
            <div className="flex flex-wrap gap-2">
              {batchTask?.segments.map((seg) => (
                <a
                  key={seg.segment_id}
                  href={`/api/batch-video/segment/${batchTask.batch_id}/${seg.segment_no}`}
                  download
                  className={`text-xs px-2 py-1 rounded border ${
                    seg.status === 'succeed'
                      ? 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100'
                      : 'bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed'
                  }`}
                  onClick={(e) => {
                    if (seg.status !== 'succeed') e.preventDefault()
                  }}
                >
                  片段 {seg.segment_no}
                </a>
              ))}
            </div>
          </div>
        )}
        <p className="text-xs text-gray-400 mt-2 text-center">
          {isBatch
            ? '视频已自动拼接，保存到本地后可上传至各平台'
            : '视频将通过后端代理下载，保存到本地后可上传至各平台'
          }
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
          {isBatch && (
            <li>• 长视频（{totalDuration}秒）建议在各平台发布时选择横屏或完整竖屏模式</li>
          )}
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