import { useEffect, useMemo, useState } from 'react'
import { OperationHandle } from '../hooks/useOperation'
import { UseProductReturn } from '../hooks/useProduct'
import { UseStoryboardReturn } from '../hooks/useStoryboard'
import { GenerationTask, KlingLibraryItem } from '../api'

interface Props {
  op: OperationHandle
  prod: UseProductReturn
  board: UseStoryboardReturn
}

const activeGenerationStatuses = new Set(['queued', 'submitted', 'processing', 'pending'])

function elapsedLabel(startedAt?: string, now = Date.now()) {
  if (!startedAt) return '刚刚开始'
  const timestamp = Date.parse(startedAt.replace(' ', 'T'))
  if (Number.isNaN(timestamp)) return '生成中'
  const elapsedSeconds = Math.max(0, Math.floor((now - timestamp) / 1000))
  const minutes = Math.floor(elapsedSeconds / 60)
  const seconds = elapsedSeconds % 60
  return minutes ? `已等待 ${minutes} 分 ${seconds} 秒` : `已等待 ${seconds} 秒`
}

export function TaskDashboard({ op, prod: _prod, board }: Props) {
  const { busy, run, setNotice } = op
  const {
    storyboard, tasks, traceEvents, draftScenes: _ds,
    candidateCount, setCandidateCount,
    libraryType, setLibraryType, libraryItems, setLibraryItems, libraryPage, setLibraryPage,
    libraryTargetSceneId, setLibraryTargetSceneId,
    queueTasks, queueCandidates, dispatchNext, refreshBoard,
    refreshTask, composeTask, selectCandidate, qualityReview,
    loadTrace, composeFinal,
    loadKlingLibrary, importLibraryVideo,
  } = board

  const [now, setNow] = useState(() => Date.now())
  const activeTasks = useMemo(
    () => tasks.filter((task) => activeGenerationStatuses.has(task.status.toLowerCase()) && !task.video_url),
    [tasks],
  )
  const activeScenes = useMemo(() => {
    if (!storyboard) return []
    return storyboard.scenes.flatMap((scene) => {
      const sceneTasks = activeTasks.filter((task) => task.scene_id === scene.id)
      return sceneTasks.length ? [{ scene, tasks: sceneTasks }] : []
    })
  }, [activeTasks, storyboard])
  const incompleteCompositionScenes = useMemo(() => {
    if (!storyboard) return []
    return storyboard.scenes
      .filter((scene) => !tasks.some((task) => (
        task.scene_id === scene.id
        && Boolean(task.selected)
        && task.composition_status === 'succeeded'
        && Boolean(task.composed_video_url)
      )))
      .map((scene) => scene.scene_no)
  }, [storyboard, tasks])

  useEffect(() => {
    if (!activeTasks.length) return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [activeTasks.length])

  useEffect(() => {
    if (!storyboard || !activeTasks.length) return
    const timer = window.setInterval(() => {
      void refreshBoard().catch(() => undefined)
    }, 15_000)
    return () => window.clearInterval(timer)
  }, [storyboard?.id, activeTasks.length])

  const disabled = Boolean(busy)

  function doQueueTasks() {
    if (!storyboard) return
    void queueTasks(run).then(() => setNotice('已创建图生视频任务。')).catch(() => undefined)
  }

  function doQueueCandidates() {
    if (!storyboard) return
    void queueCandidates(run).then(() => setNotice('候选任务已创建，请逐个提交并选片。')).catch(() => undefined)
  }

  function doDispatchNext() {
    if (!storyboard) return
    void dispatchNext(run).then(() => setNotice('后台 Worker 已唤醒。')).catch(() => undefined)
  }

  function doReload() {
    void run('reload', async () => { await refreshBoard(); setNotice('任务状态已同步。') })
  }

  function doLoadTrace() {
    void loadTrace(run).then(() => setNotice(`已加载追溯事件。`)).catch(() => undefined)
  }

  function doComposeFinal() {
    if (!storyboard) return
    if (incompleteCompositionScenes.length) {
      setNotice(`请先完成分镜 ${incompleteCompositionScenes.join('、')} 的选片和后期合成。`)
      return
    }
    void composeFinal(run).then(() => setNotice('最终视频已按分镜顺序合并。')).catch(() => undefined)
  }

  function doLoadLibrary(page = libraryPage) {
    void loadKlingLibrary(page, run).then(() => setNotice(`已加载可灵视频库第 ${page} 页。`)).catch(() => undefined)
  }

  function doImportLibrary(item: KlingLibraryItem) {
    const sceneId = libraryTargetSceneId ?? storyboard?.scenes[0]?.id
    if (!sceneId) return setNotice('请先保存分镜，并选择要导入的视频目标分镜。')
    void importLibraryVideo(item, run)
      .then(() => setNotice(`已将可灵任务 ${item.task_id} 导入为候选片段，请完成质检和选片。`))
      .catch(() => undefined)
  }

  return (
    <section className="card tasks-card">
      <div className="section-title"><span>04</span><div><h2>P2 候选评审、质检与最终预览</h2><p>候选片段经人工选片和商品一致性质检后，再进入确定性后期及最终合并。</p></div></div>
      <div className="actions">
        <button onClick={doQueueTasks} disabled={!storyboard || disabled}>创建单任务</button>
        <label className="candidate-count">候选数<select value={candidateCount} onChange={(event) => setCandidateCount(Number(event.target.value))}><option value={2}>2</option><option value={3}>3</option><option value={4}>4</option></select></label>
        <button onClick={doQueueCandidates} disabled={!storyboard || disabled}>生成候选片段</button>
        <button onClick={doDispatchNext} disabled={!storyboard || disabled}>提交下一个任务</button>
        <button onClick={doReload} disabled={!storyboard || disabled}>刷新面板</button>
        <button onClick={doLoadTrace} disabled={!storyboard || disabled}>查看追溯</button>
        <button
          className="primary"
          onClick={doComposeFinal}
          disabled={!storyboard || disabled || incompleteCompositionScenes.length > 0}
          title={incompleteCompositionScenes.length ? `请先完成分镜 ${incompleteCompositionScenes.join('、')} 的后期合成` : undefined}
        >合并最终视频</button>
      </div>

      {storyboard && incompleteCompositionScenes.length > 0 && (
        <p className="composition-readiness" role="status">
          请先对已选片段执行“后期合成”：分镜 {incompleteCompositionScenes.join('、')}。
        </p>
      )}

      {activeScenes.length > 0 && <div className="generation-status" role="status" aria-live="polite">
        <div><b>正在生成</b><small>每 15 秒自动同步状态</small></div>
        <div className="generation-status-list">
          {activeScenes.map(({ scene, tasks: sceneTasks }) => {
            const startedAt = sceneTasks.reduce<string | undefined>((earliest, task) => {
              if (!earliest || (task.created_at && task.created_at < earliest)) return task.created_at
              return earliest
            }, undefined)
            return <div className="generation-status-item" key={scene.id}>
              <span className="generation-spinner" aria-hidden="true" />
              <strong>分镜 {scene.scene_no} 正在生成</strong>
              <span>{sceneTasks.length} 个候选任务 · {elapsedLabel(startedAt, now)}</span>
            </div>
          })}
        </div>
      </div>}

      {/* 可灵视频库候选导入 */}
      <div className="library-panel">
        <div><b>可灵视频库候选导入</b><p>仅可导入当前可灵账号中已完成的视频；导入后仍需质检和人工选片，视频链接过期时请刷新或重新导入。</p></div>
        <div className="library-toolbar">
          <label>类型<select value={libraryType} onChange={(event) => { setLibraryType(event.target.value as 'text2video' | 'image2video'); setLibraryPage(1); setLibraryItems([]) }}><option value="image2video">图生视频</option><option value="text2video">文生视频</option></select></label>
          <label>导入到分镜<select value={libraryTargetSceneId ?? ''} onChange={(event) => setLibraryTargetSceneId(Number(event.target.value) || null)}><option value="">请选择分镜</option>{storyboard?.scenes.map((scene) => <option key={scene.id} value={scene.id}>分镜 {scene.scene_no}</option>)}</select></label>
          <button onClick={() => doLoadLibrary(1)} disabled={!storyboard || disabled}>加载可灵视频库</button>
        </div>
        {libraryItems.length > 0 && <>
          <div className="library-list">{libraryItems.map((item) => <article key={`${item.task_type}-${item.task_id}`}><video controls preload="metadata" src={item.video_url ?? undefined} poster={item.cover_url ?? undefined} /><b>{item.status === 'succeed' || item.status === 'succeeded' ? '已完成' : item.status}</b><small>{item.task_id}</small><button onClick={() => doImportLibrary(item)} disabled={disabled || !item.video_url || !libraryTargetSceneId}>导入为候选</button></article>)}</div>
          <div className="library-pagination"><button onClick={() => doLoadLibrary(libraryPage - 1)} disabled={disabled || libraryPage === 1}>上一页</button><span>第 {libraryPage} 页</span><button onClick={() => doLoadLibrary(libraryPage + 1)} disabled={disabled || libraryItems.length < 6}>下一页</button></div>
        </>}
      </div>

      {/* 任务列表 */}
      <div className="task-list">
        {tasks.length ? tasks.map((task) => (
          <article className={`task ${task.selected ? 'selected-task' : ''}`} key={task.id}>
            <div>
              <b>分镜 {task.scene_no} · 候选 {task.candidate_index ?? 1} · 任务 #{task.id}</b>
              <p>
                <span className={`badge ${task.status}`}>图生：{activeGenerationStatuses.has(task.status.toLowerCase()) ? '生成中' : task.status}</span>
                <span className={`badge ${task.composition_status}`}>后期：{task.composition_status ?? 'not_started'}</span>
                <span className={`badge ${task.quality_status}`}>质检：{task.quality_status ?? 'not_checked'}{task.quality_decision ? ` / ${task.quality_decision}` : ''}</span>
                {task.selected && <span className="badge succeeded">已选片</span>}
              </p>
              {task.reference_manifest?.length ? <p className="reference-summary">参考图：{task.reference_manifest.map((reference) => `${reference.role}#${reference.asset_id}`).join(' · ')}</p> : null}
              {(task.error || task.composition_error) && <p className="error">{task.error || task.composition_error}</p>}
              <div className="task-actions">
                <button onClick={() => refreshTask(task, run)} disabled={disabled}>查询图生状态</button>
                <button onClick={() => qualityReview(task, run)} disabled={disabled || !task.video_url}>商品/Logo/OCR 质检</button>
                <button onClick={() => selectCandidate(task, run)} disabled={disabled || !task.video_url}>选此片段</button>
                <button onClick={() => composeTask(task, run)} disabled={disabled || !task.video_url}>后期合成</button>
              </div>
            </div>
            {(task.composed_video_url || task.video_url) && <video controls src={task.composed_video_url || task.video_url || undefined} />}
          </article>
        )) : <p className="empty">保存分镜后，可在这里创建和管理任务。</p>}
      </div>

      {/* 追溯记录 */}
      {traceEvents.length > 0 && (
        <div className="trace-panel">
          <b>完整追溯记录</b>
          {traceEvents.map((event) => (
            <p key={event.id}><time>{event.created_at}</time><span>{event.event_type}</span>{event.task_id ? ` · 任务 #${event.task_id}` : ''}{event.asset_id ? ` · 资产 #${event.asset_id}` : ''}</p>
          ))}
        </div>
      )}

      {/* 最终成片 */}
      {storyboard?.final_video_url && (
        <div className="final-video">
          <div><span className="eyebrow">PUBLISH READY</span><h3>最终成片</h3><a href={storyboard.final_video_url} target="_blank" rel="noreferrer">打开/下载视频</a></div>
          <video controls src={storyboard.final_video_url} />
        </div>
      )}
    </section>
  )
}
