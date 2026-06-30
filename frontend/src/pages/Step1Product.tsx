import { useState, KeyboardEvent } from 'react'
import { X, Plus, ChevronRight } from 'lucide-react'
import type { ProductInfo } from '../types'

interface Props {
  onNext: (product: ProductInfo) => void
}

const AUDIENCE_OPTIONS = ['年轻女性', '年轻男性', '中年女性', '中年男性', '学生群体', '职场人士', '家庭主妇', '老年群体']

export default function Step1Product({ onNext }: Props) {
  const [keywords, setKeywords] = useState<string[]>([])
  const [kwInput, setKwInput] = useState('')
  const [name, setName] = useState('')
  const [brand, setBrand] = useState('')
  const [price, setPrice] = useState('')
  const [description, setDescription] = useState('')
  const [features, setFeatures] = useState<string[]>([''])
  const [audience, setAudience] = useState('')

  const addKeyword = () => {
    const kw = kwInput.trim()
    if (kw && !keywords.includes(kw)) {
      setKeywords([...keywords, kw])
    }
    setKwInput('')
  }

  const handleKwKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addKeyword()
    }
  }

  const removeKeyword = (kw: string) => setKeywords(keywords.filter((k) => k !== kw))

  const updateFeature = (i: number, val: string) => {
    const next = [...features]
    next[i] = val
    setFeatures(next)
  }

  const addFeature = () => setFeatures([...features, ''])
  const removeFeature = (i: number) => setFeatures(features.filter((_, idx) => idx !== i))

  const canNext =
    keywords.length > 0 &&
    name.trim() &&
    description.trim() &&
    features.some((f) => f.trim()) &&
    audience

  const handleNext = () => {
    if (!canNext) return
    onNext({
      keywords,
      name: name.trim(),
      brand: brand.trim(),
      price: price.trim(),
      description: description.trim(),
      features: features.filter((f) => f.trim()),
      target_audience: audience,
    })
  }

  return (
    <div className="card max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">填写商品信息</h2>

      {/* 关键词 */}
      <div className="mb-5">
        <label className="label">关键词 <span className="text-red-400">*</span></label>
        <div className="flex flex-wrap gap-2 p-2.5 border border-gray-200 rounded-lg min-h-[44px] focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-transparent">
          {keywords.map((kw) => (
            <span key={kw} className="flex items-center gap-1 bg-brand-50 text-brand-700 text-sm px-2.5 py-0.5 rounded-full">
              {kw}
              <button onClick={() => removeKeyword(kw)} className="hover:text-brand-900">
                <X size={12} />
              </button>
            </span>
          ))}
          <input
            value={kwInput}
            onChange={(e) => setKwInput(e.target.value)}
            onKeyDown={handleKwKeyDown}
            onBlur={addKeyword}
            placeholder={keywords.length === 0 ? '输入关键词后按 Enter 添加...' : '继续添加...'}
            className="flex-1 min-w-[120px] outline-none text-sm bg-transparent"
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">按 Enter 或逗号分隔，可添加多个</p>
      </div>

      {/* 基本信息 */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div>
          <label className="label">商品名称 <span className="text-red-400">*</span></label>
          <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} placeholder="例：无线蓝牙耳机 Pro" />
        </div>
        <div>
          <label className="label">品牌</label>
          <input className="input-field" value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="例：索尼 / 华为" />
        </div>
        <div>
          <label className="label">价格</label>
          <input className="input-field" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="例：¥299 / 299元" />
        </div>
      </div>

      {/* 商品描述 */}
      <div className="mb-5">
        <label className="label">商品描述 <span className="text-red-400">*</span></label>
        <textarea
          className="input-field resize-none"
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="简要描述商品的核心价值、使用场景、解决的痛点..."
        />
      </div>

      {/* 产品亮点 */}
      <div className="mb-5">
        <label className="label">产品亮点 <span className="text-red-400">*</span></label>
        <div className="space-y-2">
          {features.map((f, i) => (
            <div key={i} className="flex gap-2">
              <input
                className="input-field"
                value={f}
                onChange={(e) => updateFeature(i, e.target.value)}
                placeholder={`亮点 ${i + 1}，例：主动降噪，安静工作`}
              />
              {features.length > 1 && (
                <button onClick={() => removeFeature(i)} className="text-gray-400 hover:text-red-400 transition-colors">
                  <X size={18} />
                </button>
              )}
            </div>
          ))}
        </div>
        {features.length < 6 && (
          <button onClick={addFeature} className="mt-2 flex items-center gap-1 text-brand-600 text-sm hover:text-brand-700">
            <Plus size={14} /> 添加亮点
          </button>
        )}
      </div>

      {/* 目标人群 */}
      <div className="mb-8">
        <label className="label">目标人群 <span className="text-red-400">*</span></label>
        <div className="flex flex-wrap gap-2">
          {AUDIENCE_OPTIONS.map((a) => (
            <button
              key={a}
              onClick={() => setAudience(a)}
              className={`px-3 py-1.5 rounded-full text-sm border transition-all
                ${audience === a ? 'bg-brand-500 text-white border-brand-500' : 'bg-white text-gray-600 border-gray-200 hover:border-brand-300'}`}
            >
              {a}
            </button>
          ))}
          <input
            className="input-field !w-32"
            placeholder="自定义..."
            value={AUDIENCE_OPTIONS.includes(audience) ? '' : audience}
            onChange={(e) => setAudience(e.target.value)}
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleNext} disabled={!canNext} className="btn-primary flex items-center gap-2">
          下一步：生成脚本 <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
