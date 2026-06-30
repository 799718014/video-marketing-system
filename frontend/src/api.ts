import axios from 'axios'
import type { ProductInfo, ScriptResult, VideoTask } from './types'

const http = axios.create({ baseURL: '/api' })

export interface ScriptRequest {
  product: ProductInfo
  style: string
  duration: number
  platform: string
}

export interface VideoCreateRequest {
  prompt: string
  model?: string
  duration?: number
  aspect_ratio?: string
  cfg_scale?: number
}

export const generateScript = (req: ScriptRequest): Promise<ScriptResult> =>
  http.post<ScriptResult>('/script/generate', req).then((r) => r.data)

export const createVideo = (req: VideoCreateRequest): Promise<VideoTask> =>
  http.post<VideoTask>('/video/create', req).then((r) => r.data)

export const getVideoStatus = (taskId: string): Promise<VideoTask> =>
  http.get<VideoTask>(`/video/status/${taskId}`).then((r) => r.data)

export const getDownloadUrl = (taskId: string): string =>
  `/api/video/download/${taskId}`
