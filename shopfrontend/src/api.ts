export type AssetType = 'main' | 'angle' | 'detail' | 'lifestyle' | 'transparent' | 'logo'

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

export interface Scene {
  id?: number
  scene_no: number
  scene_type: string
  target_duration: number
  asset_id?: number
  asset_url?: string
  generation_strategy: 'image_to_video'
  motion_prompt: string
  identity_constraints: string[]
  postprocess_layers: string[]
  postprocess_config: PostprocessConfig
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
  error?: string | null
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
  getStoryboard: (id: number) => request<Storyboard>(`/api/storyboards/${id}`),
  queueTasks: (id: number) => request<GenerationTask[]>(`/api/storyboards/${id}/generation-tasks`, { method: 'POST' }),
  listTasks: (id: number) => request<GenerationTask[]>(`/api/storyboards/${id}/generation-tasks`),
  dispatchNext: (id: number) => request<GenerationTask | { status: string; message: string }>(`/api/storyboards/${id}/dispatch-next`, { method: 'POST' }),
  refreshTask: (id: number) => request<GenerationTask>(`/api/generation-tasks/${id}/refresh`, { method: 'POST' }),
  composeTask: (id: number) => request<GenerationTask>(`/api/generation-tasks/${id}/compose`, { method: 'POST' }),
  composeFinal: (id: number) => request<Storyboard>(`/api/storyboards/${id}/compose-final`, { method: 'POST' }),
}
