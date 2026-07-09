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

// ========== 批量视频相关类型 ==========

export interface VideoSegment {
  segment_id: string
  segment_no: number
  scene_index: number
  duration: number
  prompt: string
  keling_task_id?: string
  status: 'pending' | 'processing' | 'succeed' | 'failed'
  video_url?: string
  cover_url?: string
  retry_count: number
  error?: string
}

export interface BatchVideoTask {
  batch_id: string
  script: ScriptResult
  video_params: {
    model: string
    aspect_ratio: string
    cfg_scale: number
    transition: string
  }
  segments: VideoSegment[]
  status: 'submitted' | 'processing' | 'succeed' | 'failed' | 'merging'
  merged_video_path?: string
  merged_video_url?: string
  merged_cover_url?: string
  total_duration: number
  created_at: number
  completed_at?: number
  error?: string
}

export type VideoStyle = '活力' | '专业' | '温情' | '搞笑'
export type VideoDuration = 15 | 30 | 60
export type AspectRatio = '9:16' | '16:9' | '1:1'
