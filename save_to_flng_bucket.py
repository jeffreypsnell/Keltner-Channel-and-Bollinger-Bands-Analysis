"""
Script to save DataFrame as CSV to FLNG Trading Data S3 Bucket

Bucket: flng-trading-data
Region: us-east-2
"""

import pandas as pd
import boto3
from datetime import datetime
import io

# Configuration
BUCKET_NAME = 'flng-trading-data'
REGION = 'us-east-2'


def save_csv_to_s3(dataframe, filename, folder=''):
    """
    Save a pandas DataFrame as CSV to S3 bucket
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        The data to save
    filename : str
        Name of the CSV file (e.g., 'data.csv')
    folder : str, optional
        Folder path within bucket (e.g., 'analysis/' or 'raw_data/')
    
    Returns:
    --------
    str : S3 URI of the saved file
    """
    # Create S3 client
    s3_client = boto3.client('s3', region_name=REGION)
    
    # Prepare the S3 key (path)
    if folder and not folder.endswith('/'):
        folder += '/'
    s3_key = f"{folder}{filename}"
    
    # Convert DataFrame to CSV in memory
    csv_buffer = io.StringIO()
    dataframe.to_csv(csv_buffer, index=True)
    
    # Upload to S3
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        
        s3_uri = f"s3://{BUCKET_NAME}/{s3_key}"
        print(f"[OK] Successfully saved to S3: {s3_uri}")
        return s3_uri
        
    except Exception as e:
        print(f"[ERROR] Failed to save to S3: {e}")
        raise


def save_with_timestamp(dataframe, base_name, folder=''):
    """
    Save DataFrame with timestamp in filename
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        The data to save
    base_name : str
        Base name for the file (e.g., 'spy_data')
    folder : str, optional
        Folder path within bucket
    
    Returns:
    --------
    str : S3 URI of the saved file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{base_name}_{timestamp}.csv"
    
    return save_csv_to_s3(dataframe, filename, folder)


def list_bucket_contents(prefix=''):
    """
    List contents of the S3 bucket
    
    Parameters:
    -----------
    prefix : str, optional
        Filter by prefix/folder
    
    Returns:
    --------
    list : List of file keys in the bucket
    """
    s3_client = boto3.client('s3', region_name=REGION)
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            print(f"No files found in s3://{BUCKET_NAME}/{prefix}")
            return []
        
        files = [obj['Key'] for obj in response['Contents']]
        print(f"Found {len(files)} files in s3://{BUCKET_NAME}/{prefix}")
        
        return files
        
    except Exception as e:
        print(f"[ERROR] Failed to list bucket contents: {e}")
        raise


# Example usage
if __name__ == "__main__":
    
    # Example 1: Create sample data and save to S3
    print("=" * 60)
    print("EXAMPLE: Save Sample Data to FLNG S3 Bucket")
    print("=" * 60)
    
    # Create sample DataFrame
    sample_data = pd.DataFrame({
        'Date': pd.date_range('2026-05-01', periods=10, freq='D'),
        'Price': [100 + i * 0.5 for i in range(10)],
        'Volume': [1000000 + i * 10000 for i in range(10)]
    })
    sample_data.set_index('Date', inplace=True)
    
    print("\nSample Data:")
    print(sample_data.head())
    
    # Save with timestamp
    print("\nSaving to S3...")
    s3_uri = save_with_timestamp(sample_data, 'sample_trading_data', folder='test/')
    
    print("\n" + "=" * 60)
    print("Bucket Contents:")
    print("=" * 60)
    files = list_bucket_contents('test/')
    for file in files:
        print(f"  - {file}")
    
    print("\n" + "=" * 60)
    print("Access your data at:")
    print(f"https://us-east-2.console.aws.amazon.com/s3/buckets/{BUCKET_NAME}?region={REGION}&tab=objects")
    print("=" * 60)
