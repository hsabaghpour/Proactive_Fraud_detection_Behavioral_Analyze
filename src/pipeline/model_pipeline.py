from pyspark.ml import Pipeline
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.feature import IsolationForest
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from sklearn.ensemble import IsolationForest as SklearnIF
import mlflow
import mlflow.spark
from datetime import datetime
import logging
import json
import boto3
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnomalyDetectionPipeline:
    def __init__(self, aws_config=None, mlflow_config=None):
        """
        Initialize the anomaly detection pipeline with MLflow tracking and AWS integration
        """
        self.aws_config = aws_config
        
        # Initialize MLflow
        mlflow.set_tracking_uri(mlflow_config.get('tracking_uri'))
        mlflow.set_experiment(mlflow_config.get('experiment_name', 'fraud_detection'))
        
        # AWS Configuration
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_config.get('aws_access_key_id'),
            aws_secret_access_key=aws_config.get('aws_secret_access_key'),
            region_name=aws_config.get('region', 'us-west-2')
        )
        
        self.model_bucket = aws_config.get('model_bucket')
        
    def create_ensemble_model(self):
        """
        Create an ensemble of anomaly detection models
        """
        # Isolation Forest for unsupervised anomaly detection
        isolation_forest = IsolationForest(
            featuresCol="pca_features",
            predictionCol="iforest_prediction",
            contamination=0.1,
            numTrees=100
        )
        
        # Random Forest for supervised classification (if labeled data available)
        random_forest = RandomForestClassifier(
            featuresCol="pca_features",
            labelCol="label",
            predictionCol="rf_prediction",
            numTrees=100,
            maxDepth=10
        )
        
        # Create the pipeline
        pipeline = Pipeline(stages=[isolation_forest, random_forest])
        
        return pipeline
        
    def train_model(self, training_data, validation_data=None):
        """
        Train the anomaly detection model with monitoring
        """
        try:
            with mlflow.start_run():
                # Log parameters
                mlflow.log_params({
                    "contamination": 0.1,
                    "num_trees": 100,
                    "max_depth": 10
                })
                
                # Create and train the model
                pipeline = self.create_ensemble_model()
                model = pipeline.fit(training_data)
                
                # Evaluate the model
                if validation_data is not None:
                    predictions = model.transform(validation_data)
                    evaluator = BinaryClassificationEvaluator(
                        labelCol="label",
                        rawPredictionCol="rf_prediction",
                        metricName="areaUnderROC"
                    )
                    auc_roc = evaluator.evaluate(predictions)
                    
                    # Log metrics
                    mlflow.log_metric("auc_roc", auc_roc)
                
                # Save the model
                model_path = f"s3://{self.model_bucket}/models/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                mlflow.spark.save_model(model, model_path)
                
                return model
                
        except Exception as e:
            logger.error(f"Error in model training: {str(e)}")
            raise
            
    def predict_anomalies(self, model, data):
        """
        Make predictions and calculate risk scores
        """
        try:
            # Get predictions from both models
            predictions = model.transform(data)
            
            # Combine predictions from both models
            def calculate_risk_score(row):
                iforest_score = 1 - row['iforest_prediction']  # Convert to risk score
                rf_prob = float(row['rf_prediction'])  # Probability from Random Forest
                
                # Ensemble the scores (weighted average)
                return 0.7 * iforest_score + 0.3 * rf_prob
            
            # Add risk score calculation
            predictions = predictions.withColumn(
                "risk_score",
                calculate_risk_score(struct(*predictions.columns))
            )
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in anomaly prediction: {str(e)}")
            raise
            
    def monitor_model_performance(self, predictions, actual_labels=None):
        """
        Monitor model performance and drift
        """
        try:
            # Calculate performance metrics
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "prediction_count": predictions.count(),
                "average_risk_score": predictions.select("risk_score").mean().collect()[0][0]
            }
            
            if actual_labels is not None:
                # Calculate additional metrics with actual labels
                true_positives = predictions.filter(
                    (predictions.label == 1) & (predictions.risk_score >= 0.7)
                ).count()
                
                false_positives = predictions.filter(
                    (predictions.label == 0) & (predictions.risk_score >= 0.7)
                ).count()
                
                metrics.update({
                    "true_positive_rate": true_positives / predictions.count(),
                    "false_positive_rate": false_positives / predictions.count()
                })
            
            # Store metrics in S3
            self.s3_client.put_object(
                Bucket=self.model_bucket,
                Key=f"metrics/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                Body=json.dumps(metrics)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in model monitoring: {str(e)}")
            raise 