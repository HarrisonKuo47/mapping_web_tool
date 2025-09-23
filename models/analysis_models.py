"""
Analysis Data Models
Date: 2025-08-27 02:01:26 UTC
User: HarrisonKuo47
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import time

@dataclass
class AnalysisRequest:
    """Request model for analysis"""
    dxf_filename: str
    pkg_type: str = "ALL"
    lf_type: str = "ALL"
    early_termination: bool = False
    selected_layers: str = ""
    
    def get_layers_list(self) -> List[str]:
        """Convert selected_layers string to list"""
        if self.selected_layers:
            return [layer.strip() for layer in self.selected_layers.split(',') if layer.strip()]
        return ["SH-01_OBJECT", "SH-01_DIM", "SH-01_PKG"]

@dataclass
class HandlerKitResult:
    """Result for a single handler kit analysis"""
    handlerkit: str
    handlerkit_name: str
    is_suitable: bool
    pkg_type: str
    lf_type: str
    handler_type: str
    total_elements: int = 0
    overlap_count: int = 0
    overlap_rate: float = 0.0
    output_image_path: Optional[str] = None
    overlap_report_path: Optional[str] = None
    device_type: str = ""
    error: Optional[str] = None

@dataclass
class AnalysisResult:
    """Complete analysis result"""
    analysis_id: str
    leadframe: str
    leadframe_name: str
    analysis_time: str
    total_kits_tested: int
    suitable_kits: List[Dict]
    all_results: List[HandlerKitResult]
    selected_layers: List[str]
    filters_applied: Dict
    performance_metrics: Dict
    summary: Dict
    
    @classmethod
    def from_analysis(cls, analysis_id: str, request: AnalysisRequest, 
                     suitable_kits: List, results: List, 
                     valid_layers: List, performance: Dict) -> 'AnalysisResult':
        """Create AnalysisResult from analysis components"""
        return cls(
            analysis_id=analysis_id,
            leadframe=request.dxf_filename,
            leadframe_name=request.dxf_filename.split('.')[0],
            analysis_time=datetime.utcnow().isoformat(),
            total_kits_tested=len(results),
            suitable_kits=suitable_kits,
            all_results=results,
            selected_layers=valid_layers,
            filters_applied={
                "pkg_type": request.pkg_type,
                "lf_type": request.lf_type,
                "selected_layers": valid_layers,
                "early_termination": request.early_termination
            },
            performance_metrics=performance,
            summary={
                "suitable_count": len(suitable_kits),
                "total_tested": len(results),
                "success_rate": round((len(suitable_kits) / len(results) * 100) if results else 0, 1)
            }
        )