"""
Explainability Module
Provides human-readable explanations for anomaly detections
"""
from typing import Dict, Any, List
import numpy as np

from config.logging_config import get_logger

logger = get_logger(__name__)


class AnomalyExplainer:
    """Generate explanations for detected anomalies"""
    
    @staticmethod
    def explain(
        feature_vector: np.ndarray,
        feature_names: List[str],
        anomaly_score: float,
        feature_importance: np.ndarray = None
    ) -> str:
        """
        Generate explanation for an anomaly
        
        Args:
            feature_vector: Feature values for the anomaly
            feature_names: Names of features
            anomaly_score: Anomaly score (0-1)
            feature_importance: Feature importance scores (optional)
        
        Returns:
            Human-readable explanation
        """
        explanations = []
        
        # Check specific features
        feature_dict = dict(zip(feature_names, feature_vector))
        
        # Time-based anomalies
        if 'hour_of_day' in feature_dict:
            hour = int(feature_dict['hour_of_day'])
            if hour < 6 or hour > 22:
                explanations.append(f"unusual activity time ({hour:02d}:00)")
        
        # Severity
        if 'severity_level' in feature_dict:
            severity = int(feature_dict['severity_level'])
            if severity >= 4:
                explanations.append("critical/high severity event")
        
        # Message length
        if 'message_length' in feature_dict:
            msg_len = int(feature_dict['message_length'])
            if msg_len > 1000:
                explanations.append("extremely long log message")
            elif msg_len < 5:
                explanations.append("suspiciously short message")
        
        # Process information
        if 'has_process' in feature_dict and feature_dict['has_process'] == 0:
            if 'severity_level' in feature_dict and feature_dict['severity_level'] >= 3:
                explanations.append("high-severity event with no process information")
        
        # Feature importance based explanation
        if feature_importance is not None and len(feature_importance) > 0:
            # Get top contributing features
            top_indices = np.argsort(feature_importance)[-3:][::-1]
            top_features = [feature_names[i] for i in top_indices if i < len(feature_names)]
            
            if top_features and not explanations:
                explanations.append(f"unusual patterns in {', '.join(top_features[:2])}")
        
        # Compile final explanation
        if explanations:
            explanation = f"Anomaly (score: {anomaly_score:.3f}) - " + "; ".join(explanations)
        else:
            explanation = f"Statistical anomaly detected (score: {anomaly_score:.3f})"
        
        return explanation
    
    @staticmethod
    def get_feature_contributions(
        feature_vector: np.ndarray,
        feature_names: List[str],
        baseline: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate how much each feature contributes to anomaly
        
        Args:
            feature_vector: Feature values
            feature_names: Feature names
            baseline: Baseline (mean) feature values
        
        Returns:
            Dictionary of feature contributions
        """
        contributions = {}
        
        for i, name in enumerate(feature_names):
            if i < len(feature_vector) and i < len(baseline):
                # Calculate deviation from baseline
                deviation = abs(feature_vector[i] - baseline[i])
                contributions[name] = float(deviation)
        
        return contributions