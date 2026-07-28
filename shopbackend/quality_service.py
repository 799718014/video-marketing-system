"""P2 视觉质检适配器：评分必须来自实际视觉服务或人工审核，绝不伪造。"""

from __future__ import annotations

from typing import Any

import httpx

from config import QUALITY_REVIEW_API_KEY, QUALITY_REVIEW_URL


class QualityReviewService:
    async def inspect(self, context: dict[str, Any]) -> dict[str, Any]:
        if not context.get("video_url"):
            raise RuntimeError("图生视频尚未生成完成，不能执行质检")
        if not QUALITY_REVIEW_URL:
            return {
                "engine": "manual_required",
                "status": "manual_required",
                "decision": "review",
                "summary": "未配置 QUALITY_REVIEW_URL；请人工审核商品一致性、Logo 与字幕 OCR。",
                "details": {"reason": "quality_provider_not_configured"},
            }
        headers = {"Content-Type": "application/json"}
        if QUALITY_REVIEW_API_KEY:
            headers["Authorization"] = f"Bearer {QUALITY_REVIEW_API_KEY}"
        payload = {
            "task_id": context["id"],
            "video_url": context["video_url"],
            "cover_url": context.get("cover_url"),
            "reference_assets": context["reference_manifest"],
            "expected": {
                "product_name": context["product_name"],
                "brand": context.get("product_brand"),
                "price": context.get("product_price"),
            },
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(QUALITY_REVIEW_URL, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as error:
            raise RuntimeError(f"视觉质检服务调用失败: {error}") from error

        result = body.get("data", body)
        similarity = result.get("product_similarity_score")
        if similarity is not None:
            try:
                similarity = float(similarity)
            except (TypeError, ValueError) as error:
                raise RuntimeError("视觉质检服务返回的 product_similarity_score 无效") from error
            if not 0 <= similarity <= 1:
                raise RuntimeError("视觉质检服务返回的 product_similarity_score 必须在 0 到 1 之间")
        logo_status = self._status(result.get("logo_status"), result.get("logo_detected"))
        ocr_status = self._status(result.get("ocr_status"), result.get("ocr_matched"))
        decision = result.get("decision")
        if decision not in {"pass", "review", "reject"}:
            decision = "review" if similarity is None else ("pass" if similarity >= 0.85 and logo_status != "fail" and ocr_status != "fail" else "review")
        return {
            "engine": result.get("engine", "external_vision"),
            "status": "completed",
            "product_similarity_score": similarity,
            "logo_status": logo_status,
            "ocr_status": ocr_status,
            "decision": decision,
            "summary": result.get("summary", "视觉质检完成"),
            "details": result,
        }

    @staticmethod
    def _status(status: Any, detected: Any) -> str:
        if status in {"pass", "fail", "not_applicable"}:
            return status
        if detected is True:
            return "pass"
        if detected is False:
            return "fail"
        return "not_applicable"


quality_reviewer = QualityReviewService()
