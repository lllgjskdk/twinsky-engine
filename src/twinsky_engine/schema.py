"""
core/schema.py — 全项目的数据结构契约。

任何模块的输入输出都必须符合这里的定义。
铁律二：所有分析输出必须携带 highlight ID，无 highlight 的输出视为无效。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
import re
from collections.abc import Callable
from typing import Any
from .precision import BirthPrecision


class System(str, Enum):
    BAZI = "bazi"
    VEDIC = "vedic"


class Polarity(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InsightKind(str, Enum):
    """深度洞察的叙述边界。"""

    STRUCTURE = "structure"
    HYPOTHESIS = "hypothesis"
    PROTECTIVE = "protective"


class CrossStatus(str, Enum):
    """跨盘信号的关系类型，仅用于规则层诊断而非把矛盾抛给用户。"""

    CONVERGE = "converge"
    COMPLEMENT = "complement"
    RECONCILED = "reconciled"


class VargaRole(str, Enum):
    """吠陀分盘在证据链中的职责，不是事件概率。"""

    FOUNDATION = "foundation"
    CONFIRMATION = "confirmation"
    TOPIC_DETAIL = "topic_detail"


class RaoSignal(str, Enum):
    """Rao 分层验证的规则信号；不是事件概率。"""

    CONFIRM = "confirm"
    DAMAGE = "damage"
    QUALIFY = "qualify"
    TIMING = "timing"
    NULL = "null"


class AnalysisStepKind(str, Enum):
    """工作台公开展示的规则步骤类型，不代表模型隐藏思维链。"""

    SCOPE = "scope"
    DIMENSION = "dimension"
    INSIGHT = "insight"
    HISTORY = "history"
    RECONCILIATION = "reconciliation"
    FORECAST = "forecast"


class BlindSignalStrength(str, Enum):
    """盲测逐年信号强度，不等同于事件概率。"""

    CROSS_SYSTEM = "cross_system"
    SINGLE_SYSTEM = "single_system"
    NONE = "none"


class BlindArm(str, Enum):
    """盲测固定消融组；揭晓后不得事后调整。"""

    ANY_SIGNAL = "any_signal"
    BAZI_ONLY = "bazi_only"
    VEDIC_ONLY = "vedic_only"
    CROSS_SYSTEM = "cross_system"


class ForecastPriority(str, Enum):
    """未来观察阶段的展示优先级，不等同于事件概率。"""

    CORE = "core"
    SUPPORTING = "supporting"


class CandidateRank(str, Enum):
    """规则候选在回答中的位置，不代表事件已经发生。"""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    REJECTED = "rejected"


class GeJuResolutionStatus(str, Enum):
    """格局取格的确定性状态；候选不等于已定格。"""

    PENDING = "pending"
    RESOLVED = "resolved"
    CANDIDATES = "candidates"
    NOT_APPLICABLE = "not_applicable"
    RULE_UNAVAILABLE = "rule_unavailable"


class XiangShenResolutionStatus(str, Enum):
    """相神的裁决状态； absent 与 unresolved 必须分开。"""

    PENDING = "pending"
    RESOLVED = "resolved"
    ABSENT = "absent"
    UNRESOLVED = "unresolved"


class EventDirection(str, Enum):
    """年度主题被引动后的发展方向，不等同于事件概率。"""

    EXPANSION = "expansion"
    CONSOLIDATION = "consolidation"
    PRESSURE = "pressure"
    TRANSITION = "transition"
    UNDETERMINED = "undetermined"


class EventForm(str, Enum):
    """年度事件的可核验现实形态；比维度和方向更具体。"""

    CAREER_ENTRY = "career_entry"
    CAREER_GROWTH = "career_growth"
    CAREER_STABILITY = "career_stability"
    CAREER_TRAINING = "career_training"
    CAREER_PRESSURE = "career_pressure"
    CAREER_EXIT = "career_exit"
    CAREER_CHANGE = "career_change"
    CAREER_SELF_EMPLOYMENT = "career_self_employment"
    BUSINESS_PARTNERSHIP = "business_partnership"
    RELATIONSHIP_ENTRY = "relationship_entry"
    RELATIONSHIP_COMMITMENT = "relationship_commitment"
    RELATIONSHIP_CONFLICT = "relationship_conflict"
    RELATIONSHIP_SEPARATION = "relationship_separation"
    EDUCATION_ACHIEVEMENT = "education_achievement"
    EDUCATION_TRAINING = "education_training"
    EDUCATION_DELAY = "education_delay"
    EDUCATION_CHANGE = "education_change"
    WEALTH_GAIN = "wealth_gain"
    WEALTH_STABILITY = "wealth_stability"
    WEALTH_PRESSURE = "wealth_pressure"
    WEALTH_REALLOCATION = "wealth_reallocation"
    PROPERTY_PURCHASE = "property_purchase"
    PROPERTY_STABILITY = "property_stability"
    PROPERTY_PRESSURE = "property_pressure"
    PROPERTY_RELOCATION = "property_relocation"
    FAMILY_SUPPORT = "family_support"
    FAMILY_CARE = "family_care"
    FAMILY_PRESSURE = "family_pressure"
    FAMILY_ROLE_CHANGE = "family_role_change"
    CHILDREN_ENTRY = "children_entry"
    CHILDREN_CARE = "children_care"
    CHILDREN_PRESSURE = "children_pressure"
    CHILDREN_ROLE_CHANGE = "children_role_change"
    HEALTH_SUPPORT = "health_support"
    HEALTH_RECOVERY = "health_recovery"
    HEALTH_PRESSURE = "health_pressure"
    HEALTH_ROUTINE_CHANGE = "health_routine_change"
    RELOCATION_LOCAL = "relocation_local"
    RELOCATION_REMOTE = "relocation_remote"
    RELOCATION_ADMIN = "relocation_admin"
    SIBLINGS_COLLABORATION = "siblings_collaboration"
    SIBLINGS_BOUNDARY = "siblings_boundary"
    SIBLINGS_PRESSURE = "siblings_pressure"
    SIBLINGS_RESTRUCTURE = "siblings_restructure"


class ObservationStatus(str, Enum):
    """真人揭晓标签；资料不足必须保留为 unknown。"""

    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class StepFeedbackRating(str, Enum):
    """用户对一条公开规则步骤的核验结果，不等同于盲测标签。"""

    ACCURATE = "accurate"
    PARTIAL = "partial"
    INACCURATE = "inaccurate"
    UNKNOWN = "unknown"
    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"


class TimePrecision(str, Enum):
    """输入时间精度，直接决定印占可用范围与 confidence。见 the TwinSky project spec §6.3"""

    EXACT = "exact"
    PERIOD = "period"
    UNKNOWN = "unknown"


class SolarTimeMode(str, Enum):
    """真太阳时算法。两种结果都会计算并保存，此项决定哪个驱动时柱。"""

    STANDARD = "standard"
    LONGITUDE = "longitude"
    LONGITUDE_EOT = "longitude_eot"


# 线上唯一有效的八字时间口径。均时差结果仍保留在 BirthInput 中供研发审计，
# 但不能被建档 API 或首页静默选用。
ONLINE_SOLAR_TIME_MODE = SolarTimeMode.LONGITUDE


class ZiShiRule(str, Enum):
    """23:00–24:00 出生的日柱处理规则。"""

    NO_SWITCH = "no_switch"
    SWITCH = "switch"
    SPLIT = "split"


# 线上固定口径：23:00–24:00 仍归入出生当天的日柱。
# 其他枚举值保留给历史档案与研发对照，不得由线上建档接口选用。
ONLINE_ZISHI_RULE = ZiShiRule.NO_SWITCH


@dataclass(frozen=True)
class VedicEngineConfig:
    """印占引擎的可核对参数；IANA 时区负责历史夏令时转换。"""

    timezone: str
    ephe_path: str
    ayanamsa: str = "true_citra"
    node_type: str = "true_node"
    karaka_scheme: str = "eight"
    varga_profile: str = "jhora8_default_v1"
    require_swiss_ephemeris: bool = True


@dataclass(frozen=True)
class VargaPolicy:
    """分盘解读层级；Vimshopaka 分数只作经典元数据。"""

    division: str
    role: VargaRole
    topics: tuple[str, ...]
    requires_d1_support: bool
    vimshopaka_weight: float | None = None


@dataclass(frozen=True)
class DimensionSpec:
    """生活维度的单一配置源，供规划、历史、时间线与前端共用。"""

    key: str
    label: str
    keywords: tuple[str, ...]
    insight_dimensions: frozenset[str]
    preferred_varga: str
    detail_vargas: tuple[str, ...] = ()
    history_ten_gods: frozenset[str] = frozenset()
    history_ten_gods_male: frozenset[str] = frozenset()
    history_ten_gods_female: frozenset[str] = frozenset()
    history_theme: str | None = None
    forecast_profile: str | None = None
    history_continuation_conditions: tuple[str, ...] = ()
    history_interruption_conditions: tuple[str, ...] = ()
    safety_boundary: str = ""

    def history_gods_for(self, gender: str) -> frozenset[str]:
        """按性别取需要区分的历史十神；未知时保留两组候选。"""
        normalized = gender.lower()
        if normalized == "male" and self.history_ten_gods_male:
            return self.history_ten_gods_male
        if normalized == "female" and self.history_ten_gods_female:
            return self.history_ten_gods_female
        gendered = self.history_ten_gods_male | self.history_ten_gods_female
        return self.history_ten_gods or gendered


@dataclass(frozen=True)
class RegisteredDimension:
    """将维度配置与其确定性分析器绑定。"""

    spec: DimensionSpec
    analyzer: Callable[[ChartBundle], CrossValidation]


@dataclass
class BirthInput:
    """出生信息。两种真太阳时都算、都存，见 SolarTimeMode。"""

    raw_datetime: datetime
    lat: float
    lng: float
    tz_offset: float
    gender: str
    precision: TimePrecision | BirthPrecision = TimePrecision.EXACT
    t_standard: datetime | None = None
    t_longitude: datetime | None = None
    t_longitude_eot: datetime | None = None
    active_mode: SolarTimeMode = ONLINE_SOLAR_TIME_MODE

    @property
    def effective_time(self) -> datetime:
        """当前配置下实际驱动排盘的时间。"""
        return {
            SolarTimeMode.STANDARD: self.t_standard,
            SolarTimeMode.LONGITUDE: self.t_longitude,
            SolarTimeMode.LONGITUDE_EOT: self.t_longitude_eot,
        }[self.active_mode] or self.raw_datetime

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class XiangShen:
    """相神的盘面位置及其已经推导的天干、十神。"""

    id: str
    stem: str
    ten_god: str


@dataclass
class GeJuGod:
    """定格之神的实际盘面位置；不等同于成格用神或相神。"""

    id: str
    stem: str
    ten_god: str


@dataclass(frozen=True)
class GeJuCandidate:
    """未达到定格门槛的月令候选，仅供裁决而非结论。"""

    grid: str
    god: GeJuGod
    basis: str


@dataclass
class GeJuYongShen:
    """格局派用神：保存取法、允许的十神类别与盘面主用位置。"""

    principle: str
    ten_gods: tuple[str, ...]
    primary: XiangShen | None = None


@dataclass
class QiYun:
    """起运计算结果；年龄拆分遵循三日一年的传统折算法。"""

    direction: str
    target_jie: str
    target_jie_at: datetime
    elapsed_seconds: float
    age_years: int
    age_months: int
    age_days: float
    start_date: datetime


@dataclass
class DaYunPeriod:
    """一柱十年大运。"""

    id: str
    index: int
    pillar: str
    stem: str
    branch: str
    stem_ten_god: str
    branch_ten_gods: list[str]
    start_year: int
    end_year: int
    start_date: datetime
    end_date: datetime


@dataclass
class LiuNian:
    """以立春换年的流年。"""

    id: str
    year: int
    pillar: str
    stem: str
    branch: str
    stem_ten_god: str
    branch_ten_gods: list[str]


@dataclass
class XiaoYun:
    """起运前逐年推进的小运。"""

    year: int
    pillar: str
    stem: str
    branch: str
    stem_ten_god: str
    branch_ten_gods: list[str]


@dataclass
class BaziChart:
    """八字盘（格局派）。"""

    birth: BirthInput
    zishi_rule: ZiShiRule
    pillars: dict[str, str]
    stems: dict[str, str]
    branches: dict[str, str]
    hidden_stems: dict[str, dict[str, str | None]]
    day_master: str
    siling: str
    siling_depth: int | None = None
    ge_ju: str | None = None
    ge_ju_resolution_status: GeJuResolutionStatus = GeJuResolutionStatus.PENDING
    ge_ju_candidates: list[GeJuCandidate] = field(default_factory=list)
    ge_ju_status: str | None = None
    ge_ju_clarity: str | None = None  # "暗格" | None
    ge_ju_variant: str | None = None
    ge_ju_god: GeJuGod | None = None
    ge_ju_yong_shen: GeJuYongShen | None = None
    ge_ju_unavailable_reason: str | None = None
    ge_ju_assessment: dict[str, Any] = field(default_factory=dict)
    xiang_shen: XiangShen | None = None
    xiang_shen_resolution_status: XiangShenResolutionStatus = XiangShenResolutionStatus.PENDING
    shi_shen: dict[str, str] = field(default_factory=dict)
    qi_yun: QiYun | None = None
    da_yun: list[DaYunPeriod] = field(default_factory=list)
    liu_nian: list[LiuNian] = field(default_factory=list)
    xiao_yun: list[XiaoYun] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class VedicChart:
    """印占盘。True Citra（Lahiri 系）+ 整宫制。"""

    birth: BirthInput
    ayanamsa: str = "true_citra"
    house_system: str = "whole_sign"
    lagna_rasi: str = ""
    lagna_degree: float = 0.0
    grahas: dict[str, dict[str, Any]] = field(default_factory=dict)
    houses: dict[int, dict[str, Any]] = field(default_factory=dict)
    moon_nakshatra: str = ""
    dashas: list[dict[str, Any]] = field(default_factory=list)
    vargas: dict[str, Any] = field(default_factory=dict)
    yogas: list[dict[str, Any]] = field(default_factory=list)
    karakas: dict[str, dict[str, Any]] = field(default_factory=dict)
    ashtakavarga: dict[str, Any] = field(default_factory=dict)
    shadbala: dict[str, dict[str, Any]] = field(default_factory=dict)
    avasthas: dict[str, dict[str, Any]] = field(default_factory=dict)
    available_scope: set[str] = field(default_factory=set)
    degradation_reason: str | None = None
    calculation_config: dict[str, Any] = field(default_factory=dict)
    division: str = "d1"
    method_id: str = "sidereal_rasi"
    formula_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class ChartBundle:
    """会话级缓存对象。铁律三：排盘只跑一次。"""

    bazi: BaziChart
    vedic: VedicChart
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class PairChartBundle:
    """两名命主的已排双盘；合盘只组合已有 ChartBundle，不重复排盘。"""

    a: ChartBundle
    b: ChartBundle
    a_profile_id: str = ""
    b_profile_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.a_profile_id and self.a_profile_id == self.b_profile_id:
            raise ValueError("合盘必须使用两个不同档案")

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(frozen=True)
class PairEvidence:
    """合盘证据；subject 明确该证据属于 A、B 或双方互动。"""

    system: System
    subject: str
    claim: str
    refs: dict[str, tuple[str, ...]]
    polarity: Polarity = Polarity.NEUTRAL
    weight: float = 0.5
    source: str = ""
    fact_key: str = ""
    category: str = "synastry"

    def __post_init__(self) -> None:
        from . import ids

        if self.subject not in {"A", "B", "pair"}:
            raise ValueError("合盘证据 subject 必须是 A、B 或 pair")
        if not self.refs or not any(self.refs.values()):
            raise ValueError("合盘证据至少需要一个 highlight ID")
        if set(self.refs) - {"A", "B"}:
            raise ValueError("合盘证据 refs 只能按 A／B 分组")
        ids.validate_all(ref for values in self.refs.values() for ref in values)
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"合盘证据 weight 须在 0-1，收到 {self.weight}")

    @property
    def highlight(self) -> dict[str, list[str]]:
        return {
            subject: list(dict.fromkeys(self.refs.get(subject, ())))
            for subject in ("A", "B")
        }

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class PairAssessment:
    """双方主题合盘的可审计结果；不把互动信号直接升级为事件预言。"""

    topic: str
    status: str
    headline: str
    layers: dict[str, str]
    conditions: list[str]
    evidence: list[PairEvidence]
    as_of: date

    def __post_init__(self) -> None:
        if self.topic not in {"relationship", "collaboration", "property", "children"}:
            raise ValueError("当前合盘主题必须是 relationship、collaboration、property 或 children")
        if self.status not in {"converge", "pressure", "reconciled", "withheld"}:
            raise ValueError("非法合盘状态")
        if not self.evidence:
            raise ValueError("合盘结果必须携带证据")

    @property
    def highlight(self) -> dict[str, list[str]]:
        return {
            subject: list(dict.fromkeys(
                ref
                for item in self.evidence
                for ref in item.refs.get(subject, ())
            ))
            for subject in ("A", "B")
        }

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["evidence"] = [item.to_dict() for item in self.evidence]
        result["highlight"] = self.highlight
        return result


@dataclass
class Evidence:
    """证据原子。"""

    system: System
    claim: str
    refs: list[str]
    polarity: Polarity = Polarity.NEUTRAL
    weight: float = 0.5
    source: str = ""

    def __post_init__(self) -> None:
        from . import ids

        ids.validate_all(self.refs)
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"weight 须在 0-1，收到 {self.weight}")


@dataclass(frozen=True)
class RaoTopicSpec:
    """D1 与主题分盘之间的确定性角色映射。"""

    key: str
    houses: tuple[int, ...]
    varga: str
    natural_karakas: tuple[str, ...]

    def __post_init__(self) -> None:
        from . import ids

        if not self.houses or any(not 1 <= house <= 12 for house in self.houses):
            raise ValueError(f"Rao 主题宫须为非空的 1-12 元组，收到 {self.houses}")
        if len(set(self.houses)) != len(self.houses):
            raise ValueError(f"Rao 主题宫不得重复，收到 {self.houses}")
        if self.varga not in ids.VARGAS[1:]:
            raise ValueError(f"Rao 主题分盘无效：{self.varga!r}")
        if not self.natural_karakas:
            raise ValueError("Rao 主题至少需要一颗自然指示星")
        for graha in self.natural_karakas:
            if graha not in ids.GRAHAS:
                raise ValueError(f"Rao 自然指示星无效：{graha!r}")


@dataclass
class D1Verdict:
    """主题在 D1 是否获得成立许可；强度仅作规则诊断。"""

    dimension: str
    promise: bool
    strength: float
    evidence: list[Evidence] = field(default_factory=list)
    afflictions: list[Evidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"D1 strength 须在 0-1，收到 {self.strength}")

    @property
    def highlight(self) -> list[str]:
        """汇总实际参与 D1 裁决的位置。"""
        return list(dict.fromkeys(
            ref
            for item in (*self.evidence, *self.afflictions)
            for ref in item.refs
        ))

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class RaoAssessment:
    """D1、D9 与主题分盘合并后的规则层验证结果。"""

    topic: RaoTopicSpec
    d1: D1Verdict
    signal: RaoSignal
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def highlight(self) -> list[str]:
        """汇总全部可高亮位置，并保持首次出现顺序。"""
        return list(dict.fromkeys([
            *self.d1.highlight,
            *(ref for item in self.evidence for ref in item.refs),
        ]))

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class DimensionResult:
    """单一系统对单一维度的判断。"""

    dimension: str
    system: System
    verdict: str
    score: float
    confidence: Confidence
    evidence: list[Evidence] = field(default_factory=list)
    rule_trace: RaoAssessment | None = None

    @property
    def highlight(self) -> list[str]:
        """由 evidence.refs 汇总去重，保持出现顺序。"""
        seen: dict[str, None] = {}
        for evidence in self.evidence:
            for ref in evidence.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class CrossValidation:
    """交叉验证结果——规则层必须给出可消费的合参判断。"""

    dimension: str
    status: CrossStatus
    note: str
    bazi: DimensionResult
    vedic: DimensionResult | None = None
    resolution: str = ""
    conditions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def highlight(self) -> dict[str, list[str]]:
        resolved: dict[str, list[str]] = {"bazi": [], "vedic": []}
        for evidence in self.evidence:
            resolved[evidence.system.value].extend(evidence.refs)
        return {
            "bazi": list(dict.fromkeys([*self.bazi.highlight, *resolved["bazi"]])),
            "vedic": list(dict.fromkeys([
                *(self.vedic.highlight if self.vedic else []),
                *resolved["vedic"],
            ])),
        }

    @property
    def confidence(self) -> Confidence:
        """整体置信度取两系统较低者。"""
        if self.vedic is None:
            return Confidence.LOW
        order = [Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
        return min(self.bazi.confidence, self.vedic.confidence, key=order.index)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        result["confidence"] = self.confidence.value
        return result


@dataclass
class ResonanceResult:
    """时间共振——八字大运/流年 与 印占 daśā 是否同时亮起同类信号。"""

    dimension: str
    year: int
    resonant: bool
    note: str
    bazi_period: dict[str, Any] = field(default_factory=dict)
    vedic_period: dict[str, Any] = field(default_factory=dict)
    highlight: dict[str, list[str]] = field(
        default_factory=lambda: {"bazi": [], "vedic": []}
    )

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(frozen=True)
class LifeEvent:
    """用户确认的人生事件，仅作分析上下文，绝不用于出生时间校正。"""

    occurred_on: date
    dimension: str
    summary: str
    direction: EventDirection = EventDirection.UNDETERMINED
    event_forms: list[EventForm] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.event_forms) != len(set(self.event_forms)):
            raise ValueError("LifeEvent event_forms 不得重复")

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(frozen=True)
class TimelineObservation:
    """用户对年份与主题的核验，不等同于已发生经历或正式盲测。"""

    year: int
    dimension: str
    status: ObservationStatus
    summary: str = ""
    direction: EventDirection = EventDirection.UNDETERMINED
    event_forms: list[EventForm] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.event_forms) != len(set(self.event_forms)):
            raise ValueError("TimelineObservation event_forms 不得重复")
        if self.status is not ObservationStatus.PRESENT and (
            self.direction is not EventDirection.UNDETERMINED or self.event_forms
        ):
            raise ValueError("只有 present 核验项可以填写方向或事件形态")

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class HistoryValidation:
    """历史事件与既有时间信号的对照，不改变任何排盘结果。"""

    event: LifeEvent
    resonance: ResonanceResult
    matched: bool
    note: str
    predicted_direction: EventDirection = EventDirection.UNDETERMINED
    direction_matched: bool | None = None
    predicted_event_forms: list[EventForm] = field(default_factory=list)
    event_form_overlap: bool | None = None

    @property
    def highlight(self) -> dict[str, list[str]]:
        return self.resonance.highlight

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(frozen=True)
class SourceExcerpt:
    """从已授权资料库检索出的短摘录及其可追溯出处。"""

    source_id: str
    title: str
    locator: str
    excerpt: str
    tradition: str = ""
    authority: str = ""
    license_note: str = ""
    source_url: str = ""
    dimensions: tuple[str, ...] = ()


@dataclass
class DeepInsight:
    """可深挖但不可越界的规则层洞察。

    每条内容都须说明它是盘面结构还是待验证假设，并给出可观察的验证问题与
    实际建议。它绝不用于断言用户未披露的私密事实。
    """

    dimension: str
    title: str
    statement: str
    kind: InsightKind
    confidence: Confidence
    verification_questions: list[str] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        """深度洞察没有证据与高亮即视为无效。"""
        if not self.evidence:
            raise ValueError("DeepInsight 至少需要一条 Evidence")

    @property
    def highlight(self) -> list[str]:
        """由证据汇总高亮，确保深度洞察也可回指盘面。"""
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class ReportSection:
    """用户报告的一段确定性内容，不能脱离证据独立存在。"""

    title: str
    body: str
    confidence: Confidence
    evidence: list[Evidence] = field(default_factory=list)
    verification_questions: list[str] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("ReportSection 至少需要一条 Evidence")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class HistoricalAnchor:
    """历史区间中的规则主题信号，只供用户核验而不宣称事件已经发生。"""

    year: int
    role: str
    statement: str
    verification_question: str
    evidence: list[Evidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("HistoricalAnchor 至少需要一条 Evidence")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class HistoricalChain:
    """把长期结构、历史主题信号与后续观察条件连接为可审计链条。"""

    dimension: str
    statement: str
    confidence: Confidence
    anchors: list[HistoricalAnchor] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    continuation_conditions: list[str] = field(default_factory=list)
    interruption_conditions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.anchors:
            raise ValueError("HistoricalChain 至少需要一个 HistoricalAnchor")

    @property
    def evidence(self) -> list[Evidence]:
        return [item for anchor in self.anchors for item in anchor.evidence]

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for anchor in self.anchors:
            for ref in anchor.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["evidence"] = [_serialize(item) for item in self.evidence]
        result["highlight"] = self.highlight
        return result


@dataclass
class AnalysisStep:
    """一条可公开展示的确定性规则步骤，不能脱离盘面证据独立存在。"""

    kind: AnalysisStepKind
    title: str
    body: str
    confidence: Confidence
    evidence: list[Evidence] = field(default_factory=list)
    verification_questions: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("AnalysisStep 至少需要一条 Evidence")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class AnalysisRun:
    """一次问题对应的公开规则步骤集合。"""

    question: str
    scope: str
    steps: list[AnalysisStep] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("AnalysisRun 至少需要一个 AnalysisStep")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for step in self.steps:
            for ref in step.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "scope": self.scope,
            "steps": [step.to_dict() for step in self.steps],
            "highlight": self.highlight,
        }


@dataclass(frozen=True)
class AnalysisFeedback:
    """绑定原公开步骤的用户反馈，只作误差归因线索。"""

    id: str
    message_id: str
    step_index: int
    rating: StepFeedbackRating
    step_hash: str
    highlight: list[str]
    note: str
    created_at: datetime

    def __post_init__(self) -> None:
        from . import ids

        if self.step_index < 0:
            raise ValueError("反馈步骤序号不能为负数")
        if len(self.step_hash) != 64:
            raise ValueError("反馈步骤摘要必须为 SHA-256")
        if not self.highlight and self.rating not in {
            StepFeedbackRating.HELPFUL, StepFeedbackRating.UNHELPFUL,
        }:
            raise ValueError("反馈必须绑定原步骤 highlight")
        ids.validate_all(self.highlight)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class UserReport:
    """纯规则层组装的用户报告。"""

    as_of: date
    generation: str
    summary: str
    sections: list[ReportSection]

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for section in self.sections:
            for ref in section.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "generation": self.generation,
            "summary": self.summary,
            "sections": [section.to_dict() for section in self.sections],
            "highlight": self.highlight,
        }


@dataclass
class UserAnswer:
    """可直接展示的确定性客户回答，高亮继承自同一份报告。"""

    generation: str
    text: str
    highlight: list[str]

    def __post_init__(self) -> None:
        from . import ids

        if not self.text.strip():
            raise ValueError("客户回答不能为空")
        if not self.highlight:
            raise ValueError("客户回答必须携带 highlight")
        ids.validate_all(self.highlight)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(frozen=True)
class AnswerQualityCheck:
    """一次回答的内容交付检查，不代表命理命中率。"""

    key: str
    label: str
    passed: bool
    weight: int
    detail: str


@dataclass
class AnswerQualityAudit:
    """回答完整度审计；准确性仍须由冻结／揭盲样本另行证明。"""

    score: int
    content_ready: bool
    accuracy_status: str
    checks: list[AnswerQualityCheck]
    highlight: list[str]

    def __post_init__(self) -> None:
        if not self.checks:
            raise ValueError("回答质量审计至少需要一项检查")
        if not self.highlight:
            raise ValueError("回答质量审计必须绑定实际盘面 highlight")
        if self.score < 0 or self.score > 100:
            raise ValueError("回答质量分数必须在 0 到 100 之间")

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass
class CandidateJudgment:
    """由既有规则结果裁出的主判断、次候选或排除项。"""

    dimension: str
    rank: CandidateRank
    kind: str
    statement: str
    reason: str
    confidence: Confidence
    evidence: list[Evidence]
    direction: EventDirection = EventDirection.UNDETERMINED

    def __post_init__(self) -> None:
        from . import ids

        if self.kind not in {"structure", "timing"}:
            raise ValueError("候选类型必须为 structure 或 timing")
        if not self.statement.strip() or not self.reason.strip():
            raise ValueError("候选判断与裁决理由不能为空")
        if not self.evidence:
            raise ValueError("候选判断必须携带 Evidence")
        ids.validate_all(self.highlight)

    @property
    def highlight(self) -> list[str]:
        """返回首屏用的决定性定位，完整证据仍保留在 ``evidence``。

        一套体系只取权重最高的 Evidence，避免把所有被检查过的位置误标成
        同等重要；这只是展示投影，不改变候选排序、证据内容或规则判断。
        """
        selected: dict[System, Evidence] = {}
        for item in self.evidence:
            if not item.refs:
                continue
            current = selected.get(item.system)
            if current is None or item.weight > current.weight:
                selected[item.system] = item
        refs = list(dict.fromkeys(
            ref
            for item in selected.values()
            for ref in item.refs
        ))
        if refs:
            return refs
        return list(dict.fromkeys(ref for item in self.evidence for ref in item.refs))

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass(frozen=True)
class ChartFact:
    """可交给解释模型的已计算盘面事实。

    fact_id 仅用于结论引用；真正的可视定位仍由 highlight 完成。
    """

    fact_id: str
    system: System
    category: str
    statement: str
    highlight: tuple[str, ...]
    dimensions: tuple[str, ...] = ()
    # Internal dependency hints for deterministic fact retrieval.  They are
    # deliberately omitted from to_dict(): callers/users only see canonical
    # facts, while the tool layer can resolve the smallest static closure.
    related_entities: tuple[str, ...] = ()
    required_static_fact_ids: tuple[str, ...] = ()
    topic_static_fact_ids: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def __post_init__(self) -> None:
        from . import ids

        if not re.fullmatch(r"fact\.(?:bazi|vedic)\.[a-z0-9_.-]+", self.fact_id):
            raise ValueError(f"盘面事实 fact_id 无效：{self.fact_id!r}")
        if self.category not in {"foundation", "varga", "timing"}:
            raise ValueError(f"盘面事实 category 无效：{self.category!r}")
        if not self.statement.strip() or not self.highlight:
            raise ValueError("盘面事实必须有文本与盘面定位")
        ids.validate_all(self.highlight)
        if any(ids.system_of(ref) != self.system.value for ref in self.highlight):
            raise ValueError("盘面事实不得混用两套体系的定位 ID")
        dependency_ids = [
            *self.required_static_fact_ids,
            *(fact_id for _, fact_ids in self.topic_static_fact_ids for fact_id in fact_ids),
        ]
        if any(not re.fullmatch(r"fact\.(?:bazi|vedic)\.[a-z0-9_.-]+", fact_id)
               for fact_id in dependency_ids):
            raise ValueError("盘面事实依赖 fact_id 无效")
        if len({topic for topic, _ in self.topic_static_fact_ids}) != len(self.topic_static_fact_ids):
            raise ValueError("盘面事实主题依赖不得重复")

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        for key in ("related_entities", "required_static_fact_ids", "topic_static_fact_ids"):
            result.pop(key, None)
        return result


@dataclass
class ReasoningPacket:
    """一次问答的唯一冻结推理包；其中不含未验证的命理结论。"""

    question: str
    cross_validations: list[CrossValidation]
    insights: list[DeepInsight] = field(default_factory=list)
    history: list[HistoryValidation] = field(default_factory=list)
    historical_chains: list[HistoricalChain] = field(default_factory=list)
    forecast: list[ForecastWindow] = field(default_factory=list)
    sources: list[SourceExcerpt] = field(default_factory=list)
    candidates: list[CandidateJudgment] = field(default_factory=list)
    chart_facts: list[ChartFact] = field(default_factory=list)
    dimensions: tuple[str, ...] = ()
    scope: str = "定向问题"
    include_timeline: bool = False
    include_history: bool = False
    include_current_phase: bool = True
    lifecycle_focus: bool = False
    analysis_mode: str = "standard"
    reasoning_mode: str = "dual"
    answer_contract: dict[str, bool] = field(default_factory=dict)
    time_scope: dict[str, str] | None = None
    subject_scope: str | None = None
    relationship_state: str | None = None

    def __post_init__(self) -> None:
        """冻结问题范围，确保后续三种表现共用同一组维度。"""
        if not self.question.strip():
            raise ValueError("推理包的用户问题不能为空")
        if self.relationship_state not in {None, "single", "partnered", "separated"}:
            raise ValueError("推理包 relationship_state 无效")
        if self.reasoning_mode not in {"bazi", "vedic", "dual"}:
            raise ValueError("推理包 reasoning_mode 无效")
        if not self.cross_validations:
            raise ValueError("推理包至少需要一条规则层合参结果")
        resolved = tuple(item.dimension for item in self.cross_validations)
        if self.dimensions and self.dimensions != resolved:
            raise ValueError("推理包维度必须与合参结果完全一致")
        self.dimensions = resolved
        allowed = set(resolved)
        if any(item.dimension not in allowed for item in self.historical_chains):
            raise ValueError("历史影响链包含本次问题范围外的维度")
        if any(item.dimension not in allowed for item in self.forecast):
            raise ValueError("未来窗口包含本次问题范围外的维度")
        if any(item.dimension not in allowed for item in self.candidates):
            raise ValueError("候选裁决包含本次问题范围外的维度")
        fact_ids = [item.fact_id for item in self.chart_facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("盘面事实 fact_id 不得重复")
        expected_systems = (
            {self.reasoning_mode}
            if self.reasoning_mode in {"bazi", "vedic"}
            else {"bazi", "vedic"}
        )
        if any(item.system.value not in expected_systems for item in self.chart_facts):
            raise ValueError("盘面事实越过了当前推理模式")
        if any(set(item.dimensions) - allowed for item in self.chart_facts):
            raise ValueError("盘面事实包含本题范围外的维度")
        if self.time_scope is not None:
            required = {"granularity", "start", "end", "label"}
            if set(self.time_scope) != required:
                raise ValueError("推理包 time_scope 字段不完整")
            if date.fromisoformat(self.time_scope["start"]) >= date.fromisoformat(self.time_scope["end"]):
                raise ValueError("推理包 time_scope 起始时间必须早于结束时间")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for validation in self.cross_validations:
            for refs in validation.highlight.values():
                for ref in refs:
                    seen.setdefault(ref, None)
        for validation in self.history:
            for refs in validation.highlight.values():
                for ref in refs:
                    seen.setdefault(ref, None)
        for chain in self.historical_chains:
            for ref in chain.highlight:
                seen.setdefault(ref, None)
        for window in self.forecast:
            for ref in window.highlight:
                seen.setdefault(ref, None)
        for insight in self.insights:
            for ref in insight.highlight:
                seen.setdefault(ref, None)
        for candidate in self.candidates:
            for ref in candidate.highlight:
                seen.setdefault(ref, None)
        for fact in self.chart_facts:
            for ref in fact.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        candidates = []
        for index, candidate in enumerate(self.candidates):
            item = candidate.to_dict()
            item["candidate_index"] = index
            candidates.append(item)
        return {
            "question": self.question,
            "cross_validations": [item.to_dict() for item in self.cross_validations],
            "insights": [item.to_dict() for item in self.insights],
            "history": [item.to_dict() for item in self.history],
            "historical_chains": [item.to_dict() for item in self.historical_chains],
            "forecast": [item.to_dict() for item in self.forecast],
            "sources": [_serialize(item) for item in self.sources],
            "candidates": candidates,
            "chart_facts": [item.to_dict() for item in self.chart_facts],
            "dimensions": list(self.dimensions),
            "scope": self.scope,
            "include_timeline": self.include_timeline,
            "include_history": self.include_history,
            "include_current_phase": self.include_current_phase,
            "lifecycle_focus": self.lifecycle_focus,
            "analysis_mode": self.analysis_mode,
            "reasoning_mode": self.reasoning_mode,
            "answer_contract": dict(self.answer_contract),
            "time_scope": dict(self.time_scope) if self.time_scope is not None else None,
            "subject_scope": self.subject_scope,
            "relationship_state": self.relationship_state,
            "highlight": self.highlight,
        }


@dataclass
class UserProfile:
    """本地档案：出生资料及其明确选择的排盘配置。"""

    id: str
    birth: BirthInput
    zishi_rule: ZiShiRule
    timezone: str
    created_at: datetime
    label: str = ""
    profile_version_id: str | None = None
    current_version_id: str | None = None
    archived_at: str | None = None
    calculation_config: dict[str, Any] | None = None
    configuration_provenance: str = ""
    owner_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        for key in ("calculation_config", "configuration_provenance", "owner_id"):
            result.pop(key, None)
        if self.profile_version_id is None:
            for key in ("profile_version_id", "current_version_id", "archived_at"):
                result.pop(key, None)
        return result


@dataclass
class Conversation:
    """围绕同一档案持续提问的会话。"""

    id: str
    profile_id: str
    created_at: datetime
    last_activity_at: datetime | None = None
    profile_version_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        if self.profile_version_id is None:
            result.pop("profile_version_id", None)
        return result


@dataclass
class ForecastWindow:
    """规则层识别的未来观察窗口，不把倾向表述为必然事件。"""

    dimension: str
    start: datetime
    end: datetime
    verdict: str
    confidence: Confidence
    evidence: list[Evidence] = field(default_factory=list)
    direction: EventDirection = EventDirection.UNDETERMINED
    triggered: bool = True
    history_calibration: str | None = None
    rule_signal: RaoSignal | None = None
    arm_predictions: dict[str, bool] = field(default_factory=dict)
    event_forms: list[EventForm] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.event_forms) != len(set(self.event_forms)):
            raise ValueError("ForecastWindow event_forms 不得重复")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["highlight"] = self.highlight
        return result


@dataclass
class ForecastPhase:
    """将相邻且主判断一致的观察窗口压缩为一个可核验阶段。"""

    start: datetime
    end: datetime
    windows: list[ForecastWindow]
    priority: ForecastPriority

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError("ForecastPhase 起始时间必须早于结束时间")
        if not self.windows:
            raise ValueError("ForecastPhase 至少需要一条 ForecastWindow")

    @property
    def confidence(self) -> Confidence:
        """采用阶段内最低置信度，避免压缩后虚增把握。"""
        order = [Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
        return min((item.confidence for item in self.windows), key=order.index)

    @property
    def evidence(self) -> list[Evidence]:
        """汇总阶段内全部决定性证据并保持原顺序。"""
        result: dict[tuple[object, ...], Evidence] = {}
        for window in self.windows:
            for item in window.evidence:
                key = (item.system, item.claim, tuple(item.refs), item.source)
                result.setdefault(key, item)
        return list(result.values())

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        result["confidence"] = self.confidence.value
        result["highlight"] = self.highlight
        return result


@dataclass
class BlindSignal:
    """冻结快照中的逐年、逐维度规则信号。"""

    year: int
    dimension: str
    strength: BlindSignalStrength
    verdict: str
    confidence: Confidence
    evidence: list[Evidence] = field(default_factory=list)
    direction: EventDirection = EventDirection.UNDETERMINED
    event_forms: list[EventForm] = field(default_factory=list)
    # 未达到正式触发门槛的背景形态，只供回放诊断；绝不参与正式评分。
    secondary_event_forms: list[EventForm] = field(default_factory=list)
    arm_predictions: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("BlindSignal 至少需要一条 Evidence")
        if len(self.event_forms) != len(set(self.event_forms)):
            raise ValueError("BlindSignal event_forms 不得重复")
        if len(self.secondary_event_forms) != len(set(self.secondary_event_forms)):
            raise ValueError("BlindSignal secondary_event_forms 不得重复")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.evidence:
            for ref in item.refs:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        # 旧版快照没有 direction；未定向时保持旧序列化，使历史摘要仍可验签。
        if self.direction is EventDirection.UNDETERMINED:
            result.pop("direction", None)
        if not self.event_forms:
            result.pop("event_forms", None)
        if not self.secondary_event_forms:
            result.pop("secondary_event_forms", None)
        if not self.arm_predictions:
            result.pop("arm_predictions", None)
        result["highlight"] = self.highlight
        return result


@dataclass
class BlindSnapshot:
    """经历揭晓前冻结的规则结果；内容摘要用于检测事后篡改。"""

    case_id: str
    frozen_at: datetime
    rule_digest: str
    start_year: int
    end_year: int
    dimensions: tuple[str, ...]
    structural_results: list[CrossValidation]
    signals: list[BlindSignal]
    content_hash: str
    calculation_fingerprint: str = ""
    subject_fingerprint: str = ""

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for result in self.structural_results:
            for refs in result.highlight.values():
                for ref in refs:
                    seen.setdefault(ref, None)
        for signal in self.signals:
            for ref in signal.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "case_id": self.case_id,
            "frozen_at": self.frozen_at.isoformat(),
            "rule_digest": self.rule_digest,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "dimensions": list(self.dimensions),
            "structural_results": [item.to_dict() for item in self.structural_results],
            "signals": [item.to_dict() for item in self.signals],
            "content_hash": self.content_hash,
            "highlight": self.highlight,
        }
        if self.calculation_fingerprint:
            result["calculation_fingerprint"] = self.calculation_fingerprint
        if self.subject_fingerprint:
            result["subject_fingerprint"] = self.subject_fingerprint
        return result


@dataclass(frozen=True)
class BlindObservation:
    """揭晓阶段的独立观察格，不修改冻结快照。"""

    year: int
    dimension: str
    status: ObservationStatus
    summary: str = ""
    direction: EventDirection = EventDirection.UNDETERMINED
    event_forms: list[EventForm] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.event_forms) != len(set(self.event_forms)):
            raise ValueError("BlindObservation event_forms 不得重复")
        if self.event_forms and self.status is not ObservationStatus.PRESENT:
            raise ValueError("只有 present 观察项可以填写 event_forms")

    def to_dict(self) -> dict[str, Any]:
        result = _serialize(self)
        if not self.event_forms:
            result.pop("event_forms", None)
        return result


@dataclass
class BlindEvaluationItem:
    """一条冻结信号与一条真人观察的对照。"""

    observation: BlindObservation
    signal: BlindSignal

    @property
    def highlight(self) -> list[str]:
        return self.signal.highlight

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation": self.observation.to_dict(),
            "signal": self.signal.to_dict(),
            "highlight": self.highlight,
        }


@dataclass
class BlindScorecard:
    """同一冻结快照在四组固定策略下的客观评分。"""

    case_id: str
    snapshot_hash: str
    rule_digest: str
    items: list[BlindEvaluationItem]
    any_signal: dict[str, int | float | None]
    bazi_only: dict[str, int | float | None]
    vedic_only: dict[str, int | float | None]
    cross_system: dict[str, int | float | None]
    comparisons: dict[str, dict[str, int | float | None]]
    direction: dict[str, int | float | None] = field(default_factory=dict)
    event_forms: dict[str, int | float | None] = field(default_factory=dict)
    subject_fingerprint: str = ""
    content_hash: str = ""

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for item in self.items:
            for ref in item.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "case_id": self.case_id,
            "snapshot_hash": self.snapshot_hash,
            "rule_digest": self.rule_digest,
            "items": [item.to_dict() for item in self.items],
            "any_signal": self.any_signal,
            "bazi_only": self.bazi_only,
            "vedic_only": self.vedic_only,
            "cross_system": self.cross_system,
            "comparisons": self.comparisons,
            "direction": self.direction,
            "event_forms": self.event_forms,
            "highlight": self.highlight,
        }
        if self.subject_fingerprint:
            result["subject_fingerprint"] = self.subject_fingerprint
        if self.content_hash:
            result["content_hash"] = self.content_hash
        return result


@dataclass
class BlindBenchmark:
    """同一规则版本下的跨样本三臂盲测汇总。"""

    rule_digest: str
    scorecards: list[BlindScorecard]
    any_signal: dict[str, int | float | None]
    bazi_only: dict[str, int | float | None]
    vedic_only: dict[str, int | float | None]
    cross_system: dict[str, int | float | None]
    comparisons: dict[str, dict[str, int | float | None]]
    direction: dict[str, int | float | None] = field(default_factory=dict)
    event_forms: dict[str, int | float | None] = field(default_factory=dict)
    by_dimension: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scorecards:
            raise ValueError("BlindBenchmark 至少需要一份评分卡")

    @property
    def highlight(self) -> list[str]:
        seen: dict[str, None] = {}
        for scorecard in self.scorecards:
            for ref in scorecard.highlight:
                seen.setdefault(ref, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_digest": self.rule_digest,
            "case_ids": [item.case_id for item in self.scorecards],
            "snapshot_hashes": [item.snapshot_hash for item in self.scorecards],
            "observation_count": sum(len(item.items) for item in self.scorecards),
            "scorecards": [item.to_dict() for item in self.scorecards],
            "any_signal": self.any_signal,
            "bazi_only": self.bazi_only,
            "vedic_only": self.vedic_only,
            "cross_system": self.cross_system,
            "comparisons": self.comparisons,
            "direction": self.direction,
            "event_forms": self.event_forms,
            "by_dimension": self.by_dimension,
            "highlight": self.highlight,
        }


def confidence_from_precision(precision: TimePrecision) -> Confidence:
    """the TwinSky project spec §6.3 分级降级：印占置信度由输入时间精度决定。"""
    return {
        TimePrecision.EXACT: Confidence.HIGH,
        TimePrecision.PERIOD: Confidence.MEDIUM,
        TimePrecision.UNKNOWN: Confidence.LOW,
        BirthPrecision.SECOND: Confidence.HIGH,
        BirthPrecision.MINUTE: Confidence.HIGH,
        BirthPrecision.TIME_RANGE: Confidence.MEDIUM,
        BirthPrecision.DATE: Confidence.LOW,
    }[precision]


def vedic_available_scope(precision: TimePrecision) -> set[str]:
    """该精度下印占哪些部分可用。降级必须对用户可见，不可静默处理。"""
    if precision in {TimePrecision.EXACT, BirthPrecision.MINUTE, BirthPrecision.SECOND}:
        return {"lagna", "houses", "dasha", "vargas", "grahas"}
    if precision in {TimePrecision.PERIOD, BirthPrecision.TIME_RANGE}:
        return {"grahas"}
    return set()


def _serialize(obj: Any) -> Any:
    """dataclass -> dict，枚举转值，datetime 转 ISO 字符串。"""

    def convert(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    return convert(asdict(obj))
