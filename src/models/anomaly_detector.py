from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
import joblib
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BehavioralAnomalyDetector:
    def __init__(self, contamination: float = 0.1):
        """
        Initialize the anomaly detector
        :param contamination: The proportion of outliers in the training set
        """
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted = False

    def _prepare_features(self, features_dict: Dict[str, float]) -> np.ndarray:
        """
        Convert feature dictionary to numpy array
        :param features_dict: Dictionary of features
        :return: Numpy array of features
        """
        if not self.feature_names:
            self.feature_names = list(features_dict.keys())
        
        # Ensure all features are present
        feature_vector = []
        for feature in self.feature_names:
            if feature not in features_dict:
                logger.warning(f"Missing feature: {feature}")
                feature_vector.append(0.0)
            else:
                feature_vector.append(features_dict[feature])
        
        return np.array(feature_vector).reshape(1, -1)

    def fit(self, feature_dicts: List[Dict[str, float]]) -> None:
        """
        Fit the model on training data
        :param feature_dicts: List of feature dictionaries
        """
        if not feature_dicts:
            raise ValueError("No training data provided")

        # Prepare feature matrix
        X = np.vstack([self._prepare_features(f) for f in feature_dicts])
        
        # Fit scaler and transform data
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the model
        self.model.fit(X_scaled)
        self.is_fitted = True
        logger.info("Model fitted successfully")

    def predict(self, features_dict: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict anomaly score for new data
        :param features_dict: Dictionary of features
        :return: Dictionary with prediction results
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before making predictions")

        # Prepare features
        X = self._prepare_features(features_dict)
        X_scaled = self.scaler.transform(X)
        
        # Get raw score and prediction
        raw_score = self.model.score_samples(X_scaled)[0]
        is_anomaly = self.model.predict(X_scaled)[0] == -1
        
        # Convert raw score to probability-like value between 0 and 1
        # Higher values indicate more normal behavior
        normalized_score = 1 / (1 + np.exp(-raw_score))
        
        # Calculate feature importance
        feature_contributions = self._calculate_feature_contributions(X_scaled)
        
        return {
            "is_anomaly": bool(is_anomaly),
            "risk_score": 1 - normalized_score,  # Convert to risk score (higher is riskier)
            "confidence": abs(normalized_score - 0.5) * 2,  # Scale confidence to [0,1]
            "feature_importance": feature_contributions
        }

    def _calculate_feature_contributions(self, X_scaled: np.ndarray) -> Dict[str, float]:
        """
        Calculate the contribution of each feature to the anomaly score
        :param X_scaled: Scaled feature vector
        :return: Dictionary of feature importances
        """
        # Use the absolute scaled values as a simple proxy for feature importance
        feature_importance = {}
        for i, feature_name in enumerate(self.feature_names):
            feature_importance[feature_name] = abs(X_scaled[0, i])
        
        # Normalize to sum to 1
        total = sum(feature_importance.values())
        if total > 0:
            feature_importance = {k: v/total for k, v in feature_importance.items()}
        
        return feature_importance

    def save_model(self, filepath: str) -> None:
        """
        Save the model to disk
        :param filepath: Path to save the model
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted model")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_fitted': self.is_fitted
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")

    @classmethod
    def load_model(cls, filepath: str) -> 'BehavioralAnomalyDetector':
        """
        Load a saved model from disk
        :param filepath: Path to the saved model
        :return: Loaded BehavioralAnomalyDetector instance
        """
        model_data = joblib.load(filepath)
        
        detector = cls()
        detector.model = model_data['model']
        detector.scaler = model_data['scaler']
        detector.feature_names = model_data['feature_names']
        detector.is_fitted = model_data['is_fitted']
        
        logger.info(f"Model loaded from {filepath}")
        return detector 