import { FormEvent, useMemo, useState } from 'react'
import {
  api, AssetType, GenerationTask, getApiBase, PostprocessConfig, Product, ProductAsset, Scene, setApiBase, Storyboard,
} from './api'

const layerOptions = [
  ['transparent_product', '透明商品图'], ['brand_logo', '品牌 Logo'], ['subtitle', '字幕'], ['price_tag', '价格'], ['cta', 'CTA'],
] as const

const assetTypes: Array<[AssetType, string]> = [
  ['main', '主图'], ['angle', '角度图'], ['detail', '细节图'], ['lifestyle', '场景图'], ['transparent', '透明底商品图'], ['logo', 'Logo'],
]

function createDraftScene(sceneNo: number, assets: ProductAsset[]): Scene {
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
    postprocess_layers: ['transparent_product', 'brand_logo', 'subtitle', 'price_tag', 'cta'],
    postprocess_config: {
      template: 'product_promo_portrait', transparent_asset_id: transparent?.id, logo_asset_id: logo?.id, cta: '立即购买',
    },
  }
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export default function App() {
  const [apiBase, setApiBaseInput] = useState(getApiBase())
  const [product, setProduct] = useState<Product | null>(null)
  const [assets, setAssets] = useState<ProductAsset[]>([])
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null)
  const [tasks, setTasks] = useState<GenerationTask[]>([])
  const [notice, setNotice] = useState('请先创建商品并上传真实商品资产。')
  const [busy, setBusy] = useState<string | null>(null)
  const [loadProductId, setLoadProductId] = useState('')
  const [productForm, setProductForm] = useState({ name: '', brand: '', price: '', selling_points: '' })
  const [assetForm, setAssetForm] = useState<{ asset_type: AssetType; url: string; is_primary: boolean }>({ asset_type: 'main', url: '', is_primary: true })
  const [assetFile, setAssetFile] = useState<File | null>(null)
  const [storyboardTitle, setStoryboardTitle] = useState('商品短视频分镜')
  const [draftScenes, setDraftScenes] = useState<Scene[]>([])

  const transparentAssets = useMemo(() => assets.filter((asset) => asset.asset_type === 'transparent'), [assets])
  const logoAssets = useMemo(() => assets.filter((asset) => asset.asset_type === 'logo'), [assets])

  async function run(name: string, action: () => Promise<void>) {
    setBusy(name)
    try {
      await action()
    } catch (error) {
      setNotice(messageOf(error))
    } finally {
      setBusy(null)
    }
  }

  async function syncProduct(id: number) {
    const [nextProduct, nextAssets] = await Promise.all([api.getProduct(id), api.listAssets(id)])
    setProduct(nextProduct)
    setAssets(nextAssets)
    setDraftScenes((scenes) => scenes.length ? scenes : [createDraftScene(1, nextAssets)])
  }

  async function refreshBoard() {
    if (!storyboard) return
    const [nextBoard, nextTasks] = await Promise.all([api.getStoryboard(storyboard.id), api.listTasks(storyboard.id)])
    setStoryboard(nextBoard)
    setTasks(nextTasks)
  }

  function submitProduct(event: FormEvent) {
    event.preventDefault()
    void run('product', async () => {
      const created = await api.createProduct({
        name: productForm.name, brand: productForm.brand || null, price: productForm.price || null,
        specs: {}, selling_points: productForm.selling_points.split(/\n|，|,/).map((item) => item.trim()).filter(Boolean), prohibited_terms: [],
      })
      setStoryboard(null); setTasks([]); setDraftScenes([])
      await syncProduct(created.id)
      setNotice(`已创建商品「${created.name}」，请补充商品图片、透明底图和 Logo。`)
    })
  }

  function loadProduct() {
    void run('load-product', async () => {
      const id = Number(loadProductId)
      if (!id) throw new Error('请输入有效的商品 ID')
      setStoryboard(null); setTasks([]); setDraftScenes([])
      await syncProduct(id)
      setNotice('商品资产已加载。')
    })
  }

  function submitAsset(event: FormEvent) {
    event.preventDefault()
    if (!product) return setNotice('请先创建或加载商品')
    void run('asset', async () => {
      const asset = assetFile
        ? await api.uploadAsset(product.id, assetFile, assetForm.asset_type, assetForm.is_primary)
        : await api.createAsset(product.id, assetForm)
      const nextAssets = [...assets.filter((item) => !asset.is_primary || item.id !== asset.id), asset]
      setAssets(nextAssets)
      setAssetForm((form) => ({ ...form, url: '' })); setAssetFile(null)
      setNotice(`已添加${assetTypes.find(([type]) => type === asset.asset_type)?.[1] ?? '商品资产'}。`)
    })
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

  function saveStoryboard() {
    if (!product) return setNotice('请先创建或加载商品')
    void run('storyboard', async () => {
      if (!draftScenes.length || draftScenes.some((scene) => !scene.asset_id)) throw new Error('每个分镜必须选择一张真实商品图')
      const created = await api.createStoryboard(product.id, storyboardTitle, draftScenes)
      setStoryboard(created); setTasks([])
      setNotice('分镜已保存，现在可以创建图生视频任务。')
    })
  }

  function queueTasks() {
    if (!storyboard) return
    void run('queue', async () => {
      const created = await api.queueTasks(storyboard.id)
      await refreshBoard()
      setNotice(created.length ? `已创建 ${created.length} 个图生视频任务。` : '没有新增任务；已有任务仍在队列或处理中。')
    })
  }

  function dispatchNext() {
    if (!storyboard) return
    void run('dispatch', async () => {
      const result = await api.dispatchNext(storyboard.id)
      await refreshBoard()
      setNotice('message' in result ? result.message : `已提交任务 #${result.id} 至可灵。`)
    })
  }

  function refreshTask(task: GenerationTask) {
    void run(`refresh-${task.id}`, async () => {
      await api.refreshTask(task.id); await refreshBoard(); setNotice(`任务 #${task.id} 状态已刷新。`)
    })
  }

  function composeTask(task: GenerationTask) {
    void run(`compose-${task.id}`, async () => {
      await api.composeTask(task.id); await refreshBoard(); setNotice(`任务 #${task.id} 已完成确定性后期合成。`)
    })
  }

  function composeFinal() {
    if (!storyboard) return
    void run('final', async () => {
      await api.composeFinal(storyboard.id); await refreshBoard(); setNotice('最终视频已按分镜顺序合并。')
    })
  }

  const disabled = Boolean(busy)
  return <main>
    <header className="topbar">
      <div><span className="eyebrow">SHOP VIDEO STUDIO</span><h1>商品资产视频工作台</h1></div>
      <label className="api-setting">后端地址<input value={apiBase} onChange={(event) => setApiBaseInput(event.target.value)} onBlur={() => setApiBase(apiBase)} /></label>
    </header>

    <section className="notice"><strong>工作流</strong><span>真实商品资产 → 图生视频 → 确定性后期 → 最终成片</span><em>{notice}</em></section>

    <div className="workspace">
      <section className="card product-card">
        <div className="section-title"><span>01</span><div><h2>商品事实</h2><p>品牌、价格和卖点只从这里进入后期模板。</p></div></div>
        <form onSubmit={submitProduct} className="form-grid">
          <label>商品名称<input required value={productForm.name} onChange={(event) => setProductForm({ ...productForm, name: event.target.value })} placeholder="如：心形耳环" /></label>
          <label>品牌<input value={productForm.brand} onChange={(event) => setProductForm({ ...productForm, brand: event.target.value })} placeholder="如：老凤祥" /></label>
          <label>价格<input value={productForm.price} onChange={(event) => setProductForm({ ...productForm, price: event.target.value })} placeholder="如：限时 ¥299" /></label>
          <label className="wide">卖点<textarea value={productForm.selling_points} onChange={(event) => setProductForm({ ...productForm, selling_points: event.target.value })} placeholder="每行一个卖点，用于字幕默认文案" /></label>
          <button disabled={disabled}>{busy === 'product' ? '创建中…' : '创建商品'}</button>
        </form>
        <div className="load-row"><input value={loadProductId} onChange={(event) => setLoadProductId(event.target.value)} placeholder="已有商品 ID" /><button onClick={loadProduct} disabled={disabled}>加载商品</button>{product && <b>当前：#{product.id} {product.name}</b>}</div>
      </section>

      <section className="card asset-card">
        <div className="section-title"><span>02</span><div><h2>商品资产</h2><p>透明底商品图与 Logo 是 P1 后期合成的必需素材。</p></div></div>
        <form onSubmit={submitAsset} className="asset-form">
          <label>资产类型<select value={assetForm.asset_type} onChange={(event) => { const assetType = event.target.value as AssetType; setAssetForm({ ...assetForm, asset_type: assetType, is_primary: assetType === 'main' }) }}>{assetTypes.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>
          <label className="asset-url">公网 URL<input value={assetForm.url} disabled={Boolean(assetFile)} onChange={(event) => setAssetForm({ ...assetForm, url: event.target.value })} placeholder="https://cdn.example.com/product.png" /></label>
          <label className="file-input">或上传文件<input type="file" accept="image/*" onChange={(event) => setAssetFile(event.target.files?.[0] ?? null)} /></label>
          <label className="check"><input type="checkbox" checked={assetForm.is_primary} onChange={(event) => setAssetForm({ ...assetForm, is_primary: event.target.checked })} /> 设为主图</label>
          <button disabled={disabled || !product || (!assetFile && !assetForm.url)}>{busy === 'asset' ? '保存中…' : '添加资产'}</button>
        </form>
        <div className="asset-list">{assets.length ? assets.map((asset) => <article className="asset" key={asset.id}><img src={asset.url} alt={asset.asset_type} /><div><b>{assetTypes.find(([type]) => type === asset.asset_type)?.[1]}</b><small>#{asset.id}{asset.is_primary ? ' · 主图' : ''}</small></div></article>) : <p className="empty">尚未添加商品资产。</p>}</div>
      </section>

      <section className="card storyboard-card">
        <div className="section-title"><span>03</span><div><h2>分镜编辑</h2><p>模型只生成运动和场景，商品、价格与品牌由真实素材和后期模板锁定。</p></div></div>
        <label className="board-title">分镜标题<input value={storyboardTitle} onChange={(event) => setStoryboardTitle(event.target.value)} /></label>
        <div className="scene-list">{draftScenes.map((scene, index) => <article className="scene" key={index}>
          <div className="scene-head"><b>分镜 {scene.scene_no}</b><button className="text-button" onClick={() => setDraftScenes((items) => items.filter((_, itemIndex) => itemIndex !== index).map((item, itemIndex) => ({ ...item, scene_no: itemIndex + 1 })))} disabled={draftScenes.length === 1}>删除</button></div>
          <div className="form-grid compact">
            <label>商品图<select value={scene.asset_id ?? ''} onChange={(event) => updateScene(index, { asset_id: Number(event.target.value) })}><option value="">请选择</option>{assets.filter((asset) => asset.asset_type !== 'logo').map((asset) => <option value={asset.id} key={asset.id}>#{asset.id} · {asset.asset_type}</option>)}</select></label>
            <label>镜头类型<select value={scene.scene_type} onChange={(event) => updateScene(index, { scene_type: event.target.value })}><option value="product_closeup">商品特写</option><option value="product_hero">主商品展示</option><option value="lifestyle_use">场景使用</option><option value="cta">行动召唤</option></select></label>
            <label>时长<input type="number" min="1" max="5" value={scene.target_duration} onChange={(event) => updateScene(index, { target_duration: Number(event.target.value) })} /></label>
            <label className="wide">运动提示词<textarea value={scene.motion_prompt} onChange={(event) => updateScene(index, { motion_prompt: event.target.value })} /></label>
          </div>
          <div className="template-box"><b>确定性后期模板</b><div className="checks">{layerOptions.map(([value, text]) => <label key={value}><input type="checkbox" checked={scene.postprocess_layers.includes(value)} onChange={() => toggleLayer(index, value)} />{text}</label>)}</div>
            <div className="form-grid compact"><label>字幕<input value={scene.postprocess_config.subtitle ?? ''} onChange={(event) => updateConfig(index, { subtitle: event.target.value })} placeholder="默认使用第一条卖点" /></label><label>价格文字<input value={scene.postprocess_config.price_text ?? ''} onChange={(event) => updateConfig(index, { price_text: event.target.value })} placeholder="默认使用商品价格" /></label><label>CTA<input value={scene.postprocess_config.cta ?? ''} onChange={(event) => updateConfig(index, { cta: event.target.value })} /></label><label>透明商品图<select value={scene.postprocess_config.transparent_asset_id ?? ''} onChange={(event) => updateConfig(index, { transparent_asset_id: Number(event.target.value) || undefined })}><option value="">自动选择</option>{transparentAssets.map((asset) => <option key={asset.id} value={asset.id}>#{asset.id}</option>)}</select></label><label>Logo<select value={scene.postprocess_config.logo_asset_id ?? ''} onChange={(event) => updateConfig(index, { logo_asset_id: Number(event.target.value) || undefined })}><option value="">自动选择</option>{logoAssets.map((asset) => <option key={asset.id} value={asset.id}>#{asset.id}</option>)}</select></label></div>
          </div>
        </article>)}</div>
        <div className="actions"><button onClick={() => setDraftScenes((items) => [...items, createDraftScene(items.length + 1, assets)])} disabled={!product}>+ 添加分镜</button><button className="primary" onClick={saveStoryboard} disabled={disabled || !product}>{busy === 'storyboard' ? '保存中…' : '保存分镜并创建项目'}</button>{storyboard && <b>当前分镜项目 #{storyboard.id}</b>}</div>
      </section>

      <section className="card tasks-card">
        <div className="section-title"><span>04</span><div><h2>任务面板与最终预览</h2><p>先完成图生视频，再进行透明商品图与文字模板的确定性合成。</p></div></div>
        <div className="actions"><button onClick={queueTasks} disabled={!storyboard || disabled}>创建任务</button><button onClick={dispatchNext} disabled={!storyboard || disabled}>提交下一个任务</button><button onClick={() => void run('reload', async () => { await refreshBoard(); setNotice('任务状态已同步。') })} disabled={!storyboard || disabled}>刷新面板</button><button className="primary" onClick={composeFinal} disabled={!storyboard || disabled}>合并最终视频</button></div>
        <div className="task-list">{tasks.length ? tasks.map((task) => <article className="task" key={task.id}><div><b>分镜 {task.scene_no} · 任务 #{task.id}</b><p><span className={`badge ${task.status}`}>图生：{task.status}</span><span className={`badge ${task.composition_status}`}>后期：{task.composition_status ?? 'not_started'}</span></p>{(task.error || task.composition_error) && <p className="error">{task.error || task.composition_error}</p>}<div className="task-actions"><button onClick={() => refreshTask(task)} disabled={disabled}>查询图生状态</button><button onClick={() => composeTask(task)} disabled={disabled || !task.video_url}>后期合成</button></div></div>{(task.composed_video_url || task.video_url) && <video controls src={task.composed_video_url || task.video_url || undefined} />}</article>) : <p className="empty">保存分镜后，可在这里创建和管理任务。</p>}</div>
        {storyboard?.final_video_url && <div className="final-video"><div><span className="eyebrow">PUBLISH READY</span><h3>最终成片</h3><a href={storyboard.final_video_url} target="_blank" rel="noreferrer">打开/下载视频</a></div><video controls src={storyboard.final_video_url} /></div>}
      </section>
    </div>
  </main>
}
