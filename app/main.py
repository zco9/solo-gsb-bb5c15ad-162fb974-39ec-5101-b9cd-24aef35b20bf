"""抄本核对 API:对三份独立抄录做三维全局对齐并生成共识文本。"""
from __future__ import annotations

import unicodedata

import grapheme
from fastapi import FastAPI, HTTPException

from .reconcile import reconcile, reconcile_anchored
from .schemas import (
    AnchoredReconcileRequest,
    AnchoredReconcileResponse,
    ReconcileRequest,
    ReconcileResponse,
)

MAX_GRAPHEMES = 120

app = FastAPI(
    title="抄本核对 API",
    version="1.1.0",
    description=(
        "接收三段抄录文本,NFC 规范化后做三维全局动态规划对齐,输出共识文本、"
        "对齐列与总成本。/reconcile/anchored 额外支持锚点强制同列约束。"
    ),
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _prepare_sequences(texts: list[str]) -> list[list[str]]:
    """NFC 规范化并按 UAX #29 切分为字素簇,超长返回 422。"""
    seqs: list[list[str]] = []
    for idx, raw in enumerate(texts):
        normalized = unicodedata.normalize("NFC", raw)
        clusters = list(grapheme.graphemes(normalized))
        if len(clusters) > MAX_GRAPHEMES:
            raise HTTPException(
                status_code=422,
                detail=f"texts[{idx}] 超过 {MAX_GRAPHEMES} 个字素簇(当前 {len(clusters)} 个)",
            )
        seqs.append(clusters)
    return seqs


def _validate_anchors(
    anchors: list[tuple[int, int, int]], lengths: tuple[int, int, int]
) -> None:
    """校验锚点不越界,且在每个来源中严格递增(等价于不重复、不倒序)。"""
    prev = [-1, -1, -1]
    for aidx, anchor in enumerate(anchors):
        for s in range(3):
            pos = anchor[s]
            if pos < 0 or pos >= lengths[s]:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"anchors[{aidx}].positions[{s}]={pos} 越界:"
                        f"texts[{s}] 长度为 {lengths[s]} 个字素簇"
                    ),
                )
            if pos <= prev[s]:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"anchors[{aidx}].positions[{s}]={pos} 未按来源位置严格递增"
                        f"(前一锚点位置为 {prev[s]})"
                    ),
                )
            prev[s] = pos


@app.post("/reconcile", response_model=ReconcileResponse)
def post_reconcile(req: ReconcileRequest) -> dict:
    seqs = _prepare_sequences(req.texts)
    return reconcile(*seqs)


@app.post("/reconcile/anchored", response_model=AnchoredReconcileResponse)
def post_reconcile_anchored(req: AnchoredReconcileRequest) -> dict:
    seqs = _prepare_sequences(req.texts)
    anchors = [tuple(a.positions) for a in req.anchors]
    _validate_anchors(anchors, (len(seqs[0]), len(seqs[1]), len(seqs[2])))
    return reconcile_anchored(seqs[0], seqs[1], seqs[2], anchors)
