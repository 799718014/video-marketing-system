import { FormEvent } from 'react'
import { OperationHandle } from '../hooks/useOperation'
import { UseProductReturn } from '../hooks/useProduct'
import { AssetType } from '../api'

interface Props {
  op: OperationHandle
  prod: UseProductReturn
}

export function AssetPanel({ op, prod }: Props) {
  const { busy, run, setNotice } = op
  const { product, assets, assetTypes, assetForm, setAssetForm, assetFile, setAssetFile, submitAsset } = prod
  const disabled = Boolean(busy)

  function doSubmitAsset(event: FormEvent) {
    if (!product) return setNotice('请先创建或加载商品')
    void submitAsset(event, run)
      .then(() => setNotice(`已添加${assetTypes.find(([type]) => type === assetForm.asset_type)?.[1] ?? '商品资产'}。`))
      .catch(() => undefined)
  }

  return (
    <section className="card asset-card">
      <div className="section-title"><span>02</span><div><h2>商品资产</h2><p>透明底商品图与 Logo 是 P1 后期合成的必需素材。</p></div></div>
      <form onSubmit={doSubmitAsset} className="asset-form">
        <label>资产类型<select value={assetForm.asset_type} onChange={(event) => { const assetType = event.target.value as AssetType; setAssetForm({ ...assetForm, asset_type: assetType, is_primary: assetType === 'main' }) }}>{assetTypes.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>
        <label className="asset-url">公网 URL<input value={assetForm.url} disabled={Boolean(assetFile)} onChange={(event) => setAssetForm({ ...assetForm, url: event.target.value })} placeholder="https://cdn.example.com/product.png" /></label>
        <label className="file-input">或上传文件<input type="file" accept="image/*" onChange={(event) => setAssetFile(event.target.files?.[0] ?? null)} /></label>
        <label className="check"><input type="checkbox" checked={assetForm.is_primary} onChange={(event) => setAssetForm({ ...assetForm, is_primary: event.target.checked })} /> 设为主图</label>
        <button disabled={disabled || !product || (!assetFile && !assetForm.url)}>{busy === 'asset' ? '保存中…' : '添加资产'}</button>
      </form>
      <div className="asset-list">
        {assets.length ? assets.map((asset) => <article className="asset" key={asset.id}><img src={asset.url} alt={asset.asset_type} /><div><b>{assetTypes.find(([type]) => type === asset.asset_type)?.[1]}</b><small>#{asset.id}{asset.is_primary ? ' · 主图' : ''}</small></div></article>) : <p className="empty">尚未添加商品资产。</p>}
      </div>
    </section>
  )
}
