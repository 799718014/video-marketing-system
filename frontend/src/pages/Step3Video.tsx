import { useState, useEffect, useRef } from 'react'
import { Clapperboard, ChevronLeft, ChevronRight, Loader2, CheckCircle2, XCircle, AlertCircle, RefreshCw, Play } from 'lucide-react'
import type { ScriptResult, VideoTask, BatchVideoTask, VideoSegment, AspectRatio } from '../types'
import { createVideo, getVideoStatus, createBatchVideo, getBatchStatus, checkMergeStatus, retryBatchSegments } from '../api'
import SegmentProgress from '../components/SegmentProgress'

interface Props {
  script: ScriptResult
  onBack: () => void
  onNext: (task: VideoTask | null, batchTask?: BatchVideoTask) => void
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
  merging: { label: '合并视频...', color: 'text-purple-600', bg: 'bg-purple-50' },
}

export default function Step3Video({ script, onBack, onNext }: Props) {
  // 视频参数
  const [ratio, setRatio] = useState<AspectRatio>('9:16')
  const [model, setModel] = useState('kling-v1-5')
  const [cfgScale, setCfgScale] = useState(0.5)

  // 单任务模式状态
  const [task, setTask] = useState<VideoTask | null>(null)

  // 批量模式状态
  const [batchMode, setBatchMode] = useState(false)
  const [batchTask, setBatchTask] = useState<BatchVideoTask | null>(null)
  const [showRetry, setShowRetry] = useState(false)
  const [previewSegment, setPreviewSegment] = useState<VideoSegment | null>(null)

  // 通用状态
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 轮询引用
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 检测是否需要批量模式
  useEffect(() => {
    if (script.total_duration > 5) {
      setBatchMode(true)
    }
  }, [script])

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // 单任务轮询
  const startSinglePolling = (taskId: string) => {
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
        // 忽略轮询错误
      }
    }, 5000)
  }

  // 批量任务轮询
  const startBatchPolling = (batchId: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getBatchStatus(batchId)
        setBatchTask(updated)

        // 检查是否有失败片段
        const hasFailed = updated.segments.some(s => s.status === 'failed')
        setShowRetry(hasFailed)

        // 检查是否需要合并
        if (updated.status === 'merging') {
          // 轮询合并状态
          const merged = await checkMergeStatus(batchId)
          if (merged.status === 'succeed') {
            setBatchTask(merged)
            clearInterval(pollRef.current!)
            pollRef.current = null
          }
        }

        // 全部完成或全部失败停止轮询
        const allDone = updated.segments.every(s => s.status === 'succeed')
        const allFailed = updated.segments.every(s => s.status === 'failed')

        if (allDone && updated.status === 'merging') {
          // 等待合并完成
        } else if (allDone || allFailed) {
          clearInterval(pollRef.current!)
          pollRef.current = null
        }
      } catch {
        // 忽略轮询错误
      }
    }, 3000)
  }

  // 单任务创建
  const handleSingleCreate = async () => {
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
      startSinglePolling(created.task_id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '视频创建失败，请检查可灵影音 API Key'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // 批量任务创建
  const handleBatchCreate = async () => {
    setLoading(true)
    setError(null)
    setBatchTask(null)
    setShowRetry(false)
    try {
      const created = await createBatchVideo({
        script,
        model,
        aspect_ratio: ratio,
        cfg_scale: cfgScale,
        transition: 'fade',
        max_concurrent: 3,
      })
      setBatchTask(created)
      startBatchPolling(created.batch_id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '批量视频创建失败'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // 重试失败片段
  const handleRetry = async () => {
    if (!batchTask) return
    setShowRetry(false)
    try {
      const updated = await retryBatchSegments(batchTask.batch_id)
      setBatchTask(updated)
      startBatchPolling(batchTask.batch_id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '重试失败'
      setError(msg)
    }
  }

  // 计算进度
  const calculateProgress = () => {
    if (batchTask) {
      const completed = batchTask.segments.filter(s => s.status === 'succeed').length
      const total = batchTask.segments.length
      return Math.round((completed / total) * 100)
    }
    return 0
  }

  const progress = calculateProgress()
  const statusInfo = batchTask ? STATUS_MAP[batchTask.status] : task ? STATUS_MAP[task.status] : null

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
                <strong>提示：</strong>可灵影音每次最长生成 5 秒视频。
                {batchMode ? (
                  <>检测到您选择了 {script.total_duration} 秒视频，将自动拆分为多个片段生成后合并。</>
                ) : (
                  <>长视频需分段生成后合并。</>
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4">
          <button
            onClick={batchMode ? handleBatchCreate : handleSingleCreate}
            disabled={loading || (batchMode ? batchTask?.status === 'processing' : task?.status === 'processing')}
            className="btn-primary flex items-center gap-2 w-full justify-center"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Clapperboard size={16} />}
            {loading ? '提交中...' : batchMode ? `批量生成视频（${script.total_duration}秒）` : '开始生成视频'}
          </button>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 text-red-600 bg-red-50 p-3 rounded-lg text-sm">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* 单任务状态 */}
      {!batchMode && task && (
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

      {/* 批量任务状态 */}
      {batchMode && batchTask && (
        <>
          {/* 进度概览 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                {batchTask.status === 'merging' ? (
                  <Loader2 size={20} className="text-purple-500 animate-spin" />
                ) : batchTask.status === 'processing' ? (
                  <Loader2 size={20} className="text-amber-500 animate-spin" />
                ) : batchTask.status === 'succeed' ? (
                  <CheckCircle2 size={20} className="text-green-500" />
                ) : (
                  <XCircle size={20} className="text-red-500" />
                )}
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    批量任务 ID: <span className="font-mono text-xs">{batchTask.batch_id}</span>
                  </p>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusInfo?.bg} ${statusInfo?.color}`}>
                    {statusInfo?.label}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">
                  已完成: {batchTask.segments.filter(s => s.status === 'succeed').length} / {batchTask.segments.length}
                </p>
                <p className="text-xs text-gray-400">总时长: {batchTask.total_duration}秒</p>
              </div>
            </div>

            {/* 进度条 */}
            <div className="mb-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-brand-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1 text-center">{progress}%</p>
            </div>

            {/* 重试按钮 */}
            {showRetry && (
              <button
                onClick={handleRetry}
                className="w-full flex items-center justify-center gap-2 p-2 bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 transition-colors"
              >
                <RefreshCw size={16} />
                重试失败片段
              </button>
            )}
          </div>

          {/* 片段列表 */}
          <div className="card">
            <h3 className="text-base font-semibold text-gray-900 mb-3">视频片段</h3>
            <div className="space-y-2">
              {batchTask.segments.map((segment) => (
                <SegmentProgress
                  key={segment.segment_id}
                  segment={segment}
                  onPreview={() => setPreviewSegment(segment)}
                />
              ))}
            </div>
          </div>

          {/* 错误信息 */}
          {batchTask.status === 'failed' && batchTask.error && (
            <div className="card bg-red-50 border-red-200">
              <p className="text-sm text-red-700">{batchTask.error}</p>
            </div>
          )}
        </>
      )}

      {/* 预览模态框 */}
      {previewSegment && previewSegment.video_url && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setPreviewSegment(null)}>
          <div className="bg-white rounded-xl p-4 max-w-lg w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-900">片段 {previewSegment.segment_no} 预览</h3>
              <button onClick={() => setPreviewSegment(null)} className="p-1 hover:bg-gray-100 rounded">
                ✕
              </button>
            </div>
            <video src={previewSegment.video_url} controls className="w-full rounded-lg" />
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button onClick={onBack} className="btn-secondary flex items-center gap-2">
          <ChevronLeft size={16} /> 上一步
        </button>
        <button
          onClick={() => {
            if (batchMode && batchTask?.status === 'succeed') {
              onNext(null, batchTask)
            } else if (!batchMode && task?.status === 'succeed') {
              onNext(task)
            }
          }}
          disabled={(batchMode ? batchTask?.status !== 'succeed' : task?.status !== 'succeed')}
          className="btn-primary flex items-center gap-2"
        >
          下一步：下载发布 <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}