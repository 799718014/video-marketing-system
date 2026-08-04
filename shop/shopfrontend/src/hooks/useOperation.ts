import { useState } from 'react'

export interface OperationHandle {
  busy: string | null
  notice: string
  run: (name: string, action: () => Promise<void>) => Promise<void>
  setNotice: (msg: string) => void
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export function useOperation(): OperationHandle {
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState('请先创建商品并上传真实商品资产。')

  async function run(name: string, action: () => Promise<void>) {
    setBusy(name)
    try {
      await action()
    } catch (error) {
      setNotice(messageOf(error))
      // 调用方只有在操作真实完成后才应展示成功提示。
      throw error
    } finally {
      setBusy(null)
    }
  }

  return { busy, notice, run, setNotice }
}
