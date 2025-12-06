"""
Data shapes for the Competitor Analysis Engine.

These models are deliberately JSON-friendly and mirror Hummingbird concepts
where possible. They may be implemented later as Pydantic models; for now we
use dataclasses to keep dependencies light.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

Device = Literal["desktop", "iphone", "ipad"]
HumStatus = Literal["queued", "running", "passed", "failed", "completed"]
ApprovalStatus = Literal["pending", "approved", "rejected"]


# Core summaries ----------------------------------------------------------------

@dataclass
class SentimentBucket:
    positive: int
    neutral: int
    negative: int


@dataclass
class CompetitorSummary:
    competitorId: str
    name: str
    baseUrl: str
    sentiment: SentimentBucket
    valueVsTechnical: Dict[str, float]
    topProps: List[str] = field(default_factory=list)


@dataclass
class TopicSummary:
    topicId: str
    label: str
    competitors: List[str]
    scoreByCompetitor: Dict[str, float]


@dataclass
class CompetitorAnalysisSummary:
    competitors: List[CompetitorSummary]
    topics: List[TopicSummary]
    sentimentByCompetitor: Dict[str, SentimentBucket]
    valueVsTechnicalByCompetitor: Dict[str, Dict[str, float]]
    topValueProps: List[str]
    topKeywords: List[str]
    _meta: Dict[str, Any] = field(default_factory=dict)


# Config -----------------------------------------------------------------------

@dataclass
class CompetitorConfig:
    id: str
    name: str
    baseUrl: str
    priorityPages: List[str]


# Run record (HumRecord-compatible) -------------------------------------------

@dataclass
class CompetitorAnalysisRunRecord:
    id: str
    projectId: str
    humId: str
    url: str
    devices: List[Device]
    deviceMatrix: List[Device]
    flowId: str
    status: HumStatus
    approvalStatus: ApprovalStatus
    startedAt: str
    finishedAt: Optional[str]
    summaryJson: Optional[CompetitorAnalysisSummary] = None
    seriesBaseUrl: Optional[str] = None
    seriesBaseNormalized: Optional[str] = None
    name: Optional[str] = None
    seriesLabel: Optional[str] = None
    baselineId: Optional[str] = None
    retentionPolicy: Optional[str] = None
    phase: Optional[str] = None
    verification: Optional[Dict[str, Any]] = None
    clearance: Optional[Dict[str, Any]] = None
    diffStats: Optional[Dict[str, Any]] = None
    releaseNotes: Optional[Any] = None
    publishedAt: Optional[str] = None
    publishedTo: Optional[List[str]] = None
    lastPromotedAt: Optional[str] = None
    lastPromotedCaptureIds: Optional[List[str]] = None
    lastPromotedCaptureCount: Optional[int] = None
    lastPromotedChangedIds: Optional[List[str]] = None


# Artifacts --------------------------------------------------------------------

@dataclass
class CompetitorArtifactRecord:
    id: str
    projectId: str
    humId: str
    runId: str
    scenarioId: str
    scenarioKind: str
    routeTemplate: str
    device: Device
    stateSlug: Optional[str]
    capturedAt: str
    mimeType: Optional[str]
    rawKey: Optional[str]
    brandedKey: Optional[str]
    thumbKey: Optional[str]
    diffKey: Optional[str]
    afterUrl: Optional[str]
    beforeUrl: Optional[str]
    thumbUrl: Optional[str]
    byteSize: Optional[int]
    width: Optional[int]
    height: Optional[int]
    rawDiffScore: Optional[float] = None
    maskedDiffScore: Optional[float] = None
    noiseScore: Optional[float] = None
    stabilityScore: Optional[float] = None
    stabilitySampleCount: Optional[int] = None
    diffStatus: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

