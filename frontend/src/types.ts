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
  status: 'submitted' | 'processing' | 'succeed' | 'succeeded' | 'failed'
  video_url?: string
  cover_url?: string
  error?: string
}

export type VideoTaskType = 'text2video' | 'image2video'

export interface VideoListItem extends VideoTask {
  task_type: VideoTaskType
  created_at?: number
  updated_at?: number
  duration?: string
}

export interface VideoListResponse {
  items: VideoListItem[]
  page_num: number
  page_size: number
  task_type: VideoTaskType
}

export interface Image2VideoCreateRequest {
  image_url: string
  prompt: string
  model?: string
  duration?: number
  aspect_ratio?: AspectRatio
  callback_url?: string
  external_task_id?: string
  watermark_enabled?: boolean
}

export interface Image2VideoResult extends VideoTask {
  create_time?: number
  update_time?: number
  external_id?: string
}

// ========== 批量视频相关类型 ==========

export interface VideoSegment {
  segment_id: string
  segment_no: number
  scene_index: number
  /** 成片时间线中的目标时长。 */
  duration: number
  /** 提交模型的合法生成时长，短分镜通常生成后再裁剪。 */
  generation_duration?: number
  /** 合并时实际保留的时长，未设置时使用 duration。 */
  trim_duration?: number
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

// ========== 历史记录相关类型 ==========

export interface ScriptHistory {
  id: number
  title: string
  product_name: string
  brand: string | null
  keywords: string[]
  style: string
  duration: number
  platform: string
  created_at: string
  is_favorite: boolean
}

export interface ScriptHistoryDetail extends ScriptHistory {
  script_data: ScriptResult
}

export interface HistoryStats {
  total: number
  favorite_count: number
  style_stats: Record<string, number>
  platform_stats: Record<string, number>
}

// ========== 模板库相关类型 ==========

export interface Template {
  id: number
  name: string
  category: string
  description: string
  product_name: string
  keywords: string[]
  style: string
  duration: number
  platform: string
  is_system: boolean
  created_by: string | null
  created_at: string
  usage_count: number
}

export interface TemplateDetail extends Template {
  script_data: ScriptResult
}

export type VideoStyle = '活力' | '专业' | '温情' | '搞笑'
export type VideoDuration = 15 | 30 | 60
export type AspectRatio = '9:16' | '16:9' | '1:1'
