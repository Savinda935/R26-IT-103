from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SensorValues(BaseModel):
    air_temperature_c: Optional[float] = None
    relative_humidity_percent: Optional[float] = None
    heat_index_c: Optional[float] = None
    soil_temperature_c: Optional[float] = None
    soil_moisture_raw: Optional[float] = None
    soil_moisture_percent: Optional[float] = None
    ec_ms_cm: Optional[float] = None


class CanonicalSensorPayload(BaseModel):
    schema_version: str = "1.0"
    device_id: str = Field(..., min_length=1, max_length=100)
    plot_id: str = Field(..., min_length=1, max_length=100)
    crop_cycle_id: str = Field(..., min_length=1, max_length=100)
    plant_id: Optional[str] = Field(default=None, max_length=100)
    recorded_at: Optional[float] = Field(default=None, description="Unix timestamp in seconds")
    sensors: SensorValues
    calibration_version: Optional[str] = Field(default=None, max_length=100)
    source: str = Field(default="firebase", max_length=50)


class IngestionResult(BaseModel):
    status: Literal["inserted", "updated"]
    reading_id: int
    recorded_at: float
    bucket_start: float
    quality_status: str
    quality_issues: List[str] = Field(default_factory=list)


class PlotCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=150)
    location: Optional[str] = Field(default=None, max_length=250)
    soil_type: Optional[str] = Field(default=None, max_length=100)


class CropCycleCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    plot_id: str = Field(..., min_length=1, max_length=100)
    crop_name: str = Field(default="Nai Miris", max_length=100)
    variety: str = Field(default="Scotch Bonnet", max_length=100)
    planting_date: str = Field(..., description="ISO date, for example 2026-08-17")
    status: str = Field(default="active", max_length=30)


class PlantCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    crop_cycle_id: str = Field(..., min_length=1, max_length=100)
    plant_code: str = Field(..., min_length=1, max_length=100)
    row_number: Optional[str] = Field(default=None, max_length=50)
    position: Optional[str] = Field(default=None, max_length=100)


class DeviceCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    plot_id: str = Field(..., min_length=1, max_length=100)
    device_code: str = Field(..., min_length=1, max_length=100)
    firmware_version: Optional[str] = Field(default=None, max_length=100)
    expected_interval_seconds: int = Field(default=300, ge=30, le=86400)


class MonitoringSetupRequest(BaseModel):
    plot: PlotCreate
    crop_cycle: CropCycleCreate
    device: DeviceCreate
    plants: List[PlantCreate] = Field(default_factory=list)


class DeviceStatus(BaseModel):
    device_id: str
    device_code: str
    plot_id: str
    last_seen_at: Optional[float] = None
    expected_interval_seconds: int
    seconds_since_seen: Optional[float] = None
    status: Literal["online", "offline", "never_seen"]


class AggregatedPeriod(BaseModel):
    period_start: float
    period_end: float
    sample_count: int
    valid_sample_count: int
    valid_sample_percent: float
    averages: Dict[str, Optional[float]]
    minimums: Dict[str, Optional[float]]
    maximums: Dict[str, Optional[float]]


class AggregationResponse(BaseModel):
    interval: Literal["hour", "day"]
    device_id: Optional[str] = None
    periods: List[AggregatedPeriod]
