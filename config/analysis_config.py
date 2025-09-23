"""
Analysis Configuration and Data Models
Date: 2025-08-27 01:14:49 UTC
User: HarrisonKuo47
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import time

@dataclass
class AnalysisRequest:
    """Data model for analysis request parameters"""
    dxf_filename: str
    pkg_type: str = "ALL"
    lf_type: str = "ALL"
    early_termination: bool = False
    selected_layers: str = ""

@dataclass
class AnalysisPerformance:
    """Performance metrics for analysis"""
    start_time: float
    filtering_time: float = 0.0
    analysis_time: float = 0.0
    total_time: float = 0.0
    
    def calculate_total_time(self) -> float:
        self.total_time = time.time() - self.start_time
        return self.total_time
    
    def to_dict(self) -> Dict:
        return {
            "filtering_time": round(self.filtering_time, 2),
            "analysis_time": round(self.analysis_time, 2),
            "total_time": round(self.total_time, 2)
        }

@dataclass
class AnalysisResult:
    """Complete analysis result data model"""
    analysis_id: str
    leadframe: str
    leadframe_name: str
    analysis_time: str
    total_kits_tested: int
    total_kits_in_database: int
    suitable_kits: List[Dict]
    all_results: List[Dict]
    selected_layers: List[str]
    invalid_layers: List[str]
    filters_applied: Dict
    performance_metrics: Dict
    summary: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "leadframe": self.leadframe,
            "leadframe_name": self.leadframe_name,
            "analysis_time": self.analysis_time,
            "total_kits_tested": self.total_kits_tested,
            "total_kits_in_database": self.total_kits_in_database,
            "suitable_kits": self.suitable_kits,
            "all_results": self.all_results,
            "selected_layers": self.selected_layers,
            "invalid_layers": self.invalid_layers,
            "filters_applied": self.filters_applied,
            "performance_metrics": self.performance_metrics,
            "summary": self.summary
        }