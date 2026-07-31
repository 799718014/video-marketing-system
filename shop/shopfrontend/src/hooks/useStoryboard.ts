import { useEffect, useState } from 'react'
import { api, GenerationTask, KlingLibraryItem, PostprocessConfig, ProductAsset, Scene, SceneReference, Storyboard, TraceEvent } from '../api'

export interface UseStoryboardInput {
  productId: number | null
  assets: ProductAsset[]
}

export function createDraftScene(sceneNo: number, assets: ProductAsset[]): Scene {
  const main = assets.find((asset) => Boolean(asset.is_primary)) ?? assets.find((asset) => asset.asset_type === 'main')
  const transparent = assets.find((asset) => asset.asset_type === 'transparent')
  const logo = assets.find((asset) => asset.asset_type === 'logo')
  return {
    scene_no: sceneNo,
    scene_type: 'product_closeup',
    target_duration: 5,
    asset_id: main?.id,
    generation_strategy: 'image_to_video',
    motion_prompt: '镜头缓慢推进，保持商品形状、材质、颜色和比例不变，突出真实商品细节。',
    identity_constraints: ['保持参考图中商品的形状、材质、颜色和比例', '不得增加、删除或替换商品部件'],
    reference_assets: main ? [{ asset_id: main.id, role: 'identity', sort_order: 0 }] : [],
    postprocess_layers: ['transparent_product', 'brand_logo', 'subtitle', 'price_tag', 'cta'],
    postprocess_config: {
      template: 'product_promo_portrait', transparent_asset_id: transparent?.id, logo_asset_id: logo?.id, cta: '立即购买',
    },
  }
}

export interface UseStoryboardReturn {
  storyboard: Storyboard | null
  tasks: GenerationTask[]
  traceEvents: TraceEvent[]
  draftScenes: Scene[]
  storyboardTitle: string
  setStoryboardTitle: React.Dispatch<React.SetStateAction<string>>
  candidateCount: number
  setCandidateCount: React.Dispatch<React.SetStateAction<number>>
  libraryType: 'text2video' | 'image2video'
  setLibraryType: React.Dispatch<React.SetStateAction<'text2video' | 'image2video'>>
  libraryItems: KlingLibraryItem[]
  setLibraryItems: React.Dispatch<React.SetStateAction<KlingLibraryItem[]>>
  libraryPage: number
  setLibraryPage: React.Dispatch<React.SetStateAction<number>>
  libraryTargetSceneId: number | null
  setLibraryTargetSceneId: React.Dispatch<React.SetStateAction<number | null>>
  setStoryboard: React.Dispatch<React.SetStateAction<Storyboard | null>>
  setTasks: React.Dispatch<React.SetStateAction<GenerationTask[]>>
  setDraftScenes: React.Dispatch<React.SetStateAction<Scene[]>>
  updateScene: (index: number, patch: Partial<Scene>) => void
  updateConfig: (index: number, patch: Partial<PostprocessConfig>) => void
  toggleLayer: (index: number, layer: string) => void
  toggleReference: (index: number, asset: ProductAsset) => void
  selectMainAsset: (index: number, assetId: number) => void
  updateReferenceRole: (index: number, assetId: number, role: SceneReference['role']) => void
  saveStoryboard: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  refreshBoard: () => Promise<void>
  queueTasks: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  queueCandidates: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  dispatchNext: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  refreshTask: (task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  composeTask: (task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  selectCandidate: (task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  qualityReview: (task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  loadTrace: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  composeFinal: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  loadKlingLibrary: (page: number, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  importLibraryVideo: (item: KlingLibraryItem, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
}

export function useStoryboard({ productId, assets }: UseStoryboardInput): UseStoryboardReturn {
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null)
  const [tasks, setTasks] = useState<GenerationTask[]>([])
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])
  const [storyboardTitle, setStoryboardTitle] = useState('商品短视频分镜')
  const [draftScenes, setDraftScenes] = useState<Scene[]>([])
  const [candidateCount, setCandidateCount] = useState(3)
  const [libraryType, setLibraryType] = useState<'text2video' | 'image2video'>('image2video')
  const [libraryItems, setLibraryItems] = useState<KlingLibraryItem[]>([])
  const [libraryPage, setLibraryPage] = useState(1)
  const [libraryTargetSceneId, setLibraryTargetSceneId] = useState<number | null>(null)

  // 当 product 变化时重置分镜和相关状态
  useEffect(() => {
    setStoryboard(null)
    setTasks([])
    setTraceEvents([])
    setDraftScenes(assets.length ? [createDraftScene(1, assets)] : [])
    setLibraryItems([])
  }, [productId])

  // assets 变化时，如果还没有草稿分镜则初始化
  useEffect(() => {
    if (assets.length && !draftScenes.length && !storyboard) {
      setDraftScenes([createDraftScene(1, assets)])
    }
  }, [assets])

  async function refreshBoard() {
    if (!storyboard) return
    const [nextBoard, nextTasks] = await Promise.all([api.getStoryboard(storyboard.id), api.listTasks(storyboard.id)])
    setStoryboard(nextBoard)
    setTasks(nextTasks)
  }

  function updateScene(index: number, patch: Partial<Scene>) {
    setDraftScenes((scenes) => scenes.map((scene, sceneIndex) => sceneIndex === index ? { ...scene, ...patch } : scene))
  }

  function updateConfig(index: number, patch: Partial<PostprocessConfig>) {
    updateScene(index, { postprocess_config: { ...draftScenes[index].postprocess_config, ...patch } })
  }

  function toggleLayer(index: number, layer: string) {
    const scene = draftScenes[index]
    const enabled = scene.postprocess_layers.includes(layer)
    updateScene(index, { postprocess_layers: enabled ? scene.postprocess_layers.filter((item) => item !== layer) : [...scene.postprocess_layers, layer] })
  }

  function toggleReference(index: number, asset: ProductAsset) {
    const scene = draftScenes[index]
    const exists = scene.reference_assets.some((reference) => reference.asset_id === asset.id)
    const referenceAssets: SceneReference[] = exists
      ? scene.reference_assets.filter((reference) => reference.asset_id !== asset.id)
      : [...scene.reference_assets, { asset_id: asset.id, role: asset.id === scene.asset_id ? 'identity' : 'detail', sort_order: scene.reference_assets.length }]
    updateScene(index, { reference_assets: referenceAssets })
  }

  function updateReferenceRole(index: number, assetId: number, role: SceneReference['role']) {
    const referenceAssets = draftScenes[index].reference_assets.map((reference) => reference.asset_id === assetId ? { ...reference, role } : reference)
    updateScene(index, { reference_assets: referenceAssets })
  }

  function selectMainAsset(index: number, assetId: number) {
    const scene = draftScenes[index]
    const existing = scene.reference_assets.filter((reference) => reference.asset_id !== assetId)
    updateScene(index, {
      asset_id: assetId,
      reference_assets: [{ asset_id: assetId, role: 'identity', sort_order: 0 }, ...existing.map((reference, sortOrder) => ({ ...reference, sort_order: sortOrder + 1 }))],
    })
  }

  async function saveStoryboard(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run('storyboard', async () => {
      if (!draftScenes.length || draftScenes.some((scene) => !scene.asset_id)) throw new Error('每个分镜必须选择一张真实商品图')
      const created = await api.createStoryboard(productId!, storyboardTitle, draftScenes)
      setStoryboard(created)
      setTasks([])
    })
  }

  async function queueTasks(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    if (!storyboard) return
    await run('queue', async () => {
      const created = await api.queueTasks(storyboard.id)
      await refreshBoard()
    })
  }

  async function queueCandidates(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    if (!storyboard) return
    await run('candidates', async () => {
      const created = await api.queueCandidates(storyboard.id, candidateCount)
      await refreshBoard()
    })
  }

  async function dispatchNext(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    if (!storyboard) return
    await run('dispatch', async () => {
      const result = await api.dispatchNext(storyboard.id)
      await refreshBoard()
    })
  }

  async function refreshTask(task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run(`refresh-${task.id}`, async () => {
      await api.refreshTask(task.id)
      await refreshBoard()
    })
  }

  async function composeTask(task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run(`compose-${task.id}`, async () => {
      await api.composeTask(task.id)
      await refreshBoard()
    })
  }

  async function selectCandidate(task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run(`select-${task.id}`, async () => {
      await api.selectCandidate(task.id)
      await refreshBoard()
    })
  }

  async function qualityReview(task: GenerationTask, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run(`quality-${task.id}`, async () => {
      const result = await api.qualityReview(task.id)
      await refreshBoard()
    })
  }

  async function loadTrace(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    if (!storyboard) return
    await run('trace', async () => {
      const events = await api.getTrace(storyboard.id)
      setTraceEvents(events)
    })
  }

  async function composeFinal(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    if (!storyboard) return
    await run('final', async () => {
      await api.composeFinal(storyboard.id)
      await refreshBoard()
    })
  }

  async function loadKlingLibrary(page: number, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run('library', async () => {
      const result = await api.getKlingVideoLibrary(libraryType, page)
      setLibraryItems(result.items)
      setLibraryPage(page)
    })
  }

  async function importLibraryVideo(item: KlingLibraryItem, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    const sceneId = libraryTargetSceneId ?? storyboard?.scenes[0]?.id
    if (!sceneId) return
    await run(`import-${item.task_id}`, async () => {
      await api.importKlingVideo(sceneId, item.task_id, item.task_type)
      await refreshBoard()
    })
  }

  return {
    storyboard, tasks, traceEvents, draftScenes,
    storyboardTitle, setStoryboardTitle,
    candidateCount, setCandidateCount,
    libraryType, setLibraryType, libraryItems, setLibraryItems, libraryPage, setLibraryPage,
    libraryTargetSceneId, setLibraryTargetSceneId,
    setStoryboard, setTasks, setDraftScenes,
    updateScene, updateConfig, toggleLayer, toggleReference, selectMainAsset, updateReferenceRole,
    saveStoryboard, refreshBoard, queueTasks, queueCandidates, dispatchNext,
    refreshTask, composeTask, selectCandidate, qualityReview,
    loadTrace, composeFinal,
    loadKlingLibrary, importLibraryVideo,
  }
}
