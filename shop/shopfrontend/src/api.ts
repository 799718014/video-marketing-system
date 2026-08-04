export type AssetType = 'main' | 'angle' | 'detail' | 'lifestyle' | 'transparent' | 'logo' | 'scene_ref'

export interface Product {
  id: number
  name: string
  brand?: string | null
  price?: string | null
  specs: Record<string, unknown>
  selling_points: string[]
  prohibited_terms: string[]
}

export interface ProductAsset {
  id: number
  product_id: number
  asset_type: AssetType
  url: string
  is_primary: number | boolean
  metadata: Record<string, unknown>
}

export interface PostprocessConfig {
  template: 'product_promo_portrait'
  subtitle?: string
  price_text?: string
  cta?: string
  transparent_asset_id?: number
  logo_asset_id?: number
}

export interface SceneReference {
  id?: number
  asset_id: number
  role: 'identity' | 'material' | 'detail' | 'element' | 'logo' | 'scene_setting'
  sort_order: number
  asset_type?: AssetType
  url?: string
}

export interface Scene {
  id?: number
  scene_no: number
  scene_type: string
  target_duration: number
  asset_id?: number
  asset_url?: string
  generation_strategy: 'image_to_video' | 'text_to_video'
  narration: string
  visual_description: string
  ai_prompt: string
  motion_prompt: string
  scene_prompt?: string
  identity_constraints: string[]
  reference_assets: SceneReference[]
  postprocess_layers: string[]
  postprocess_config: PostprocessConfig
}

export interface ScenePromptReference {
  narration: string
  visual_description: string
  ai_prompt: string
}

export interface Storyboard {
  id: number
  product_id: number
  title: string
  scenes: Scene[]
  final_video_url?: string | null
  final_composition_status?: string
  final_composition_error?: string | null
}

export interface GenerationTask {
  id: number
  scene_id: number
  scene_no: number
  provider_task_id?: string | null
  status: string
  video_url?: string | null
  composed_video_url?: string | null
  composition_status?: string
  composition_error?: string | null
  candidate_group_id?: string | null
  candidate_index?: number
  selected?: number | boolean
  reference_manifest?: SceneReference[]
  quality_status?: string
  quality_decision?: string | null
  error?: string | null
  created_at?: string
  updated_at?: string
}

export interface TraceEvent {
  id: number
  event_type: string
  created_at: string
  task_id?: number | null
  scene_id?: number | null
  asset_id?: number | null
  payload: Record<string, unknown>
}

export interface KlingLibraryItem {
  task_id: string
  task_type: 'text2video' | 'image2video'
  status: string
  video_url?: string | null
  cover_url?: string | null
  duration?: string | number | null
  created_at?: number | null
  error?: string | null
}

export interface KlingLibraryResponse {
  items: KlingLibraryItem[]
  page_num: number
  page_size: number
  task_type: 'text2video' | 'image2video'
}

const defaultBaseUrl = import.meta.env.VITE_SHOP_API_BASE ?? 'http://localhost:8010'

export function getApiBase() {
  return localStorage.getItem('shop-api-base') ?? defaultBaseUrl
}

export function setApiBase(value: string) {
  localStorage.setItem('shop-api-base', value.replace(/\/$/, ''))
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, init)
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    throw new Error(detail.detail ?? `请求失败（${response.status}）`)
  }
  return response.json() as Promise<T>
}

export const api = {
  getProduct: (id: number) => request<Product>(`/api/products/${id}`),
  createProduct: (payload: Omit<Product, 'id'>) => request<Product>('/api/products', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
  listAssets: (productId: number) => request<ProductAsset[]>(`/api/products/${productId}/assets`),
  createAsset: (productId: number, payload: { asset_type: AssetType; url: string; is_primary: boolean }) =>
    request<ProductAsset>(`/api/products/${productId}/assets`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    }),
  uploadAsset: (productId: number, file: File, assetType: AssetType, isPrimary: boolean) => {
    const form = new FormData()
    form.append('file', file)
    form.append('asset_type', assetType)
    form.append('is_primary', String(isPrimary))
    return request<ProductAsset>(`/api/products/${productId}/assets/upload`, { method: 'POST', body: form })
  },
  createStoryboard: (productId: number, title: string, scenes: Scene[]) => request<Storyboard>(`/api/products/${productId}/storyboards`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, scenes }),
  }),
  generateScenePromptReference: (productId: number, scene: Scene) => request<ScenePromptReference>(`/api/products/${productId}/scene-prompt-reference`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      scene_no: scene.scene_no,
      scene_type: scene.scene_type,
      target_duration: scene.target_duration,
      generation_strategy: scene.generation_strategy,
    }),
  }),
  getStoryboard: (id: number) => request<Storyboard>(`/api/storyboards/${id}`),
  getKlingVideoLibrary: (taskType: 'text2video' | 'image2video', pageNum = 1, pageSize = 6) =>
    request<KlingLibraryResponse>(`/api/kling-video-library?task_type=${taskType}&page_num=${pageNum}&page_size=${pageSize}`),
  queueTasks: (id: number) => request<GenerationTask[]>(`/api/storyboards/${id}/generation-tasks`, { method: 'POST' }),
  queueCandidates: (id: number, candidateCount: number, forceNew = false) => request<GenerationTask[]>(`/api/storyboards/${id}/candidate-tasks`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_count: candidateCount, force_new: forceNew }),
  }),
  listTasks: (id: number) => request<GenerationTask[]>(`/api/storyboards/${id}/generation-tasks`),
  dispatchNext: (id: number) => request<GenerationTask | { status: string; message: string }>(`/api/storyboards/${id}/dispatch-next`, { method: 'POST' }),
  refreshTask: (id: number) => request<GenerationTask>(`/api/generation-tasks/${id}/refresh`, { method: 'POST' }),
  selectCandidate: (id: number, reviewer = 'operator', note?: string) => request<GenerationTask>(`/api/generation-tasks/${id}/select`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reviewer, note }),
  }),
  qualityReview: (id: number) => request<{ task: GenerationTask; review: { summary: string; decision: string } }>(`/api/generation-tasks/${id}/quality-review`, { method: 'POST' }),
  getTrace: (id: number) => request<TraceEvent[]>(`/api/storyboards/${id}/trace`),
  importKlingVideo: (sceneId: number, taskId: string, taskType: 'text2video' | 'image2video') => request<GenerationTask>(`/api/storyboard-scenes/${sceneId}/import-kling-video`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId, task_type: taskType }),
  }),
  composeTask: (id: number) => request<GenerationTask>(`/api/generation-tasks/${id}/compose`, { method: 'POST' }),
  composeFinal: (id: number) => request<Storyboard>(`/api/storyboards/${id}/compose-final`, { method: 'POST' }),
}
