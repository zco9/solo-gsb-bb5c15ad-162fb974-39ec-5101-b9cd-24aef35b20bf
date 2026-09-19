"""请求/响应模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ReconcileRequest(BaseModel):
    """恰好三段待核对文本。"""

    texts: list[str] = Field(..., description="恰好三段文本,每段不超过 120 个字素簇")

    @field_validator("texts")
    @classmethod
    def _exactly_three(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError("必须恰好提供三段文本(texts 长度须为 3)")
        return v


class Anchor(BaseModel):
    """一个锚点:三份文本中强制同列的三个字素簇位置(0 起始)。"""

    positions: list[int] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="三个来源中被锚定字素簇的位置,依次对应 texts[0/1/2]",
    )

    @field_validator("positions")
    @classmethod
    def _three_ints(cls, v: list[Any]) -> list[Any]:
        # bool 是 int 的子类,显式拒绝以免 True/False 被当作位置
        if len(v) != 3 or any(isinstance(x, bool) or not isinstance(x, int) for x in v):
            raise ValueError("每个锚点必须恰好提供三个整数位置(positions 长度须为 3)")
        return v


class AnchoredReconcileRequest(ReconcileRequest):
    """三段文本加锚点列表。"""

    anchors: list[Anchor] = Field(
        default_factory=list,
        description="锚点列表;各锚点位置在每个来源中均须严格递增、不越界且不重复",
    )


class SourceCell(BaseModel):
    """某列中一个来源的字素及其原位置;空位均为 null。"""

    grapheme: str | None
    position: int | None


class Column(BaseModel):
    index: int = Field(..., description="列序号(0 起始)")
    mask: int = Field(..., description="本列消费的来源位掩码,bit0/1/2 对应 texts[0/1/2]")
    cost: int = Field(..., description="本列成本")
    sources: list[SourceCell] = Field(..., description="三个来源的字素与原位置")
    consensus: str = Field(..., description="本列共识字素,未达成时为 �")


class AnchoredColumn(Column):
    anchored: bool = Field(..., description="本列是否为锚点强制对齐列")


class UncertainColumn(BaseModel):
    column: int = Field(..., description="未达成共识的列序号")
    sources: list[SourceCell] = Field(..., description="三个来源的字素与原位置")


class ReconcileResponse(BaseModel):
    consensus: str = Field(..., description="共识文本")
    total_cost: int = Field(..., description="对齐总成本")
    columns: list[Column] = Field(..., description="对齐列")
    uncertain: list[UncertainColumn] = Field(..., description="写入 � 的列及各来源字素与原位置")


class AnchoredReconcileResponse(BaseModel):
    consensus: str = Field(..., description="共识文本")
    total_cost: int = Field(..., description="对齐总成本(含锚点列)")
    columns: list[AnchoredColumn] = Field(..., description="对齐列,锚点列 anchored=true")
    uncertain: list[UncertainColumn] = Field(..., description="写入 � 的列及各来源字素与原位置")
