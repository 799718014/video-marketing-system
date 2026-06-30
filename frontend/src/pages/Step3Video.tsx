import { useState, useEffect, useRef } from 'react'
import { Clapperboard, ChevronLeft, ChevronRight, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import type { ScriptResult, VideoTask, AspectRatio } from '../types'
import { createVideo, getVideoStatus } from '../api'

interface Props {
  script: ScriptResult
  onBack: () => void
  onNext: (task: VideoTask) => void
}

const RATIOS: { value: AspectRatio; label: string; desc: string }[] = [
  { value: '9:16', label: '9:16', desc: '竖屏（抖音/快手）' },
  { value: '16:9', label: '16:9', desc: '横屏（B站）' },
  { value: '1:1', label: '1:1', desc: '方形（小红书）' },
]

const MODELS = [
  { value: 'kling-v1', label: '可灵 v1', desc: '标准质量，生成较快' },
  { value: 'kling-v1-5', label: '可灵 v1.5', desc: '高质量，推荐使用' },
]

const STATUS_MAP = {
  submitted: { label: '已提交', color: 'text-blue-600', bg: 'bg-blue-50' },
  processing: { label: '生成中...', color: 'text-amber-600', bg: 'bg-amber-50' },
  succeed: { label: '生成成功', color: 'text-green-600', bg: 'bg-green-50' },
  failed: { label: '生成失败', color: 'text-red-600', bg: 'bg-red-50' },
}

export default function Step3Video({ script, onBack, onNext }: Props) {
  const [ratio, setRatio] = useState<AspectRatio>('9:16')
  const [model, setModel] = useState('kling-v1-5')
  const [cfgScale, setCfgScale] = useState(0.5)
  const [task, setTask] = useState<VideoTask | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startPolling = (taskId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getVideoStatus(taskId)
        setTask(updated)
        if (updated.status === 'succeed' || updated.status === 'failed') {
          clearInterval(pollRef.current!)
          pollRef.current = null
        }
      } catch {
        // 忽略轮询错误，继续重试
      }
    }, 5000)
  }

  const handleCreate = async () => {
    setLoading(true)
    setError(null)
    setTask(null)
    try {
      const created = await createVideo({
        prompt: script.full_prompt,
        model,
        duration: 5,
        aspect_ratio: ratio,
        cfg_scale: cfgScale,
      })
      setTask(created)
      startPolling(created.task_id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '视频创建失败，请检查可灵影音 API Key'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const statusInfo = task ? STATUS_MAP[task.status] : null

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-5">配置视频参数</h2>

        {/* Prompt 预览 */}
        <div className="mb-5 p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <p className="text-xs font-medium text-slate-500 mb-1">生成 Prompt（来自脚本）</p>
          <p className="text-sm text-slate-700 leading-relaxed">{script.full_prompt}</p>
        </div>

        <div className="grid grid-cols-3 gap-6 mb-5">
          {/* 画面比例 */}
          <div>
            <label className="label">画面比例</label>
            <div className="space-y-2">
              {RATIOS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => setRatio(r.value)}
                  className={`w-full p-2.5 rounded-lg border text-left text-sm transition-all
                    ${ratio === r.value ? 'bg-brand-50 border-brand-400 text-brand-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                >
                  <div className="font-medium">{r.label}</div>
                  <div className="text-xs text-gray-400">{r.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 模型选择 */}
          <div>
            <label className="label">生成模型</label>
            <div className="space-y-2">
              {MODELS.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setModel(m.value)}
                  className={`w-full p-2.5 rounded-lg border text-left text-sm transition-all
                    ${model === m.value ? 'bg-brand-50 border-brand-400 text-brand-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                >
                  <div className="font-medium">{m.label}</div>
                  <div className="text-xs text-gray-400">{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 创意强度 */}
          <div>
            <label className="label">创意强度 <span className="text-gray-400 font-normal">{cfgScale.toFixed(1)}</span></label>
            <div className="mt-3">
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={cfgScale}
                onChange={(e) => setCfgScale(parseFloat(e.target.value))}
                className="w-full accent-brand-500"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>自由创意</span>
                <span>严格遵循</span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-amber-50 rounded-lg">
              <p className="text-xs text-amber-700">
                <strong>提示：</strong>可灵影音每次最长生成 5 秒视频。长视频需分段生成后合并。
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4">
          <button
            onClick={handleCreate}
            disabled={loading || (task?.status === 'processing') || (task?.status === 'submitted')}
            className="btn-primary flex items-center gap-2 w-full justify-center"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Clapperboard size={16} />}
            {loading ? '提交中...' : '开始生成视频'}
          </button>
        </div>

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
          <div className="flex items-center gap-3 mb-3">
            {task.status === 'processing' || task.status === 'submitted' ? (
              <Loader2 size={20} className="text-amber-500 animate-spin" />
            ) : task.status === 'succeed' ? (
              <CheckCircle2 size={20} className="text-green-500" />
            ) : (
              <XCircle size={20} className="text-red-500" />
            )}
            <div>
              <p className="text-sm font-medium text-gray-900">
                任务 ID: <span className="font-mono text-xs">{task.task_id}</span>
              </p>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusInfo?.bg} ${statusInfo?.color}`}>
                {statusInfo?.label}
              </span>
            </div>
          </div>

          {(task.status === 'processing' || task.status === 'submitted') && (
            <div className="flex items-center gap-2 text-sm text-gray-500 mt-2">
              <Loader2 size={14} className="animate-spin" />
              每 5 秒自动刷新状态，视频生成通常需要 1-3 分钟...
            </div>
          )}

          {task.status === 'failed' && (
            <p className="text-sm text-red-600 mt-1">{task.error}</p>
          )}

          {task.status === 'succeed' && task.cover_url && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-2">封面预览</p>
              <img src={task.cover_url} alt="视频封面" className="w-32 h-auto rounded-lg border border-gray-200" />
            </div>
          )}
        </div>
      )}

      <div className="flex justify-between">
        <button onClick={onBack} className="btn-secondary flex items-center gap-2">
          <ChevronLeft size={16} /> 上一步
        </button>
        <button
          onClick={() => task && onNext(task)}
          disabled={task?.status !== 'succeed'}
          className="btn-primary flex items-center gap-2"
        >
          下一步：下载发布 <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
