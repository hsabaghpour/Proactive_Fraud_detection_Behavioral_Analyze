from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.feature import PCA
import boto3
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureEngineeringPipeline:
    def __init__(self, spark_config=None, aws_config=None):
        """
        Initialize the feature engineering pipeline with Spark and AWS configurations
        """
        self.spark = (SparkSession.builder
                     .appName("BehavioralBiometrics")
                     .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.1")
                     .getOrCreate())
        
        # AWS Configuration
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_config.get('aws_access_key_id'),
            aws_secret_access_key=aws_config.get('aws_secret_access_key'),
            region_name=aws_config.get('region', 'us-west-2')
        )
        
        self.feature_store_bucket = aws_config.get('feature_store_bucket')
        
    def extract_behavioral_features(self, df):
        """
        Extract advanced behavioral features from raw data
        """
        # Register the DataFrame as a SQL temporary view
        df.createOrReplaceTempView("raw_behavioral_data")
        
        # Complex feature extraction using SQL
        features_df = self.spark.sql("""
            SELECT 
                session_id,
                -- Typing patterns
                avg(time_between_keystrokes) as avg_typing_speed,
                stddev(time_between_keystrokes) as typing_rhythm_consistency,
                percentile_approx(time_between_keystrokes, 0.9) as typing_burst_speed,
                
                -- Mouse movement patterns
                avg(mouse_velocity) as avg_mouse_speed,
                stddev(mouse_movement_angle) as mouse_direction_entropy,
                count(distinct mouse_click_position) as distinct_click_positions,
                
                -- Device characteristics
                collect_set(device_orientation) as device_orientation_changes,
                collect_set(screen_resolution) as screen_resolution_changes,
                
                -- Temporal patterns
                count(*) as total_interactions,
                sum(case when hour(timestamp) between 0 and 5 then 1 else 0 end) as late_night_activity
                
            FROM raw_behavioral_data
            GROUP BY session_id
        """)
        
        return features_df
    
    def create_feature_pipeline(self):
        """
        Create a Spark ML Pipeline for feature processing
        """
        # Vector Assembly
        assembler = VectorAssembler(
            inputCols=[
                "avg_typing_speed", "typing_rhythm_consistency", "typing_burst_speed",
                "avg_mouse_speed", "mouse_direction_entropy", "distinct_click_positions",
                "total_interactions", "late_night_activity"
            ],
            outputCol="features"
        )
        
        # Standardization
        scaler = StandardScaler(
            inputCol="features",
            outputCol="scaled_features",
            withStd=True,
            withMean=True
        )
        
        # Dimensionality Reduction
        pca = PCA(
            k=5,
            inputCol="scaled_features",
            outputCol="pca_features"
        )
        
        # Create the pipeline
        pipeline = Pipeline(stages=[assembler, scaler, pca])
        
        return pipeline
    
    def store_features(self, features_df, version=None):
        """
        Store processed features in AWS S3-based feature store
        """
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Convert Spark DataFrame to Parquet and save to S3
        s3_path = f"s3://{self.feature_store_bucket}/features/version={version}"
        
        try:
            features_df.write.parquet(s3_path, mode="overwrite")
            logger.info(f"Successfully stored features in {s3_path}")
            
            # Store feature metadata
            metadata = {
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "feature_count": len(features_df.columns),
                "row_count": features_df.count()
            }
            
            self.s3_client.put_object(
                Bucket=self.feature_store_bucket,
                Key=f"metadata/version={version}/metadata.json",
                Body=json.dumps(metadata)
            )
            
        except Exception as e:
            logger.error(f"Error storing features: {str(e)}")
            raise
    
    def process_and_store_features(self, input_data):
        """
        Main method to process raw data and store engineered features
        """
        try:
            # Convert input data to Spark DataFrame
            raw_df = self.spark.createDataFrame(input_data)
            
            # Extract behavioral features
            features_df = self.extract_behavioral_features(raw_df)
            
            # Create and fit the feature pipeline
            pipeline = self.create_feature_pipeline()
            processed_features = pipeline.fit(features_df).transform(features_df)
            
            # Store the processed features
            self.store_features(processed_features)
            
            return processed_features
            
        except Exception as e:
            logger.error(f"Error in feature processing pipeline: {str(e)}")
            raise 