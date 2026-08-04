import { FormEvent } from 'react'
import { OperationHandle } from '../hooks/useOperation'
import { UseProductReturn } from '../hooks/useProduct'

interface Props {
  op: OperationHandle
  prod: UseProductReturn
}

export function ProductCard({ op, prod }: Props) {
  const { busy, notice, run, setNotice } = op
  const { product, productForm, setProductForm, loadProductId, setLoadProductId, createProduct, loadProduct } = prod
  const disabled = Boolean(busy)

  function submitProduct(event: FormEvent) {
    void createProduct(event, run)
      .then(() => setNotice(`已创建商品「${productForm.name}」，请补充商品图片、透明底图和 Logo。`))
      .catch(() => undefined)
  }

  function doLoadProduct() {
    void loadProduct(run).then(() => setNotice('商品资产已加载。')).catch(() => undefined)
  }

  return (
    <section className="card product-card">
      <div className="section-title"><span>01</span><div><h2>商品事实</h2><p>品牌、价格和卖点只从这里进入后期模板。</p></div></div>
      <form onSubmit={submitProduct} className="form-grid">
        <label>商品名称<input required value={productForm.name} onChange={(event) => setProductForm({ ...productForm, name: event.target.value })} placeholder="如：心形耳环" /></label>
        <label>品牌<input value={productForm.brand} onChange={(event) => setProductForm({ ...productForm, brand: event.target.value })} placeholder="如：老凤祥" /></label>
        <label>价格<input value={productForm.price} onChange={(event) => setProductForm({ ...productForm, price: event.target.value })} placeholder="如：限时 ¥299" /></label>
        <label className="wide">卖点<textarea value={productForm.selling_points} onChange={(event) => setProductForm({ ...productForm, selling_points: event.target.value })} placeholder="每行一个卖点，用于字幕默认文案" /></label>
        <button disabled={disabled}>{busy === 'product' ? '创建中…' : '创建商品'}</button>
      </form>
      <div className="load-row">
        <input value={loadProductId} onChange={(event) => setLoadProductId(event.target.value)} placeholder="已有商品 ID" />
        <button onClick={doLoadProduct} disabled={disabled}>加载商品</button>
        {product && <b>当前：#{product.id} {product.name}</b>}
      </div>
    </section>
  )
}
