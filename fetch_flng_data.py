"""
Fetch FLNG Stock Data and Calculate Technical Indicators
- Fetches 5 days of minute-level data from Yahoo Finance
- Calculates Keltner Channels and Bollinger Bands
- Saves data to S3
- Creates visualization charts
"""

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import pytz
from save_to_flng_bucket import save_with_timestamp, save_csv_to_s3

# Configuration
TICKER = 'FLNG'
DAYS_BACK = 5


def fetch_flng_data(days=5, interval='5m'):
    """
    Fetch FLNG stock data from Yahoo Finance
    
    Parameters:
    -----------
    days : int
        Number of days of historical data
    interval : str
        Data interval ('1m', '5m', '15m', '30m', '1h', '1d')
        Note: Yahoo limits minute data to 7 days max
    
    Returns:
    --------
    pd.DataFrame : Stock data with OHLCV columns
    """
    print(f"Fetching {days} days of {interval} data for {TICKER}...")
    
    # Create ticker object
    stock = yf.Ticker(TICKER)
    
    # Calculate date range
    end_date = datetime.now(pytz.timezone('US/Eastern'))
    start_date = end_date - timedelta(days=days)
    
    # Fetch data
    df = stock.history(start=start_date, end=end_date, interval=interval)
    
    if df.empty:
        raise ValueError(f"No data retrieved for {TICKER}")
    
    # Standardize column names
    df.columns = df.columns.str.title()
    
    # Remove timezone for easier handling
    df.index = df.index.tz_localize(None)
    
    print(f"[OK] Fetched {len(df)} data points")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    return df


def filter_trading_hours(df):
    """
    Filter data to only include regular trading hours (9:30 AM - 4:00 PM EST)
    
    Parameters:
    -----------
    df : pd.DataFrame
        Stock data with datetime index
    
    Returns:
    --------
    pd.DataFrame : Filtered data with only trading hours
    """
    # Get time component from index
    times = df.index.time
    
    # Define trading hours (9:30 AM to 4:00 PM)
    from datetime import time
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    # Filter for trading hours only
    mask = (times >= market_open) & (times <= market_close)
    df_filtered = df[mask].copy()
    
    print(f"[OK] Filtered to trading hours only (9:30 AM - 4:00 PM EST)")
    print(f"  Data points before: {len(df)}")
    print(f"  Data points after: {len(df_filtered)}")
    
    return df_filtered


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """
    Calculate Bollinger Bands
    
    Parameters:
    -----------
    df : pd.DataFrame
        Stock data with 'Close' column
    period : int
        Moving average period (default: 20)
    std_dev : int
        Number of standard deviations (default: 2)
    
    Returns:
    --------
    pd.DataFrame : Original df with BB columns added
    """
    df = df.copy()
    
    # Middle band (SMA)
    df['BB_Middle'] = df['Close'].rolling(window=period).mean()
    
    # Standard deviation
    rolling_std = df['Close'].rolling(window=period).std()
    
    # Upper and lower bands
    df['BB_Upper'] = df['BB_Middle'] + (rolling_std * std_dev)
    df['BB_Lower'] = df['BB_Middle'] - (rolling_std * std_dev)
    
    # Bandwidth (volatility indicator)
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
    
    print(f"[OK] Calculated Bollinger Bands (period={period}, std={std_dev})")
    
    return df


def calculate_keltner_channels(df, ema_period=20, atr_period=10, multiplier=2):
    """
    Calculate Keltner Channels
    
    Parameters:
    -----------
    df : pd.DataFrame
        Stock data with OHLC columns
    ema_period : int
        EMA period for middle line (default: 20)
    atr_period : int
        ATR period (default: 10)
    multiplier : float
        ATR multiplier for bands (default: 2)
    
    Returns:
    --------
    pd.DataFrame : Original df with Keltner Channel columns added
    """
    df = df.copy()
    
    # Middle line (EMA)
    df['KC_Middle'] = df['Close'].ewm(span=ema_period, adjust=False).mean()
    
    # Calculate True Range
    df['TR'] = df[['High', 'Low', 'Close']].apply(
        lambda x: max(x['High'] - x['Low'], 
                     abs(x['High'] - x['Close']), 
                     abs(x['Low'] - x['Close'])),
        axis=1
    )
    
    # Average True Range (ATR)
    df['ATR'] = df['TR'].rolling(window=atr_period).mean()
    
    # Upper and lower channels
    df['KC_Upper'] = df['KC_Middle'] + (df['ATR'] * multiplier)
    df['KC_Lower'] = df['KC_Middle'] - (df['ATR'] * multiplier)
    
    # Channel width
    df['KC_Width'] = df['KC_Upper'] - df['KC_Lower']
    
    print(f"[OK] Calculated Keltner Channels (EMA={ema_period}, ATR={atr_period}, mult={multiplier})")
    
    return df


def create_chart(df, save_path='FLNG_Technical_Indicators.png'):
    """
    Create chart showing price with Bollinger Bands and Keltner Channels
    
    Parameters:
    -----------
    df : pd.DataFrame
        Stock data with indicator columns
    save_path : str
        Path to save the chart
    """
    print(f"\nGenerating chart...")
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), 
                                     gridspec_kw={'height_ratios': [3, 1]})
    
    # Use integer indices to eliminate gaps from non-trading periods
    x_indices = range(len(df))
    
    # Main price chart - plot using indices
    ax1.plot(x_indices, df['Close'].values, label='FLNG Close Price', 
             color='black', linewidth=1.5, zorder=5)
    
    # Bollinger Bands
    ax1.plot(x_indices, df['BB_Upper'].values, label='BB Upper', 
             color='blue', linestyle='--', linewidth=1, alpha=0.7)
    ax1.plot(x_indices, df['BB_Middle'].values, label='BB Middle (SMA)', 
             color='blue', linestyle=':', linewidth=1, alpha=0.7)
    ax1.plot(x_indices, df['BB_Lower'].values, label='BB Lower', 
             color='blue', linestyle='--', linewidth=1, alpha=0.7)
    ax1.fill_between(x_indices, df['BB_Upper'].values, df['BB_Lower'].values, 
                      color='blue', alpha=0.1)
    
    # Keltner Channels
    ax1.plot(x_indices, df['KC_Upper'].values, label='KC Upper', 
             color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax1.plot(x_indices, df['KC_Middle'].values, label='KC Middle (EMA)', 
             color='red', linestyle=':', linewidth=1, alpha=0.7)
    ax1.plot(x_indices, df['KC_Lower'].values, label='KC Lower', 
             color='red', linestyle='--', linewidth=1, alpha=0.7)
    ax1.fill_between(x_indices, df['KC_Upper'].values, df['KC_Lower'].values, 
                      color='red', alpha=0.1)
    
    # Create custom x-tick labels showing date/time at key points
    # Show labels at start of each day and some intermediate points
    tick_positions = []
    tick_labels = []
    current_date = None
    
    for i, timestamp in enumerate(df.index):
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H:%M')
        
        # Add tick at start of each new day
        if date_str != current_date:
            tick_positions.append(i)
            tick_labels.append(f"{timestamp.strftime('%m/%d')}\n{time_str}")
            current_date = date_str
        # Add tick at noon (12:00) for reference
        elif time_str == '12:00':
            tick_positions.append(i)
            tick_labels.append(time_str)
    
    # Add final timestamp
    if len(df) - 1 not in tick_positions:
        tick_positions.append(len(df) - 1)
        tick_labels.append(df.index[-1].strftime('%m/%d\n%H:%M'))
    
    # Formatting main chart
    ax1.set_title(f'FLNG - Bollinger Bands & Keltner Channels (Trading Hours Only)\n'
                  f'{df.index[0].strftime("%Y-%m-%d")} to {df.index[-1].strftime("%Y-%m-%d")} | 9:30 AM - 4:00 PM EST',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Price ($)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels(tick_labels, fontsize=9)
    ax1.set_xlim(0, len(df) - 1)
    
    # Volume subplot - use indices
    colors = ['green' if df['Close'].iloc[i] >= df['Open'].iloc[i] 
              else 'red' for i in range(len(df))]
    ax2.bar(x_indices, df['Volume'].values, color=colors, alpha=0.5, width=0.8)
    ax2.set_ylabel('Volume', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date & Time', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, fontsize=9)
    ax2.set_xlim(0, len(df) - 1)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"[OK] Chart saved: {save_path}")
    
    return fig


def generate_trading_signals(df):
    """
    Generate trading signals based on Bollinger Bands and Keltner Channels
    
    Parameters:
    -----------
    df : pd.DataFrame
        Stock data with indicator columns
    
    Returns:
    --------
    pd.DataFrame : DataFrame with signal columns added
    """
    df = df.copy()
    
    # Bollinger Band signals
    # Buy when price touches lower BB
    df['BB_Buy_Signal'] = (df['Close'] <= df['BB_Lower']).astype(int)
    # Sell when price touches upper BB
    df['BB_Sell_Signal'] = (df['Close'] >= df['BB_Upper']).astype(int)
    
    # Keltner Channel signals
    # Buy when price breaks below lower KC (potential reversal)
    df['KC_Buy_Signal'] = (df['Close'] <= df['KC_Lower']).astype(int)
    # Sell when price breaks above upper KC
    df['KC_Sell_Signal'] = (df['Close'] >= df['KC_Upper']).astype(int)
    
    # Squeeze indicator (Bollinger Bands inside Keltner Channels)
    df['Squeeze'] = ((df['BB_Upper'] < df['KC_Upper']) & 
                     (df['BB_Lower'] > df['KC_Lower'])).astype(int)
    
    # Combined signal
    df['Signal'] = 'HOLD'
    df.loc[df['BB_Buy_Signal'] == 1, 'Signal'] = 'BUY'
    df.loc[df['BB_Sell_Signal'] == 1, 'Signal'] = 'SELL'
    
    print(f"[OK] Generated trading signals")
    print(f"  Buy signals: {df['BB_Buy_Signal'].sum()}")
    print(f"  Sell signals: {df['BB_Sell_Signal'].sum()}")
    print(f"  Squeeze periods: {df['Squeeze'].sum()}")
    
    return df


def aggregate_to_daily(df):
    """
    Aggregate intraday data to daily OHLC format
    
    Parameters:
    -----------
    df : pd.DataFrame
        Intraday stock data with datetime index
    
    Returns:
    --------
    pd.DataFrame : Daily OHLC data
    """
    # Extract date from datetime index
    df['Date'] = df.index.date
    
    # Aggregate by date
    daily_df = df.groupby('Date').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    
    # Convert Date index to datetime
    daily_df.index = pd.to_datetime(daily_df.index)
    
    print(f"[OK] Aggregated to daily data: {len(daily_df)} trading days")
    
    return daily_df


def create_daily_boxplot_chart(df_intraday, save_path='FLNG_Daily_BoxPlot.png'):
    """
    Create daily box-and-whisker plot with Bollinger Bands and Keltner Channels
    
    Parameters:
    -----------
    df_intraday : pd.DataFrame
        Intraday stock data with datetime index
    save_path : str
        Path to save the chart
    """
    print(f"\nGenerating daily box plot chart...")
    
    # Aggregate to daily data
    df_daily = aggregate_to_daily(df_intraday.copy())
    
    # Calculate indicators on daily data
    df_daily = calculate_bollinger_bands(df_daily, period=5, std_dev=2)
    df_daily = calculate_keltner_channels(df_daily, ema_period=5, atr_period=5, multiplier=2)
    
    # Prepare data for box plots
    df_intraday_copy = df_intraday.copy()
    df_intraday_copy['Date'] = df_intraday_copy.index.date
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), 
                                     gridspec_kw={'height_ratios': [3, 1]})
    
    # Get unique dates
    unique_dates = sorted(df_intraday_copy['Date'].unique())
    
    # Prepare box plot data
    box_data = []
    box_positions = []
    for i, date in enumerate(unique_dates):
        day_data = df_intraday_copy[df_intraday_copy['Date'] == date]['Close']
        box_data.append(day_data.values)
        box_positions.append(i)
    
    # Create box plots
    bp = ax1.boxplot(box_data, positions=box_positions, widths=0.6,
                     patch_artist=True,
                     boxprops=dict(facecolor='lightblue', alpha=0.7),
                     medianprops=dict(color='darkblue', linewidth=2),
                     whiskerprops=dict(color='gray', linewidth=1.5),
                     capprops=dict(color='gray', linewidth=1.5),
                     flierprops=dict(marker='o', markerfacecolor='red', 
                                   markersize=5, alpha=0.5))
    
    # Overlay Bollinger Bands
    x_positions = range(len(df_daily))
    ax1.plot(x_positions, df_daily['BB_Upper'].values, 
             label='BB Upper', color='blue', linestyle='--', linewidth=2)
    ax1.plot(x_positions, df_daily['BB_Middle'].values, 
             label='BB Middle (SMA)', color='blue', linestyle=':', linewidth=2)
    ax1.plot(x_positions, df_daily['BB_Lower'].values, 
             label='BB Lower', color='blue', linestyle='--', linewidth=2)
    ax1.fill_between(x_positions, df_daily['BB_Upper'].values, 
                      df_daily['BB_Lower'].values, color='blue', alpha=0.1)
    
    # Overlay Keltner Channels
    ax1.plot(x_positions, df_daily['KC_Upper'].values, 
             label='KC Upper', color='red', linestyle='--', linewidth=2)
    ax1.plot(x_positions, df_daily['KC_Middle'].values, 
             label='KC Middle (EMA)', color='red', linestyle=':', linewidth=2)
    ax1.plot(x_positions, df_daily['KC_Lower'].values, 
             label='KC Lower', color='red', linestyle='--', linewidth=2)
    ax1.fill_between(x_positions, df_daily['KC_Upper'].values, 
                      df_daily['KC_Lower'].values, color='red', alpha=0.1)
    
    # Plot daily close prices as a line
    ax1.plot(x_positions, df_daily['Close'].values, 
             label='Daily Close', color='black', linewidth=2, marker='o', markersize=6)
    
    # Formatting
    ax1.set_title(f'FLNG - Daily Box Plot with Bollinger Bands & Keltner Channels\n'
                  f'{unique_dates[0]} to {unique_dates[-1]}',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Price ($)', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Set x-axis labels (dates)
    date_labels = [pd.to_datetime(d).strftime('%m/%d\n%a') for d in unique_dates]
    ax1.set_xticks(box_positions)
    ax1.set_xticklabels(date_labels, fontsize=10)
    ax1.set_xlim(-0.5, len(unique_dates) - 0.5)
    
    # Volume subplot
    colors = ['green' if df_daily['Close'].iloc[i] >= df_daily['Open'].iloc[i] 
              else 'red' for i in range(len(df_daily))]
    ax2.bar(x_positions, df_daily['Volume'].values, color=colors, alpha=0.6, width=0.8)
    ax2.set_ylabel('Volume', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Trading Day', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_xticks(box_positions)
    ax2.set_xticklabels(date_labels, fontsize=10)
    ax2.set_xlim(-0.5, len(unique_dates) - 0.5)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"[OK] Daily box plot chart saved: {save_path}")
    
    return fig, df_daily


def main():
    """
    Main execution function
    """
    print("=" * 70)
    print("FLNG TECHNICAL ANALYSIS - Keltner Channels & Bollinger Bands")
    print("=" * 70)
    
    # 1. Fetch data
    df = fetch_flng_data(days=DAYS_BACK, interval='5m')
    
    # 2. Filter to trading hours only
    df = filter_trading_hours(df)
    
    # 3. Calculate indicators
    df = calculate_bollinger_bands(df, period=20, std_dev=2)
    df = calculate_keltner_channels(df, ema_period=20, atr_period=10, multiplier=2)
    
    # 4. Generate signals
    df = generate_trading_signals(df)
    
    # 5. Save raw data to S3
    print("\n" + "=" * 70)
    print("SAVING DATA TO S3")
    print("=" * 70)
    
    # Save raw OHLCV data
    s3_uri_raw = save_with_timestamp(
        df[['Open', 'High', 'Low', 'Close', 'Volume']], 
        'flng_raw_data',
        folder='raw_data/'
    )
    
    # Save data with indicators
    s3_uri_indicators = save_with_timestamp(
        df,
        'flng_with_indicators',
        folder='indicators/'
    )
    
    # Save signals only
    signal_df = df[df['Signal'] != 'HOLD'][['Close', 'Signal', 'BB_Buy_Signal', 
                                             'BB_Sell_Signal', 'Squeeze']]
    if not signal_df.empty:
        s3_uri_signals = save_with_timestamp(
            signal_df,
            'flng_signals',
            folder='signals/'
        )
    
    # 6. Create and save charts
    print("\n" + "=" * 70)
    print("CREATING VISUALIZATIONS")
    print("=" * 70)
    
    # Intraday chart
    chart_path = 'FLNG_Technical_Indicators.png'
    create_chart(df, save_path=chart_path)
    
    # Daily box plot chart
    daily_chart_path = 'FLNG_Daily_BoxPlot.png'
    fig_daily, df_daily = create_daily_boxplot_chart(df, save_path=daily_chart_path)
    
    # 7. Display summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    
    print(f"\nPrice Statistics:")
    print(f"  Current Price: ${df['Close'].iloc[-1]:.2f}")
    print(f"  Period High: ${df['High'].max():.2f}")
    print(f"  Period Low: ${df['Low'].min():.2f}")
    print(f"  Price Change: ${df['Close'].iloc[-1] - df['Close'].iloc[0]:.2f}")
    print(f"  % Change: {((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100:.2f}%")
    
    print(f"\nCurrent Indicator Levels:")
    print(f"  BB Upper: ${df['BB_Upper'].iloc[-1]:.2f}")
    print(f"  BB Middle: ${df['BB_Middle'].iloc[-1]:.2f}")
    print(f"  BB Lower: ${df['BB_Lower'].iloc[-1]:.2f}")
    print(f"  KC Upper: ${df['KC_Upper'].iloc[-1]:.2f}")
    print(f"  KC Middle: ${df['KC_Middle'].iloc[-1]:.2f}")
    print(f"  KC Lower: ${df['KC_Lower'].iloc[-1]:.2f}")
    
    current_signal = df['Signal'].iloc[-1]
    print(f"\nCurrent Signal: {current_signal}")
    
    if df['Squeeze'].iloc[-1] == 1:
        print("  [!] SQUEEZE DETECTED - Volatility compression, potential breakout coming!")
    
    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"\nFiles saved:")
    print(f"  Intraday Chart: {chart_path}")
    print(f"  Daily Box Plot Chart: {daily_chart_path}")
    print(f"  S3 Raw Data: {s3_uri_raw}")
    print(f"  S3 Indicators: {s3_uri_indicators}")
    print(f"\nView in S3: https://us-east-2.console.aws.amazon.com/s3/buckets/flng-trading-data?region=us-east-2&tab=objects")
    
    return df


if __name__ == "__main__":
    df = main()
