# charts/base.py
"""
统一图表接口协议
所有图表 generate() 必须遵循此接口
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChartResult:
    """
    统一返回结构
    所有图表 generate() 必须返回此结构
    """
    html: str = ""
    spec: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return bool(self.html.strip()) and len(self.html) > 500


@dataclass
class FieldMapping:
    """
    字段映射标准名称
    图表使用 mapping.xxx 读取实际列名
    """
    label: Optional[str] = None
    value: Optional[str] = None
    x: Optional[str] = None
    y: Optional[str] = None
    series: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    lat: Optional[str] = None
    lon: Optional[str] = None
    geo: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    parent: Optional[str] = None
    child: Optional[str] = None
    path: Optional[str] = None
    open_: Optional[str] = field(default=None, metadata={"alias": "open"})
    high: Optional[str] = None
    low: Optional[str] = None
    close: Optional[str] = field(default=None, metadata={"alias": "close"})
    volume: Optional[str] = None
    text: Optional[str] = None
    frequency: Optional[str] = None
    group: Optional[str] = None
    rank: Optional[str] = None
    actual: Optional[str] = None
    target_val: Optional[str] = field(default=None, metadata={"alias": "target"})

    def to_dict(self) -> Dict[str, str]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "FieldMapping":
        known = {}
        for k, v in d.items():
            if hasattr(cls, k) or k in ("open", "close", "target"):
                key = {"open": "open_", "close": "close_", "target": "target_val"}.get(k, k)
                known[key] = v
        return cls(**known)
