import { useState, useEffect, useRef } from 'react'
import { Upload, Play, XCircle, CheckCircle2, AlertCircle, Loader2, Download, RefreshCw, Image as ImageIcon } from 'lucide-react'
import type { AspectRatio, VideoTask } from '../types'
import { createImage2Video, getImage2VideoStatus } from '../api'

interface Props {
  onBack?: () => void
}

const RATIOS: { value: AspectRatio; label: string; desc: string; width: number; height: number }[] = [
  { value: '9:16', label: '9:16', desc: '竖屏（抖音/快手）', width: 270, height: 480 },
  { value: '16:9', label: '16:9', desc: '横屏（B站）', width: 480, height: 270 },
  { value: '1:1', label: '1:1', desc: '方形（小红书）', width: 400, height: 400 },
]

const MODELS = [
  { value: 'kling-v1-5-video-generation-3.0-turbo', label: '可灵 3.0 Turbo', desc: '最新版本，速度快质量高' },
]

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  submitted: { label: '已提交', color: 'text-blue-600', bg: 'bg-blue-50' },
  processing: { label: '生成中...', color: 'text-amber-600', bg: 'bg-amber-50' },
  succeeded: { label: '生成成功', color: 'text-green-600', bg: 'bg-green-50' },
  succeed: { label: '生成成功', color: 'text-green-600', bg: 'bg-green-50' },
  failed: { label: '生成失败', color: 'text-red-600', bg: 'bg-red-50' },
}

// 预设提示词示例
const PROMPT_EXAMPLES = [
  "让图片中的人物微笑着慢慢向前走，背景有轻微的云朵流动",
  "水面泛起涟漪，倒影微微晃动，阳光在水面上闪烁",
  "树叶随风轻轻摇曳，阳光穿过树叶洒下斑驳的光影",
  "人物眨眼，微微点头，眼神更加生动",
  "背景中的花瓣缓缓飘落，营造出梦幻般的氛围",
]

export default function Image2Video({ onBack }: Props) {
  const [imageUrl, setImageUrl] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')
  const [prompt, setPrompt] = useState('')
  const [ratio, setRatio] = useState<AspectRatio>('9:16')
  const [model, setModel] = useState('kling-v1-5-video-generation-3.0-turbo')
  const [duration, setDuration] = useState(5)
  const [watermarkEnabled, setWatermarkEnabled] = useState(true)
  const [task, setTask] = useState<VideoTask | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // 轮询状态
  const startPolling = (taskId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getImage2VideoStatus(taskId)
        setTask(updated)
        if (updated.status === 'succeeded' || updated.status === 'succeed' || updated.status === 'failed') {
          clearInterval(pollRef.current!)
          pollRef.current = null
        }
      } catch {
        // 忽略轮询错误
      }
    }, 3000)
  }

  // 图片URL变更时更新预览
  useEffect(() => {
    if (imageUrl) {
      setPreviewUrl(imageUrl)
    }
  }, [imageUrl])

  // 处理文件上传
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // 检查文件类型
    if (!file.type.startsWith('image/')) {
      setError('请上传图片文件')
      return
    }

    // 检查文件大小（10MB）
    if (file.size > 10 * 1024 * 1024) {
      setError('图片大小不能超过10MB')
      return
    }

    setUploading(true)
    setError(null)

    try {
      // 这里应该上传到服务器，暂时使用本地预览URL
      // 实际项目中需要上传到 OSS 或服务器
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreviewUrl(reader.result as string)
        setImageUrl(reader.result as string)
      }
      reader.readAsDataURL(file)
    } catch (e) {
      setError('图片处理失败')
    } finally {
      setUploading(false)
    }
  }

  // 创建图生视频任务
  const handleCreate = async () => {
    if (!imageUrl) {
      setError('请先上传图片或输入图片URL')
      return
    }
    if (!prompt) {
      setError('请输入提示词')
      return
    }

    setLoading(true)
    setError(null)
    setTask(null)

    try {
      const created = await createImage2Video({
        image_url: imageUrl,
        prompt,
        model,
        duration,
        aspect_ratio: ratio,
        watermark_enabled: watermarkEnabled,
      })
      setTask(created)
      startPolling(created.task_id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '图生视频创建失败，请检查API配置'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // 重新生成
  const handleRetry = () => {
    handleCreate()
  }

  // 下载视频
  const handleDownload = () => {
    if (!task?.video_url) return
    const link = document.createElement('a')
    link.href = task.video_url
    link.download = `image2video_${task.task_id}.mp4`
    link.click()
  }

  const statusInfo = task ? STATUS_MAP[task.status] : null

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {onBack && (
        <button onClick={onBack} className="btn-secondary flex items-center gap-2">
          返回
        </button>
      )}

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-5">图生视频</h2>
        <p className="text-sm text-gray-600 mb-6">
          上传一张图片，使用可灵3.0 Turbo模型将其转换为动态视频。
        </p>

        {/* 图片上传区域 */}
        <div className="mb-6">
          <label className="label">上传图片</label>
          <div className="flex gap-4">
            {/* 上传按钮 */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="btn-secondary flex items-center gap-2"
              >
                <Upload size={16} />
                {uploading ? '处理中...' : '选择图片'}
              </button>
            </div>

            {/* URL输入 */}
            <div className="flex-1">
              <input
                type="text"
                placeholder="或输入图片URL"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
              />
            </div>
          </div>

          {/* 图片预览 */}
          {previewUrl && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">预览</p>
              <div className="inline-block rounded-lg overflow-hidden border border-gray-200">
                <img
                  src={previewUrl}
                  alt="预览"
                  className="max-h-64 object-contain"
                />
              </div>
            </div>
          )}
        </div>

        {/* 提示词输入 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="label mb-0">提示词</label>
            <button
              onClick={() => {
                const random = PROMPT_EXAMPLES[Math.floor(Math.random() * PROMPT_EXAMPLES.length)]
                setPrompt(random)
              }}
              className="text-xs text-brand-600 hover:text-brand-700"
            >
              随机示例
            </button>
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="描述你想要的视频效果，例如：让画面中的人物微笑着慢慢走动..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 resize-none"
          />
          <div className="flex gap-2 mt-2 flex-wrap">
            {PROMPT_EXAMPLES.slice(0, 3).map((ex, i) => (
              <button
                key={i}
                onClick={() => setPrompt(ex)}
                className="text-xs px-2 py-1 bg-slate-100 text-slate-600 rounded hover:bg-slate-200 transition-colors"
              >
                {ex.slice(0, 15)}...
              </button>
            ))}
          </div>
        </div>

        {/* 参数配置 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {/* 宽高比 */}
          <div>
            <label className="label">宽高比</label>
            <select
              value={ratio}
              onChange={(e) => setRatio(e.target.value as AspectRatio)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            >
              {RATIOS.map((r) => (
                <option key={r.value} value={r.value}>{r.label} - {r.desc}</option>
              ))}
            </select>
          </div>

          {/* 时长 */}
          <div>
            <label className="label">时长（秒）</label>
            <select
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            >
              {[5, 10].map((d) => (
                <option key={d} value={d}>{d}秒</option>
              ))}
            </select>
          </div>

          {/* 模型 */}
          <div className="col-span-2">
            <label className="label">模型</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 水印选项 */}
        <div className="mb-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={watermarkEnabled}
              onChange={(e) => setWatermarkEnabled(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-brand-500 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-700">添加可灵水印</span>
          </label>
          <p className="text-xs text-gray-500 mt-1 ml-6">关闭水印可能需要付费或更高的API权限</p>
        </div>

        {/* 创建按钮 */}
        <button
          onClick={handleCreate}
          disabled={loading || task?.status === 'processing' || task?.status === 'submitted'}
          className="btn-primary flex items-center gap-2 w-full justify-center"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              创建中...
            </>
          ) : (
            <>
              <ImageIcon size={16} />
              生成视频
            </>
          )}
        </button>

        {error && (
          <div className="mt-3 flex items-start gap-2 text-red-600 bg-red-50 p-3 rounded-lg text-sm">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* 任务状态 */}
      {task && (
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="shrink-0">
              {task.status === 'processing' || task.status === 'submitted' ? (
                <Loader2 size={24} className="text-amber-500 animate-spin" />
              ) : task.status === 'succeeded' || task.status === 'succeed' ? (
                <CheckCircle2 size={24} className="text-green-500" />
              ) : (
                <XCircle size={24} className="text-red-500" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <p className="text-sm font-medium text-gray-900">
                  任务 ID: <span className="font-mono text-xs">{task.task_id}</span>
                </p>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusInfo?.bg} ${statusInfo?.color}`}>
                  {statusInfo?.label}
                </span>
              </div>

              {(task.status === 'processing' || task.status === 'submitted') && (
                <p className="text-sm text-gray-500">视频生成中，通常需要 1-2 分钟...</p>
              )}

              {task.status === 'failed' && (
                <p className="text-sm text-red-600">{task.error}</p>
              )}

              {/* 视频预览 */}
              {(task.status === 'succeeded' || task.status === 'succeed') && task.video_url && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-900 mb-2">生成结果</p>
                  <div className="rounded-lg overflow-hidden border border-gray-200 bg-black">
                    <video
                      src={task.video_url}
                      controls
                      className="w-full max-h-96"
                      poster={task.cover_url}
                    />
                  </div>
                  <div className="flex gap-3 mt-3">
                    <button
                      onClick={handleDownload}
                      className="btn-primary flex items-center gap-2 text-sm"
                    >
                      <Download size={16} />
                      下载视频
                    </button>
                    <button
                      onClick={handleRetry}
                      className="btn-secondary flex items-center gap-2 text-sm"
                    >
                      <RefreshCw size={16} />
                      重新生成
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}