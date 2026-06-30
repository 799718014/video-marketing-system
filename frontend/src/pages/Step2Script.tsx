import { useState } from 'react'
import { Sparkles, ChevronLeft, ChevronRight, Clock, Eye, Mic, Captions, Loader2, AlertCircle } from 'lucide-react'
import type { ProductInfo, ScriptResult, VideoStyle, VideoDuration } from '../types'
import { generateScript } from '../api'

interface Props {
  product: ProductInfo
  onBack: () => void
  onNext: (script: ScriptResult) => void
}

const STYLES: VideoStyle[] = ['活力', '专业', '温情', '搞笑']
const DURATIONS: VideoDuration[] = [15, 30, 60]
const PLATFORMS = ['抖音', '快手', '小红书', 'B站']

const STYLE_DESC: Record<VideoStyle, string> = {
  活力: '动感快节奏，年轻化',
  专业: '权威严谨，数据驱动',
  温情: '情感共鸣，真实生活',
  搞笑: '幽默反转，轻松有趣',
}

export default function Step2Script({ product, onBack, onNext }: Props) {
  const [style, setStyle] = useState<VideoStyle>('活力')
  const [duration, setDuration] = useState<VideoDuration>(30)
  const [platform, setPlatform] = useState('抖音')
  const [script, setScript] = useState<ScriptResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await generateScript({ product, style, duration, platform })
      setScript(result)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '脚本生成失败，请检查 API Key 配置'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const updateScene = (i: number, field: string, value: string) => {
    if (!script) return
    const scenes = [...script.scenes]
    scenes[i] = { ...scenes[i], [field]: value }
    setScript({ ...script, scenes })
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* 参数配置卡 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-5">配置脚本参数</h2>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <label className="label">视频风格</label>
            <div className="grid grid-cols-2 gap-2">
              {STYLES.map((s) => (
                <button
                  key={s}
                  onClick={() => setStyle(s)}
                  className={`p-2 rounded-lg border text-sm text-left transition-all
                    ${style === s ? 'bg-brand-50 border-brand-400 text-brand-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                >
                  <div className="font-medium">{s}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{STYLE_DESC[s]}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label">视频时长</label>
            <div className="space-y-2">
              {DURATIONS.map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  className={`w-full p-2.5 rounded-lg border text-sm flex items-center gap-2 transition-all
                    ${duration === d ? 'bg-brand-50 border-brand-400 text-brand-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                >
                  <Clock size={14} />
                  {d} 秒
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label">目标平台</label>
            <div className="space-y-2">
              {PLATFORMS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPlatform(p)}
                  className={`w-full p-2.5 rounded-lg border text-sm transition-all
                    ${platform === p ? 'bg-brand-50 border-brand-400 text-brand-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-5 pt-4 border-t border-gray-100">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="btn-primary flex items-center gap-2 w-full justify-center"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {loading ? 'AI 正在生成脚本...' : '生成视频脚本'}
          </button>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 text-red-600 bg-red-50 p-3 rounded-lg text-sm">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* 脚本结果 */}
      {script && (
        <div className="card">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{script.title}</h3>
              <p className="text-sm text-gray-500 mt-0.5">
                {script.style} · {script.total_duration}秒 · {script.scenes.length} 个场景
              </p>
            </div>
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">✓ 已生成</span>
          </div>

          <div className="space-y-4">
            {script.scenes.map((scene, i) => (
              <div key={i} className="border border-gray-100 rounded-xl p-4 bg-gray-50">
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-6 h-6 bg-brand-500 text-white text-xs rounded-full flex items-center justify-center font-medium">
                    {scene.scene_no}
                  </span>
                  <span className="text-sm font-medium text-gray-700">场景 {scene.scene_no}</span>
                  <span className="ml-auto flex items-center gap-1 text-xs text-gray-400">
                    <Clock size={12} /> {scene.duration}s
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  <div>
                    <label className="flex items-center gap-1 text-xs font-medium text-gray-500 mb-1">
                      <Eye size={12} /> 画面描述
                    </label>
                    <textarea
                      className="input-field resize-none text-sm"
                      rows={2}
                      value={scene.visual}
                      onChange={(e) => updateScene(i, 'visual', e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="flex items-center gap-1 text-xs font-medium text-gray-500 mb-1">
                        <Mic size={12} /> 旁白台词
                      </label>
                      <textarea
                        className="input-field resize-none text-sm"
                        rows={2}
                        value={scene.narration}
                        onChange={(e) => updateScene(i, 'narration', e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="flex items-center gap-1 text-xs font-medium text-gray-500 mb-1">
                        <Captions size={12} /> 字幕文字
                      </label>
                      <textarea
                        className="input-field resize-none text-sm"
                        rows={2}
                        value={scene.subtitle}
                        onChange={(e) => updateScene(i, 'subtitle', e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* AI Prompt 预览 */}
          <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <p className="text-xs font-medium text-slate-500 mb-1">视频生成 Prompt（可灵影音）</p>
            <p className="text-xs text-slate-600 leading-relaxed">{script.full_prompt}</p>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex justify-between">
        <button onClick={onBack} className="btn-secondary flex items-center gap-2">
          <ChevronLeft size={16} /> 上一步
        </button>
        <button
          onClick={() => script && onNext(script)}
          disabled={!script}
          className="btn-primary flex items-center gap-2"
        >
          下一步：生成视频 <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
