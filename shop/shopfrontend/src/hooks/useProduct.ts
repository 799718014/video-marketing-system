import { FormEvent, useMemo, useState } from 'react'
import { api, AssetType, Product, ProductAsset } from '../api'

const _assetTypes: Array<[AssetType, string]> = [
  ['main', '主图'], ['angle', '角度图'], ['detail', '细节图'], ['lifestyle', '场景图'], ['transparent', '透明底商品图'], ['logo', 'Logo'], ['scene_ref', '场景设定图'],
]

export interface UseProductReturn {
  product: Product | null
  assets: ProductAsset[]
  transparentAssets: ProductAsset[]
  logoAssets: ProductAsset[]
  assetTypes: Array<[AssetType, string]>
  productForm: { name: string; brand: string; price: string; selling_points: string }
  setProductForm: React.Dispatch<React.SetStateAction<{ name: string; brand: string; price: string; selling_points: string }>>
  assetForm: { asset_type: AssetType; url: string; is_primary: boolean }
  setAssetForm: React.Dispatch<React.SetStateAction<{ asset_type: AssetType; url: string; is_primary: boolean }>>
  assetFile: File | null
  setAssetFile: React.Dispatch<React.SetStateAction<File | null>>
  loadProductId: string
  setLoadProductId: React.Dispatch<React.SetStateAction<string>>
  createProduct: (event: FormEvent, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  loadProduct: (run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
  submitAsset: (event: FormEvent, run: (name: string, action: () => Promise<void>) => Promise<void>) => Promise<void>
}

export function useProduct(): UseProductReturn {
  const [product, setProduct] = useState<Product | null>(null)
  const [assets, setAssets] = useState<ProductAsset[]>([])
  const [productForm, setProductForm] = useState({ name: '', brand: '', price: '', selling_points: '' })
  const [assetForm, setAssetForm] = useState<{ asset_type: AssetType; url: string; is_primary: boolean }>({ asset_type: 'main', url: '', is_primary: true })
  const [assetFile, setAssetFile] = useState<File | null>(null)
  const [loadProductId, setLoadProductId] = useState('')

  const transparentAssets = useMemo(() => assets.filter((asset) => asset.asset_type === 'transparent'), [assets])
  const logoAssets = useMemo(() => assets.filter((asset) => asset.asset_type === 'logo'), [assets])

  async function syncProduct(id: number) {
    const [nextProduct, nextAssets] = await Promise.all([api.getProduct(id), api.listAssets(id)])
    setProduct(nextProduct)
    setAssets(nextAssets)
  }

  async function createProduct(event: FormEvent, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    event.preventDefault()
    await run('product', async () => {
      const created = await api.createProduct({
        name: productForm.name, brand: productForm.brand || null, price: productForm.price || null,
        specs: {}, selling_points: productForm.selling_points.split(/\n|，|,/).map((item) => item.trim()).filter(Boolean), prohibited_terms: [],
      })
      await syncProduct(created.id)
    })
  }

  async function loadProduct(run: (name: string, action: () => Promise<void>) => Promise<void>) {
    await run('load-product', async () => {
      const id = Number(loadProductId)
      if (!id) throw new Error('请输入有效的商品 ID')
      await syncProduct(id)
    })
  }

  async function submitAsset(event: FormEvent, run: (name: string, action: () => Promise<void>) => Promise<void>) {
    event.preventDefault()
    if (!product) return
    await run('asset', async () => {
      const asset = assetFile
        ? await api.uploadAsset(product.id, assetFile, assetForm.asset_type, assetForm.is_primary)
        : await api.createAsset(product.id, assetForm)
      const nextAssets = [...assets.filter((item) => !asset.is_primary || item.id !== asset.id), asset]
      setAssets(nextAssets)
      setAssetForm((form) => ({ ...form, url: '' }))
      setAssetFile(null)
    })
  }

  return {
    product, assets, transparentAssets, logoAssets,
    assetTypes: _assetTypes,
    productForm, setProductForm,
    assetForm, setAssetForm,
    assetFile, setAssetFile,
    loadProductId, setLoadProductId,
    createProduct, loadProduct, submitAsset,
  }
}
