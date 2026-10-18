"""Validated domain specifications shared by the services, the API and the importers."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .timeutil import parse_ts

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,63}$")
SIGNAL_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _check_id(v: str) -> str:
    if not ID_RE.match(v):
        raise ValueError(f"identifier {v!r} must be 1-64 characters of letters, digits, '_', '.', ':' or '-'")
    return v


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignalSpec(Strict):
    name: str
    unit: str = Field(min_length=1)
    min: float | None = None
    max: float | None = None
    required: bool = True
    description: str = ""

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        if not SIGNAL_RE.match(v):
            raise ValueError(f"signal name {v!r} must be lower-case letters, digits and '_'")
        return v

    @model_validator(mode="after")
    def _range(self):
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"signal {self.name}: min {self.min} > max {self.max}")
        return self


class JobSpec(Strict):
    duration_h: float = Field(gt=0)
    skill: str = Field(min_length=1)
    parts: dict[str, int] = Field(default_factory=dict)
    crew_size: int = Field(default=1, ge=1)


class AssetTypeSpec(Strict):
    asset_type_id: str
    name: str = Field(min_length=1)
    description: str = ""
    time_basis: Literal["timestamp", "cycle_index"]
    usage_hours_per_cycle: float | None = Field(default=None, gt=0)
    signals: list[SignalSpec] = Field(min_length=1)
    jobs: dict[str, JobSpec]

    @field_validator("asset_type_id")
    @classmethod
    def _type_id(cls, v):
        return _check_id(v)

    @model_validator(mode="after")
    def _consistency(self):
        names = [s.name for s in self.signals]
        if len(names) != len(set(names)):
            raise ValueError("signal names must be unique within an asset type")
        if "inspect" not in self.jobs:
            raise ValueError("an asset type must define at least an 'inspect' job")
        if self.time_basis == "cycle_index" and self.usage_hours_per_cycle is None:
            raise ValueError("time_basis 'cycle_index' requires usage_hours_per_cycle (an explicit, documented assumption)")
        return self

    def signal(self, name: str) -> SignalSpec | None:
        return next((s for s in self.signals if s.name == name), None)


class ConsequenceSpec(Strict):
    downtime_hours: float = Field(ge=0)
    cost_per_failure: float = Field(ge=0)
    safety_impact: bool
    environmental_impact: bool
    cost_unit: str = "currency units"


class WindowSpec(Strict):
    """A period during which the asset may be taken out of service for maintenance (UTC-aware timestamps)."""
    start: str
    end: str

    @model_validator(mode="after")
    def _order(self):
        s, e = parse_ts(self.start), parse_ts(self.end)      # refuses naive timestamps
        if e <= s:
            raise ValueError(f"maintenance window ends ({self.end}) before it starts ({self.start})")
        return self

    @property
    def start_ms(self) -> int:
        return parse_ts(self.start)

    @property
    def end_ms(self) -> int:
        return parse_ts(self.end)


class AssetSpec(Strict):
    asset_id: str
    tag: str = Field(min_length=1)
    name: str = Field(min_length=1)
    asset_type_id: str
    site_id: str
    location: str = ""
    criticality: Literal["A", "B", "C"]
    consequence: ConsequenceSpec
    config: dict = Field(default_factory=dict)
    operating_context: dict = Field(default_factory=dict)
    maintenance_windows: list[WindowSpec] = Field(default_factory=list)
    installed_at: str | None = None

    @field_validator("asset_id")
    @classmethod
    def _asset_id(cls, v):
        return _check_id(v)

    @field_validator("installed_at")
    @classmethod
    def _installed(cls, v):
        if v is not None:
            parse_ts(v)
        return v


class Asset(AssetSpec):
    status: Literal["active", "out_of_service", "retired"] = "active"
    last_maintenance_at: str | None = None
    created_at: str
    updated_at: str
