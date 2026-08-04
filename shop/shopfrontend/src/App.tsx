import { useState } from 'react'
import { ProductAsset, SceneReference, getApiBase, setApiBase } from './api'
import { useOperation } from './hooks/useOperation'
import { useProduct } from './hooks/useProduct'
import { useStoryboard, createDraftScene } from './hooks/useStoryboard'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ProductCard } from './components/ProductCard'
import { AssetPanel } from './components/AssetPanel'
import { TaskDashboard } from './components/TaskDashboard'

const layerOptions = [
  ['transparent_product', '透明商品图'], ['brand_logo', '品牌 Logo'], ['subtitle', '字幕'], ['price_tag', '价格'], ['cta', 'CTA'],
] as const

export default function App() {
  const [apiBase, setApiBaseInput] = useState(getApiBase())
  const op = useOperation()
  const prod = useProduct()
  const board = useStoryboard({ productId: prod.product?.id ?? null, assets: prod.assets })

  const { busy, notice, setNotice } = op
  const { product, assets, transparentAssets, logoAssets, assetTypes } = prod
  const {
    storyboard, draftScenes, setDraftScenes, storyboardTitle, setStoryboardTitle,
    updateScene, updateConfig, toggleLayer, toggleReference, selectMainAsset, generatePromptReference, updateReferenceRole,
    saveStoryboard,
  } = board
  const disabled = Boolean(busy)

  function doSaveStoryboard() {
    if (!product) return setNotice('请先创建或加载商品')
    void saveStoryboard(run)
      .then(() => setNotice('分镜已保存，现在可以创建图生视频任务。'))
      .catch(() => undefined)
  }

  // run 不需要重新定义，直接使用 op.run
  const { run } = op

  return <main>
    <header className="topbar">
      <div><span className="eyebrow">SHOP VIDEO STUDIO</span><h1>商品资产视频工作台</h1></div>
      <label className="api-setting">后端地址<input value={apiBase} onChange={(event) => setApiBaseInput(event.target.value)} onBlur={() => setApiBase(apiBase)} /></label>
    </header>

    <section className="notice"><strong>工作流</strong><span>真实商品资产 → 图生视频 → 确定性后期 → 最终成片</span><em>{notice}</em></section>

    <div className="workspace">
      <ErrorBoundary>
        <ProductCard op={op} prod={prod} />
      </ErrorBoundary>

      <ErrorBoundary>
        <AssetPanel op={op} prod={prod} />
      </ErrorBoundary>

      <ErrorBoundary>
        <section className="card storyboard-card">
          <div className="section-title"><span>03</span><div><h2>分镜编辑</h2><p>模型只生成运动和场景，商品、价格与品牌由真实素材和后期模板锁定。</p></div></div>
          <label className="board-title">分镜标题<input value={storyboardTitle} onChange={(event) => setStoryboardTitle(event.target.value)} /></label>
          <div className="scene-list">{draftScenes.map((scene, index) => <article className="scene" key={index}>
            <div className="scene-head"><b>分镜 {scene.scene_no}</b><button className="text-button" onClick={() => setDraftScenes((items) => items.filter((_, itemIndex) => itemIndex !== index).map((item, itemIndex) => ({ ...item, scene_no: itemIndex + 1 })))} disabled={draftScenes.length === 1}>删除</button></div>
            <div className="form-grid compact">
              <label>商品主图<select value={scene.asset_id ?? ''} onChange={(event) => selectMainAsset(index, Number(event.target.value))}><option value="">请选择</option>{assets.filter((asset) => asset.asset_type !== 'logo').map((asset) => <option value={asset.id} key={asset.id}>#{asset.id} · {asset.asset_type}</option>)}</select></label>
              <label>镜头类型<select value={scene.scene_type} onChange={(event) => updateScene(index, { scene_type: event.target.value })}><option value="product_closeup">商品特写</option><option value="product_hero">主商品展示</option><option value="lifestyle_use">使用场景</option><option value="atmosphere">氛围场景</option><option value="cta">行动召唤</option></select></label>
              <label>时长<input type="number" min="1" max="5" value={scene.target_duration} onChange={(event) => updateScene(index, { target_duration: Number(event.target.value) })} /></label>
              <div className="scene-prompt-heading wide">
                <div><b>分镜参考稿</b><p>AI 可生成初稿；生成后均可手动修改。仅 AI Prompt 会提交给视频模型。</p></div>
                <button type="button" onClick={() => { void generatePromptReference(index, run).then(() => setNotice(`分镜 ${scene.scene_no} 的 AI 参考稿已生成，可继续修改。`)).catch(() => undefined) }} disabled={disabled || !product}>
                  {busy === `prompt-reference-${scene.scene_no}` ? '生成中…' : 'AI 生成参考稿'}
                </button>
              </div>
              <label className="wide">A-Roll 旁白/逐字稿（TTS 使用）<textarea value={scene.narration ?? ''} onChange={(event) => updateScene(index, { narration: event.target.value })} placeholder="例如：细节到位，质感自然呈现。" /></label>
              <label className="wide">B-Roll 画面描述（人类理解）<textarea value={scene.visual_description ?? ''} onChange={(event) => updateScene(index, { visual_description: event.target.value })} placeholder="描述主体、动作、场景、镜头和光线，便于审核。" /></label>
              <label className="wide">AI 视频/图片 Prompt（AI 生成）<textarea value={scene.ai_prompt ?? scene.scene_prompt ?? scene.motion_prompt} onChange={(event) => updateScene(index, { ai_prompt: event.target.value, motion_prompt: event.target.value, scene_prompt: event.target.value })} placeholder="直接提交给可灵：主体、动作、镜头、光线和限制条件。" /></label>
            </div>
            <div className="reference-box"><b>P2 多参考图 / 元素一致性</b><p>主图作为 identity 参考；可增加细节、材质、元素和场景设定图（scene_setting 用于 text_to_video 使用场景），候选任务会保存完整参考清单。</p><div className="reference-grid">{assets.filter((asset) => asset.asset_type !== 'transparent').map((asset) => { const reference = scene.reference_assets.find((item) => item.asset_id === asset.id); return <div className="reference-item" key={asset.id}><label><input type="checkbox" checked={Boolean(reference)} onChange={() => toggleReference(index, asset)} />#{asset.id} · {asset.asset_type}</label>{reference && <select value={reference.role} onChange={(event) => updateReferenceRole(index, asset.id, event.target.value as SceneReference['role'])}><option value="identity">身份</option><option value="material">材质</option><option value="detail">细节</option><option value="element">元素</option><option value="logo">Logo</option><option value="scene_setting">场景设定</option></select>}</div> })}</div></div>
            <div className="template-box"><b>确定性后期模板</b><div className="checks">{layerOptions.map(([value, text]) => <label key={value}><input type="checkbox" checked={scene.postprocess_layers.includes(value)} onChange={() => toggleLayer(index, value)} />{text}</label>)}</div>
              <div className="form-grid compact"><label>字幕<input value={scene.postprocess_config.subtitle ?? ''} onChange={(event) => updateConfig(index, { subtitle: event.target.value })} placeholder="默认使用第一条卖点" /></label><label>价格文字<input value={scene.postprocess_config.price_text ?? ''} onChange={(event) => updateConfig(index, { price_text: event.target.value })} placeholder="默认使用商品价格" /></label><label>CTA<input value={scene.postprocess_config.cta ?? ''} onChange={(event) => updateConfig(index, { cta: event.target.value })} /></label><label>透明商品图<select value={scene.postprocess_config.transparent_asset_id ?? ''} onChange={(event) => updateConfig(index, { transparent_asset_id: Number(event.target.value) || undefined })}><option value="">自动选择</option>{transparentAssets.map((asset) => <option key={asset.id} value={asset.id}>#{asset.id}</option>)}</select></label><label>Logo<select value={scene.postprocess_config.logo_asset_id ?? ''} onChange={(event) => updateConfig(index, { logo_asset_id: Number(event.target.value) || undefined })}><option value="">自动选择</option>{logoAssets.map((asset) => <option key={asset.id} value={asset.id}>#{asset.id}</option>)}</select></label></div>
            </div>
          </article>)}</div>
          <div className="actions"><button onClick={() => setDraftScenes((items) => [...items, createDraftScene(items.length + 1, assets)])} disabled={!product}>+ 添加分镜</button><button className="primary" onClick={doSaveStoryboard} disabled={disabled || !product}>{busy === 'storyboard' ? '保存中…' : '保存分镜并创建项目'}</button>{storyboard && <b>当前分镜项目 #{storyboard.id}</b>}</div>
        </section>
      </ErrorBoundary>

      <ErrorBoundary>
        <TaskDashboard op={op} prod={prod} board={board} />
      </ErrorBoundary>
    </div>
  </main>
}
