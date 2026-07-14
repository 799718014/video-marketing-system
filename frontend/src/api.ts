import axios from 'axios'
import type { ProductInfo, ScriptResult, VideoTask, BatchVideoTask, ScriptHistory, ScriptHistoryDetail, Template, TemplateDetail, HistoryStats, Image2VideoCreateRequest, Image2VideoResult } from './types'

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

// ========== 图生视频 API ==========

export const createImage2Video = (req: Image2VideoCreateRequest): Promise<Image2VideoResult> =>
  http.post<Image2VideoResult>('/video/image2video/create', req).then((r) => r.data)

export const getImage2VideoStatus = (taskId: string): Promise<Image2VideoResult> =>
  http.get<Image2VideoResult>(`/video/image2video/status/${taskId}`).then((r) => r.data)

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

export const retrySingleSegment = (batchId: string, segmentNo: number): Promise<BatchVideoTask> =>
  http.post<BatchVideoTask>(`/batch-video/retry-segment/${batchId}/${segmentNo}`).then((r) => r.data)

export const getBatchDownloadUrl = (batchId: string): string =>
  `/api/batch-video/download/${batchId}`

export const getSegmentDownloadUrl = (batchId: string, segmentNo: number): string =>
  `/api/batch-video/segment/${batchId}/${segmentNo}`

// ========== 历史记录 API ==========

export interface HistoryListParams {
  limit?: number
  offset?: number
  favorite_only?: boolean
}

export const getHistoryList = (params: HistoryListParams = {}): Promise<ScriptHistory[]> =>
  http.get<ScriptHistory[]>('/history/list', { params }).then((r) => r.data)

export const getHistoryDetail = (historyId: number): Promise<ScriptHistoryDetail> =>
  http.get<ScriptHistoryDetail>(`/history/detail/${historyId}`).then((r) => r.data)

export const searchHistory = (keyword: string, limit: number = 20): Promise<ScriptHistory[]> =>
  http.get<ScriptHistory[]>('/history/search', { params: { keyword, limit } }).then((r) => r.data)

export const updateHistoryFavorite = (historyId: number, isFavorite: boolean): Promise<{ success: boolean; is_favorite: boolean }> =>
  http.put<{ success: boolean; is_favorite: boolean }>(`/history/favorite/${historyId}`, { is_favorite: isFavorite }).then((r) => r.data)

export const deleteHistory = (historyId: number): Promise<{ success: boolean }> =>
  http.delete<{ success: boolean }>(`/history/${historyId}`).then((r) => r.data)

export const getHistoryStats = (): Promise<HistoryStats> =>
  http.get<HistoryStats>('/history/stats').then((r) => r.data)

export const saveHistory = (
  title: string,
  scriptData: ScriptResult,
  productInfo: ProductInfo,
  style: string,
  duration: number,
  platform: string,
  isFavorite: boolean = false
): Promise<{ id: number; success: boolean }> =>
  http.post<{ id: number; success: boolean }>('/history/save', {
    title,
    script_data: scriptData,
    product_info: productInfo,
    style,
    duration,
    platform,
    is_favorite: isFavorite
  }).then((r) => r.data)

// ========== 模板库 API ==========

export interface TemplateListParams {
  category?: string
  is_system?: boolean
  limit?: number
}

export const getTemplateList = (params: TemplateListParams = {}): Promise<Template[]> =>
  http.get<Template[]>('/template/list', { params }).then((r) => r.data)

export const getTemplateCategories = (): Promise<{ categories: string[] }> =>
  http.get<{ categories: string[] }>('/template/categories').then((r) => r.data)

export const getTemplateDetail = (templateId: number): Promise<TemplateDetail> =>
  http.get<TemplateDetail>(`/template/detail/${templateId}`).then((r) => r.data)

export const searchTemplates = (keyword: string, category?: string, limit: number = 20): Promise<Template[]> =>
  http.get<Template[]>('/template/search', { params: { keyword, category, limit } }).then((r) => r.data)

export interface CreateTemplateRequest {
  name: string
  category: string
  description: string
  product_name: string
  keywords: string[]
  style: string
  duration: number
  platform: string
  script_data: ScriptResult
}

export const createTemplate = (req: CreateTemplateRequest): Promise<{ id: number; success: boolean }> =>
  http.post<{ id: number; success: boolean }>('/template/create', req).then((r) => r.data)

export interface UpdateTemplateRequest {
  name?: string
  description?: string
  script_data?: ScriptResult
}

export const updateTemplate = (templateId: number, req: UpdateTemplateRequest): Promise<{ success: boolean }> =>
  http.put<{ success: boolean }>(`/template/update/${templateId}`, req).then((r) => r.data)

export const deleteTemplate = (templateId: number): Promise<{ success: boolean }> =>
  http.delete<{ success: boolean }>(`/template/${templateId}`).then((r) => r.data)

export const useTemplate = (templateId: number): Promise<{ success: boolean }> =>
  http.post<{ success: boolean }>(`/template/use/${templateId}`).then((r) => r.data)

export const saveTemplateToHistory = (templateId: number, title: string, isFavorite: boolean = false): Promise<{ id: number; success: boolean }> =>
  http.post<{ id: number; success: boolean }>(`/template/save-to-history/${templateId}`, null, {
    params: { title, is_favorite: isFavorite }
  }).then((r) => r.data)
