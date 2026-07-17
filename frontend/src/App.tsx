import { useState } from 'react'
import { Video, FileText, Package, Download, ChevronRight, Clock, LayoutTemplate, Image as ImageIcon } from 'lucide-react'
import type { ProductInfo, ScriptResult, VideoTask, BatchVideoTask } from './types'
import Step1Product from './pages/Step1Product'
import Step2Script from './pages/Step2Script'
import Step3Video from './pages/Step3Video'
import Step4Download from './pages/Step4Download'
import History from './pages/History'
import TemplateLibrary from './pages/TemplateLibrary'
import Image2Video from './pages/Image2Video'

const STEPS = [
  { label: '商品信息', icon: Package },
  { label: '生成脚本', icon: FileText },
  { label: '生成视频', icon: Video },
  { label: '下载发布', icon: Download },
]

type Page = 'generator' | 'history' | 'template' | 'image2video'

export default function App() {
  const [page, setPage] = useState<Page>('generator')
  const [step, setStep] = useState(0)
  const [product, setProduct] = useState<ProductInfo | null>(null)
  const [script, setScript] = useState<ScriptResult | null>(null)
  const [videoTask, setVideoTask] = useState<VideoTask | null>(null)
  const [batchTask, setBatchTask] = useState<BatchVideoTask | null>(null)

  // 从历史记录恢复状态
  const handleReuseHistory = (history: { product_info: ProductInfo; script_data: ScriptResult; style: string; duration: number; platform: string }) => {
    setProduct(history.product_info)
    setScript(history.script_data)
    setStep(2) // 直接跳到 Step3Video
    setPage('generator')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <header className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
              <Video size={18} className="text-white" />
            </div>
            <h1 className="text-lg font-semibold text-gray-900">商品宣传视频生成系统</h1>
          </div>
          <nav className="flex gap-2">
            <button
              onClick={() => setPage('generator')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                page === 'generator'
                  ? 'bg-brand-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              视频生成
            </button>
            <button
              onClick={() => setPage('image2video')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                page === 'image2video'
                  ? 'bg-brand-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <ImageIcon size={16} />
              图生视频
            </button>
            <button
              onClick={() => setPage('history')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                page === 'history'
                  ? 'bg-brand-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Clock size={16} />
              历史记录
            </button>
            <button
              onClick={() => setPage('template')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                page === 'template'
                  ? 'bg-brand-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <LayoutTemplate size={16} />
              模板库
            </button>
          </nav>
        </div>
      </header>

      <main>
        {page === 'history' ? (
          <History onReuseHistory={handleReuseHistory} />
        ) : page === 'template' ? (
          <TemplateLibrary />
        ) : page === 'image2video' ? (
          <div className="max-w-5xl mx-auto px-6 py-8">
            <Image2Video onBack={() => setPage('generator')} />
          </div>
        ) : (
          <div className="max-w-5xl mx-auto px-6 py-8">
            {/* Stepper */}
            <div className="flex items-center justify-center mb-10">
              {STEPS.map((s, i) => {
                const Icon = s.icon
                const done = i < step
                const active = i === step
                return (
                  <div key={i} className="flex items-center">
                    <div className="flex flex-col items-center gap-1.5">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all
                          ${done ? 'bg-brand-500 text-white' : active ? 'bg-brand-500 text-white ring-4 ring-brand-100' : 'bg-gray-100 text-gray-400'}`}
                      >
                        <Icon size={18} />
                      </div>
                      <span
                        className={`text-xs font-medium whitespace-nowrap
                          ${active ? 'text-brand-600' : done ? 'text-gray-600' : 'text-gray-400'}`}
                      >
                        {s.label}
                      </span>
                    </div>
                    {i < STEPS.length - 1 && (
                      <ChevronRight
                        size={20}
                        className={`mx-3 mb-5 ${i < step ? 'text-brand-400' : 'text-gray-200'}`}
                      />
                    )}
                  </div>
                )
              })}
            </div>

        {/* Step Content */}
        {step === 0 && (
          <Step1Product
            onNext={(p) => {
              setProduct(p)
              setStep(1)
            }}
          />
        )}
        {step === 1 && product && (
          <Step2Script
            product={product}
            onBack={() => setStep(0)}
            onNext={(s) => {
              setScript(s)
              setStep(2)
            }}
          />
        )}
        {step === 2 && script && (
          <Step3Video
            script={script}
            onBack={() => setStep(1)}
            onNext={(t, batchT) => {
              if (batchT) {
                setBatchTask(batchT)
                setVideoTask(null)
              } else {
                setVideoTask(t)
                setBatchTask(null)
              }
              setStep(3)
            }}
          />
        )}
        {step === 3 && (videoTask || batchTask) && (
          <Step4Download
            task={videoTask}
            batchTask={batchTask}
            onRestart={() => {
              setStep(0)
              setProduct(null)
              setScript(null)
              setVideoTask(null)
              setBatchTask(null)
            }}
          />
        )}
          </div>
        )}
      </main>
    </div>
  )
}