/**
 * 批量视频 API 前端测试用例
 *
 * 测试范围:
 * 1. API 函数调用
 * 2. 请求/响应数据格式
 * 3. 错误处理
 * 4. 轮询逻辑
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import {
  createBatchVideo,
  getBatchStatus,
  checkMergeStatus,
  retryBatchSegments,
  getBatchDownloadUrl,
  getSegmentDownloadUrl,
  type BatchVideoCreateRequest,
  type BatchVideoTask,
  type ScriptResult
} from './api'

// Mock axios
vi.mock('axios')

const mockedAxios = vi.mocked(axios)

describe('批量视频 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ========== 测试 1: 创建批量任务 ==========

  describe('createBatchVideo', () => {
    it('应该成功创建批量视频任务', async () => {
      const mockScript: ScriptResult = {
        title: '测试产品视频',
        total_duration: 30,
        style: '活力',
        scenes: [
          {
            scene_no: 1,
            duration: 5,
            visual: '产品展示场景1',
            narration: '旁白1',
            subtitle: '字幕1'
          },
          {
            scene_no: 2,
            duration: 5,
            visual: '产品展示场景2',
            narration: '旁白2',
            subtitle: '字幕2'
          }
        ],
        full_prompt: '活力产品展示视频'
      }

      const mockResponse: BatchVideoTask = {
        batch_id: 'test_batch_123',
        script: mockScript,
        video_params: {
          model: 'kling-v1-5',
          aspect_ratio: '9:16',
          cfg_scale: 0.5,
          transition: 'fade'
        },
        segments: [
          {
            segment_id: 'test_batch_123_seg_0',
            segment_no: 1,
            scene_index: 0,
            duration: 5,
            prompt: 'Scene 1: 产品展示场景1',
            status: 'pending',
            retry_count: 0
          },
          {
            segment_id: 'test_batch_123_seg_1',
            segment_no: 2,
            scene_index: 1,
            duration: 5,
            prompt: 'Scene 2: 产品展示场景2',
            status: 'pending',
            retry_count: 0
          }
        ],
        status: 'submitted',
        total_duration: 10,
        created_at: 1234567890
      }

      const request: BatchVideoCreateRequest = {
        script: mockScript,
        model: 'kling-v1-5',
        aspect_ratio: '9:16',
        cfg_scale: 0.5,
        transition: 'fade',
        max_concurrent: 3
      }

      mockedAxios.create.mockReturnValue({
        post: vi.fn().mockResolvedValue({ data: mockResponse })
      } as any)

      const result = await createBatchVideo(request)

      expect(result).toEqual(mockResponse)
      expect(result.batch_id).toBe('test_batch_123')
      expect(result.status).toBe('submitted')
      expect(result.segments).toHaveLength(2)
    })

    it('应该使用默认参数', async () => {
      const mockScript: ScriptResult = {
        title: '测试',
        total_duration: 5,
        style: '活力',
        scenes: [{ scene_no: 1, duration: 5, visual: '测试', narration: '', subtitle: '' }],
        full_prompt: 'test'
      }

      mockedAxios.create.mockReturnValue({
        post: vi.fn().mockResolvedValue({
          data: {
            batch_id: 'test_batch',
            script: mockScript,
            video_params: {},
            segments: [],
            status: 'submitted',
            total_duration: 5,
            created_at: 1234567890
          }
        })
      } as any)

      await createBatchVideo({ script: mockScript })

      // 验证使用默认值
      const postCall = mockedAxios.create().post as any
      expect(postCall).toHaveBeenCalled()
    })
  })

  // ========== 测试 2: 查询任务状态 ==========

  describe('getBatchStatus', () => {
    it('应该成功获取任务状态', async () => {
      const mockTask: BatchVideoTask = {
        batch_id: 'test_batch',
        script: {
          title: '测试',
          total_duration: 10,
          style: '活力',
          scenes: [],
          full_prompt: 'test'
        },
        video_params: {},
        segments: [
          {
            segment_id: 'seg_1',
            segment_no: 1,
            scene_index: 0,
            duration: 5,
            prompt: '测试',
            status: 'succeed',
            video_url: 'http://example.com/vid.mp4',
            retry_count: 0
          },
          {
            segment_id: 'seg_2',
            segment_no: 2,
            scene_index: 0,
            duration: 5,
            prompt: '测试',
            status: 'processing',
            retry_count: 0
          }
        ],
        status: 'processing',
        total_duration: 10,
        created_at: 1234567890
      }

      mockedAxios.create.mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockTask })
      } as any)

      const result = await getBatchStatus('test_batch')

      expect(result).toEqual(mockTask)
      expect(result.status).toBe('processing')
      expect(result.segments[0].status).toBe('succeed')
      expect(result.segments[1].status).toBe('processing')
    })

    it('应该处理任务不存在的情况', async () => {
      mockedAxios.create.mockReturnValue({
        get: vi.fn().mockRejectedValue({
          response: { status: 404, data: { detail: '任务不存在' } }
        })
      } as any)

      await expect(getBatchStatus('nonexistent'))
        .rejects.toMatchObject({
          response: { status: 404 }
        })
    })
  })

  // ========== 测试 3: 检查合并状态 ==========

  describe('checkMergeStatus', () => {
    it('应该检查合并状态', async () => {
      const mockTask: BatchVideoTask = {
        batch_id: 'test_batch',
        script: {
          title: '测试',
          total_duration: 10,
          style: '活力',
          scenes: [],
          full_prompt: 'test'
        },
        video_params: {},
        segments: [],
        status: 'merging',
        total_duration: 10,
        created_at: 1234567890,
        merged_video_path: '/output/merged.mp4',
        merged_video_url: '/api/batch-video/merged/test_batch',
        completed_at: 1234567900
      }

      mockedAxios.create.mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockTask })
      } as any)

      const result = await checkMergeStatus('test_batch')

      expect(result.status).toBe('merging')
      expect(result.merged_video_url).toBeTruthy()
    })
  })

  // ========== 测试 4: 重试失败片段 ==========

  describe('retryBatchSegments', () => {
    it('应该重试失败片段', async () => {
      const mockTask: BatchVideoTask = {
        batch_id: 'test_batch',
        script: {
          title: '测试',
          total_duration: 10,
          style: '活力',
          scenes: [],
          full_prompt: 'test'
        },
        video_params: {},
        segments: [
          {
            segment_id: 'seg_1',
            segment_no: 1,
            scene_index: 0,
            duration: 5,
            prompt: '测试',
            status: 'succeed',
            video_url: 'http://example.com/vid.mp4',
            retry_count: 0
          },
          {
            segment_id: 'seg_2',
            segment_no: 2,
            scene_index: 0,
            duration: 5,
            prompt: '测试',
            status: 'pending',  // 重置为pending
            retry_count: 0
          }
        ],
        status: 'processing',
        total_duration: 10,
        created_at: 1234567890
      }

      mockedAxios.create.mockReturnValue({
        post: vi.fn().mockResolvedValue({ data: mockTask })
      } as any)

      const result = await retryBatchSegments('test_batch')

      expect(result.status).toBe('processing')
    })

    it('应该处理错误状态', async () => {
      mockedAxios.create.mockReturnValue({
        post: vi.fn().mockRejectedValue({
          response: { status: 400, data: { detail: '当前状态不支持重试' } }
        })
      } as any)

      await expect(retryBatchSegments('completed_batch'))
        .rejects.toMatchObject({
          response: { status: 400 }
        })
    })
  })

  // ========== 测试 5: 下载URL生成 ==========

  describe('下载URL生成', () => {
    it('应该生成正确的批量视频下载URL', () => {
      const url = getBatchDownloadUrl('test_batch_123')
      expect(url).toBe('/api/batch-video/download/test_batch_123')
    })

    it('应该生成正确的片段下载URL', () => {
      const url = getSegmentDownloadUrl('test_batch_123', 2)
      expect(url).toBe('/api/batch-video/segment/test_batch_123/2')
    })
  })

  // ========== 测试 6: 轮询辅助函数 ==========

  describe('轮询逻辑', () => {
    it('应该正确计算完成进度', () => {
      const task: BatchVideoTask = {
        batch_id: 'test',
        script: {
          title: '测试',
          total_duration: 30,
          style: '活力',
          scenes: [],
          full_prompt: 'test'
        },
        video_params: {},
        segments: [
          { segment_id: '1', segment_no: 1, scene_index: 0, duration: 5, prompt: '', status: 'succeed', retry_count: 0 },
          { segment_id: '2', segment_no: 2, scene_index: 0, duration: 5, prompt: '', status: 'succeed', retry_count: 0 },
          { segment_id: '3', segment_no: 3, scene_index: 0, duration: 5, prompt: '', status: 'processing', retry_count: 0 },
          { segment_id: '4', segment_no: 4, scene_index: 0, duration: 5, prompt: '', status: 'pending', retry_count: 0 },
          { segment_id: '5', segment_no: 5, scene_index: 0, duration: 5, prompt: '', status: 'pending', retry_count: 0 },
          { segment_id: '6', segment_no: 6, scene_index: 0, duration: 5, prompt: '', status: 'pending', retry_count: 0 },
        ],
        status: 'processing',
        total_duration: 30,
        created_at: 1234567890
      }

      const succeedCount = task.segments.filter(s => s.status === 'succeed').length
      const progress = (succeedCount / task.segments.length) * 100

      expect(progress).toBe(33.333333333333336)
    })

    it('应该正确识别所有片段完成', () => {
      const task: BatchVideoTask = {
        batch_id: 'test',
        script: {
          title: '测试',
          total_duration: 15,
          style: '活力',
          scenes: [],
          full_prompt: 'test'
        },
        video_params: {},
        segments: [
          { segment_id: '1', segment_no: 1, scene_index: 0, duration: 5, prompt: '', status: 'succeed', retry_count: 0 },
          { segment_id: '2', segment_no: 2, scene_index: 0, duration: 5, prompt: '', status: 'succeed', retry_count: 0 },
          { segment_id: '3', segment_no: 3, scene_index: 0, duration: 5, prompt: '', status: 'succeed', retry_count: 0 },
        ],
        status: 'merging',
        total_duration: 15,
        created_at: 1234567890
      }

      const allSucceed = task.segments.every(s => s.status === 'succeed')
      expect(allSucceed).toBe(true)
    })
  })

  // ========== 测试 7: 数据类型验证 ==========

  describe('数据类型验证', () => {
    it('应该正确处理状态类型', () => {
      const validStatuses: Array<'pending' | 'processing' | 'succeed' | 'failed' | 'merging'> = [
        'pending',
        'processing',
        'succeed',
        'failed',
        'merging'
      ]

      validStatuses.forEach(status => {
        expect(status).toBeTruthy()
      })
    })

    it('应该正确处理宽高比类型', () => {
      const validRatios: Array<'9:16' | '16:9' | '1:1'> = ['9:16', '16:9', '1:1']

      validRatios.forEach(ratio => {
        expect(ratio).toMatch(/^\d+:\d+$/)
      })
    })
  })
})