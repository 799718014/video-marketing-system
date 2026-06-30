import { useState } from 'react'
import { Video, FileText, Package, Download, ChevronRight } from 'lucide-react'
import type { ProductInfo, ScriptResult, VideoTask } from './types'
import Step1Product from './pages/Step1Product'
import Step2Script from './pages/Step2Script'
import Step3Video from './pages/Step3Video'
import Step4Download from './pages/Step4Download'

const STEPS = [
  { label: '商品信息', icon: Package },
  { label: '生成脚本', icon: FileText },
  { label: '生成视频', icon: Video },
  { label: '下载发布', icon: Download },
]

export default function App() {
  const [step, setStep] = useState(0)
  const [product, setProduct] = useState<ProductInfo | null>(null)
  const [script, setScript] = useState<ScriptResult | null>(null)
  const [videoTask, setVideoTask] = useState<VideoTask | null>(null)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <header className="bg-white border-b border-gray-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
            <Video size={18} className="text-white" />
          </div>
          <h1 className="text-lg font-semibold text-gray-900">商品宣传视频生成系统</h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
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
            onNext={(t) => {
              setVideoTask(t)
              setStep(3)
            }}
          />
        )}
        {step === 3 && videoTask && (
          <Step4Download
            task={videoTask}
            onRestart={() => {
              setStep(0)
              setProduct(null)
              setScript(null)
              setVideoTask(null)
            }}
          />
        )}
      </main>
    </div>
  )
}
