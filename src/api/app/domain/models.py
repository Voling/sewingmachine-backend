from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class FileDescriptor:
    key: str
    size: Optional[int]
    last_modified: Optional[str]
    url: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DirectoryDescriptor:
    name: str
    prefix: str
    file_count: int
    files: List[FileDescriptor]
    truncated: bool

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["files"] = [f.to_dict() for f in self.files]
        return payload


@dataclass
class LayerSnapshot:
    prefix: Optional[str]
    dir_count: int
    dirs: List[DirectoryDescriptor]
    truncated: bool

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["dirs"] = [d.to_dict() for d in self.dirs]
        return payload


@dataclass
class QueryStatistics:
    scanned_bytes: Optional[int]
    execution_time_ms: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryResultPage:
    columns: List[str]
    rows: List[List[Optional[str]]]
    stats: QueryStatistics
    query_execution_id: str
    next_page_token: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["stats"] = self.stats.to_dict()
        return payload


@dataclass
class DatabaseSummary:
    name: str
    tables: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
