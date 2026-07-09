import axios from 'axios'
import type { ProductInfo, ScriptResult, VideoTask, BatchVideoTask } from './types'

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

// ========== 单视频 API ==========

export const generateScript = (req: ScriptRequest): Promise<ScriptResult> =>
  http.post<ScriptResult>('/script/generate', req).then((r) => r.data)

export const createVideo = (req: VideoCreateRequest): Promise<VideoTask> =>
  http.post<VideoTask>('/video/create', req).then((r) => r.data)

export const getVideoStatus = (taskId: string): Promise<VideoTask> =>
  http.get<VideoTask>(`/video/status/${taskId}`).then((r) => r.data)

export const getDownloadUrl = (taskId: string): string =>
  `/api/video/download/${taskId}`

// ========== 批量视频 API ==========

export interface BatchVideoCreateRequest {
  script: ScriptResult
  model?: string
  aspect_ratio?: string
  cfg_scale?: number
  transition?: string
  max_concurrent?: number
}

export const createBatchVideo = (req: BatchVideoCreateRequest): Promise<BatchVideoTask> =>
  http.post<BatchVideoTask>('/batch-video/create', req).then((r) => r.data)

export const getBatchStatus = (batchId: string): Promise<BatchVideoTask> =>
  http.get<BatchVideoTask>(`/batch-video/status/${batchId}`).then((r) => r.data)

export const checkMergeStatus = (batchId: string): Promise<BatchVideoTask> =>
  http.get<BatchVideoTask>(`/batch-video/check-merge/${batchId}`).then((r) => r.data)

export const retryBatchSegments = (batchId: string): Promise<BatchVideoTask> =>
  http.post<BatchVideoTask>(`/batch-video/retry/${batchId}`).then((r) => r.data)

export const getBatchDownloadUrl = (batchId: string): string =>
  `/api/batch-video/download/${batchId}`

export const getSegmentDownloadUrl = (batchId: string, segmentNo: number): string =>
  `/api/batch-video/segment/${batchId}/${segmentNo}`
