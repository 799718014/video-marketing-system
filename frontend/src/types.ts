export interface ProductInfo {
  keywords: string[]
  name: string
  brand: string
  price: string
  description: string
  features: string[]
  target_audience: string
}

export interface ScriptScene {
  scene_no: number
  duration: number
  visual: string
  narration: string
  subtitle: string
}

export interface ScriptResult {
  title: string
  total_duration: number
  style: string
  scenes: ScriptScene[]
  full_prompt: string
}

export interface VideoTask {
  task_id: string
  status: 'submitted' | 'processing' | 'succeed' | 'failed'
  video_url?: string
  cover_url?: string
  error?: string
}

export type VideoStyle = '活力' | '专业' | '温情' | '搞笑'
export type VideoDuration = 15 | 30 | 60
export type AspectRatio = '9:16' | '16:9' | '1:1'
