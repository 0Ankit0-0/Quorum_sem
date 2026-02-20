"""
Threat Scoring Engine
Converts anomaly scores to actionable threat levels
"""
from typing import Dict, Any
import numpy as np

from config.logging_config import get_logger

logger = get_logger(__name__)


class ThreatScorer:
    """Convert anomaly scores to threat assessments"""
    
    # Severity thresholds
    THRESHOLDS = {
        'CRITICAL': 0.95,
        'HIGH': 0.85,
        'MEDIUM': 0.70,
        'LOW': 0.50
    }
    
    @staticmethod
    def score_threat(
        anomaly_score: float,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate threat score with contextual adjustments
        
        Args:
            anomaly_score: Base anomaly score (0-1)
            context: Additional context (severity, event_type, etc.)
        
        Returns:
            Threat assessment dictionary
        """
        # Base score
        base_score = anomaly_score * 100
        
        # Contextual adjustments
        multiplier = 1.0
        
        if context:
            # High severity events get boost
            severity = context.get('severity', '').upper()
            if severity in ['CRITICAL', 'HIGH', 'ERROR']:
                multiplier *= 1.2
            
            # Specific event types
            event_type = context.get('event_type', '').lower()
            if any(keyword in event_type for keyword in ['failed', 'error', 'unauthorized']):
                multiplier *= 1.15
            
            # After-hours activity
            hour = context.get('hour_of_day')
            if hour is not None and (hour < 6 or hour > 22):
                multiplier *= 1.1
        
        # Calculate final score
        final_score = min(base_score * multiplier, 100.0)
        
        # Determine severity level
        severity_level = ThreatScorer._get_severity_level(final_score / 100)
        
        return {
            'threat_score': round(final_score, 2),
            'severity': severity_level,
            'base_score': round(base_score, 2),
            'multiplier': round(multiplier, 2),
            'confidence': anomaly_score
        }
    
    @staticmethod
    def _get_severity_level(score: float) -> str:
        """Get severity level from score"""
        if score >= ThreatScorer.THRESHOLDS['CRITICAL']:
            return 'CRITICAL'
        elif score >= ThreatScorer.THRESHOLDS['HIGH']:
            return 'HIGH'
        elif score >= ThreatScorer.THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
        elif score >= ThreatScorer.THRESHOLDS['LOW']:
            return 'LOW'
        else:
            return 'INFO'
    
    @staticmethod
    def batch_score(
        anomaly_scores: np.ndarray,
        contexts: list = None
    ) -> list:
        """
        Score multiple threats at once
        
        Args:
            anomaly_scores: Array of anomaly scores
            contexts: List of context dictionaries
        
        Returns:
            List of threat assessments
        """
        results = []
        
        for i, score in enumerate(anomaly_scores):
            context = contexts[i] if contexts and i < len(contexts) else None
            assessment = ThreatScorer.score_threat(score, context)
            results.append(assessment)
        
        return results