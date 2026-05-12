# Save Data to FLNG Trading Data S3 Bucket

This folder contains scripts for saving CSV data to the `flng-trading-data` S3 bucket.

## S3 Bucket Information

- **Bucket Name:** `flng-trading-data`
- **Region:** `us-east-2`
- **Console URL:** https://us-east-2.console.aws.amazon.com/s3/buckets/flng-trading-data?region=us-east-2&tab=objects

## Quick Start

### 1. Save a DataFrame to S3

```python
import pandas as pd
from save_to_flng_bucket import save_csv_to_s3, save_with_timestamp

# Create your DataFrame
df = pd.DataFrame({
    'Date': pd.date_range('2026-01-01', periods=100),
    'Price': range(100),
    'Volume': range(1000, 1100)
})

# Option A: Save with specific filename
save_csv_to_s3(df, 'my_data.csv', folder='analysis/')

# Option B: Save with automatic timestamp
save_with_timestamp(df, 'my_data', folder='analysis/')
```

### 2. List Files in Bucket

```python
from save_to_flng_bucket import list_bucket_contents

# List all files
all_files = list_bucket_contents()

# List files in specific folder
analysis_files = list_bucket_contents('analysis/')
```

## Functions Reference

### `save_csv_to_s3(dataframe, filename, folder='')`

Save a pandas DataFrame as CSV to S3 bucket.

**Parameters:**
- `dataframe` (pd.DataFrame): The data to save
- `filename` (str): Name of the CSV file (e.g., 'data.csv')
- `folder` (str, optional): Folder path within bucket (e.g., 'analysis/')

**Returns:**
- `str`: S3 URI of the saved file

**Example:**
```python
s3_uri = save_csv_to_s3(df, 'trading_data.csv', folder='raw/')
# Returns: 's3://flng-trading-data/raw/trading_data.csv'
```

### `save_with_timestamp(dataframe, base_name, folder='')`

Save DataFrame with automatic timestamp in filename.

**Parameters:**
- `dataframe` (pd.DataFrame): The data to save
- `base_name` (str): Base name for the file (e.g., 'spy_data')
- `folder` (str, optional): Folder path within bucket

**Returns:**
- `str`: S3 URI of the saved file

**Example:**
```python
s3_uri = save_with_timestamp(df, 'keltner_signals', folder='signals/')
# Returns: 's3://flng-trading-data/signals/keltner_signals_20260512_143022.csv'
```

### `list_bucket_contents(prefix='')`

List contents of the S3 bucket.

**Parameters:**
- `prefix` (str, optional): Filter by prefix/folder

**Returns:**
- `list`: List of file keys in the bucket

**Example:**
```python
files = list_bucket_contents('analysis/')
# Returns: ['analysis/data1.csv', 'analysis/data2.csv', ...]
```

## Usage Examples

### Example 1: Save Trading Signals

```python
import pandas as pd
from save_to_flng_bucket import save_with_timestamp

# Your trading signals DataFrame
signals = pd.DataFrame({
    'timestamp': pd.date_range('2026-05-01', periods=50, freq='H'),
    'signal': ['BUY', 'HOLD', 'SELL'] * 16 + ['HOLD', 'HOLD'],
    'price': [100 + i * 0.1 for i in range(50)],
    'confidence': [0.8, 0.6, 0.7] * 16 + [0.5, 0.6]
})

# Save with timestamp
s3_uri = save_with_timestamp(signals, 'keltner_signals', folder='signals/')
print(f"Saved to: {s3_uri}")
```

### Example 2: Save Daily Analysis Results

```python
import pandas as pd
from datetime import datetime
from save_to_flng_bucket import save_csv_to_s3

# Your analysis results
results = pd.DataFrame({
    'strategy': ['Bollinger Bands', 'Keltner Channels', 'Combined'],
    'win_rate': [0.65, 0.68, 0.72],
    'avg_return': [0.02, 0.025, 0.03],
    'sharpe_ratio': [1.5, 1.7, 1.9]
})

# Save with today's date in filename
today = datetime.now().strftime('%Y%m%d')
filename = f'strategy_comparison_{today}.csv'
s3_uri = save_csv_to_s3(results, filename, folder='analysis/')
```

### Example 3: Save Backtest Results

```python
import pandas as pd
from save_to_flng_bucket import save_with_timestamp

# Your backtest results
backtest_results = pd.DataFrame({
    'date': pd.date_range('2026-01-01', periods=120, freq='D'),
    'portfolio_value': [10000 + i * 50 for i in range(120)],
    'daily_return': [0.005] * 120,
    'drawdown': [-0.01] * 120
})

# Save to backtest folder with timestamp
s3_uri = save_with_timestamp(backtest_results, 'backtest_results', folder='backtests/')
```

## Folder Structure Recommendations

Organize your data in S3 with a clear folder structure:

```
flng-trading-data/
├── raw/                    # Raw data files
├── signals/                # Trading signals
├── analysis/               # Analysis results
├── backtests/              # Backtest results
├── indicators/             # Technical indicators (Keltner, Bollinger, etc.)
└── reports/                # Summary reports
```

## Requirements

- Python 3.x
- pandas
- boto3
- AWS credentials configured (via AWS CLI or environment variables)

## AWS Configuration

Ensure your AWS credentials are configured:

```bash
# Option 1: Configure AWS CLI
aws configure

# Option 2: Set environment variables
set AWS_ACCESS_KEY_ID=your_access_key
set AWS_SECRET_ACCESS_KEY=your_secret_key
set AWS_DEFAULT_REGION=us-east-2
```

## Testing

Run the example script to test your connection:

```bash
python save_to_flng_bucket.py
```

This will save a sample DataFrame to the `test/` folder in your S3 bucket.
