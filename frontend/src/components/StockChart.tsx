import React, { useEffect, useState } from 'react';
import ReactApexChart from 'react-apexcharts';
import { getChartData } from '../api';

interface StockChartProps {
  data?: any[];
  ticker?: string;
  color?: string;
  height?: number;
  compact?: boolean;
}

type ChartMode = 'line' | 'candlestick';
type ChartRange = '1mo' | '45d' | '3mo' | '6mo' | '1y';

const RANGE_LABELS: Record<ChartRange, string> = {
  '1mo': '30D',
  '45d': '45D',
  '3mo': '3M',
  '6mo': '6M',
  '1y': '1Y',
};

const StockChart: React.FC<StockChartProps> = ({
  data: initialData,
  ticker,
  color = '#15c47e',
  height = 320,
  compact = false,
}) => {
  const [data, setData] = useState<any[]>(initialData || []);
  const [loading, setLoading] = useState(false);
  const [chartMode, setChartMode] = useState<ChartMode>('candlestick');
  const [chartRange, setChartRange] = useState<ChartRange>('1mo');

  useEffect(() => {
    if (initialData && initialData.length > 0) {
      setData(initialData);
    }
  }, [initialData]);

  useEffect(() => {
    if (ticker) {
      fetchData(ticker, chartRange);
    }
  }, [ticker, chartRange]);

  async function fetchData(symbol: string, range: ChartRange) {
    setLoading(true);
    try {
      const res = await getChartData(symbol, range);
      setData(res || []);
    } catch (e) {
      console.error('Failed to fetch chart data:', e);
      setData([]);
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        <div className="loader-dot"></div>
        <span style={{ marginLeft: '10px', fontSize: '0.75rem', letterSpacing: '1px' }}>SYNCING MARKET DATA...</span>
      </div>
    );
  }

  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(255,255,255,0.02)',
          borderRadius: '18px',
          border: '1px dashed rgba(255,255,255,0.08)',
        }}
      >
        <div className="empty-chart-label">
          <span style={{ fontSize: '2rem', opacity: 0.5 }}>📈</span>
          <span>NO PRICE FEED AVAILABLE FOR {ticker}</span>
          <p style={{ fontSize: '0.7rem', fontWeight: 400 }}>Waiting for a valid market snapshot.</p>
        </div>
      </div>
    );
  }

  const processedData = data
    .map((point) => ({
      timestamp: point.x,
      open: point.y[0],
      high: point.y[1],
      low: point.y[2],
      close: point.y[3],
    }))
    .sort((a, b) => a.timestamp - b.timestamp);

  const latest = processedData[processedData.length - 1];
  const previous = processedData[Math.max(processedData.length - 2, 0)];
  const first = processedData[0];
  const absoluteChange = latest.close - previous.close;
  const percentChange = previous.close ? (absoluteChange / previous.close) * 100 : 0;
  const trendChange = latest.close - first.open;

  const candleSeries = [
    {
      name: 'OHLC',
      data: processedData.map((point) => ({
        x: point.timestamp,
        y: [point.open, point.high, point.low, point.close],
      })),
    },
  ];

  const lineSeries = [
    {
      name: 'Price',
      data: processedData.map((point) => ({
        x: point.timestamp,
        y: point.close,
      })),
    },
  ];

  const baseOptions: any = {
    chart: {
      id: compact ? 'portfolio-mini-chart' : 'finsi-stock-chart',
      background: 'transparent',
      toolbar: { show: false },
      zoom: { enabled: false },
      foreColor: '#7a8ca8',
      fontFamily: 'var(--font-mono)',
      animations: { enabled: true, easing: 'easeout', speed: 450 },
    },
    theme: { mode: 'dark' },
    dataLabels: { enabled: false },
    grid: {
      borderColor: 'rgba(255,255,255,0.06)',
      strokeDashArray: 5,
      padding: { left: 6, right: 8, top: 0, bottom: 12 },
    },
    xaxis: {
      type: 'datetime',
      tickAmount: compact ? 3 : 6,
      axisBorder: { show: false },
      axisTicks: { show: false },
      crosshairs: {
        show: !compact,
        stroke: {
          color: 'rgba(255,255,255,0.08)',
          width: 1,
          dashArray: 4,
        },
      },
      labels: {
        show: !compact,
        datetimeUTC: false,
        offsetY: 4,
        style: {
          colors: '#70819b',
          fontSize: '10px',
          fontWeight: 600,
        },
        formatter: (_value: string, timestamp: number) =>
          new Date(timestamp).toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
          }),
      },
    },
    yaxis: {
      show: !compact,
      opposite: true,
      tickAmount: 5,
      decimalsInFloat: 2,
      labels: {
        style: {
          colors: '#70819b',
          fontSize: '10px',
          fontWeight: 600,
        },
        formatter: (value: number) => `₹${Math.round(value).toLocaleString('en-IN')}`,
      },
    },
    tooltip: {
      theme: 'dark',
      shared: true,
      intersect: false,
      x: { format: 'dd MMM yyyy' },
      style: { fontSize: '11px' },
    },
    legend: { show: false },
    states: {
      hover: { filter: { type: 'none' } },
      active: { filter: { type: 'none' } },
    },
  };

  const lineOptions: any = {
    ...baseOptions,
    stroke: {
      width: compact ? 2 : 2.8,
      curve: 'smooth',
      colors: [color],
    },
    markers: {
      size: 0,
      hover: { size: compact ? 0 : 5 },
    },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: compact ? 0.24 : 0.4,
        opacityTo: 0.03,
        stops: [0, 100],
        colorStops: [
          { offset: 0, color, opacity: compact ? 0.24 : 0.4 },
          { offset: 100, color, opacity: 0.03 },
        ],
      },
    },
  };

  const candleOptions: any = {
    ...baseOptions,
    stroke: { width: 1 },
    plotOptions: {
      candlestick: {
        colors: {
          upward: color,
          downward: '#ef5350',
        },
        wick: {
          useFillColor: true,
        },
      },
    },
    annotations: compact
      ? undefined
      : {
          yaxis: [
            {
              y: latest.close,
              borderColor: color,
              strokeDashArray: 3,
              label: {
                text: `₹${latest.close.toFixed(2)}`,
                borderColor: color,
                style: {
                  background: color,
                  color: '#071017',
                  fontSize: '10px',
                  fontWeight: 800,
                },
              },
            },
          ],
        },
  };

  if (compact) {
    return (
      <div className="portfolio-mini-chart-shell">
        <div className="portfolio-mini-price">
          <strong>₹{latest.close.toFixed(2)}</strong>
          <span className={absoluteChange >= 0 ? 'positive' : 'negative'}>
            {absoluteChange >= 0 ? '+' : ''}
            {absoluteChange.toFixed(2)} ({percentChange.toFixed(2)}%)
          </span>
        </div>
        <div className="portfolio-mini-controls">
          <div className="stock-chart-mode-switch compact">
            <button className={`btn-toggle ${chartMode === 'line' ? 'active' : ''}`} onClick={() => setChartMode('line')} type="button">
              Line
            </button>
            <button className={`btn-toggle ${chartMode === 'candlestick' ? 'active' : ''}`} onClick={() => setChartMode('candlestick')} type="button">
              Candle
            </button>
          </div>
          <div className="stock-range-switch compact">
            {(Object.keys(RANGE_LABELS) as ChartRange[]).slice(0, 3).map((range) => (
              <button
                key={range}
                className={`range-toggle ${chartRange === range ? 'active' : ''}`}
                onClick={() => setChartRange(range)}
                type="button"
              >
                {RANGE_LABELS[range]}
              </button>
            ))}
          </div>
        </div>
        <div className="main-price-pane broker-chart-pane compact" style={{ height }}>
          <ReactApexChart
            options={chartMode === 'candlestick' ? candleOptions : lineOptions}
            series={chartMode === 'candlestick' ? candleSeries : lineSeries}
            type={chartMode === 'candlestick' ? 'candlestick' : 'area'}
            height={height}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="stock-chart-shell">
      <div className="stock-chart-toolbar">
        <div className="stock-chart-pricegroup">
          <div className="badge badge-accent">NSE PRICE ACTION</div>
          <div className="stock-chart-price-line">
            <strong>₹{latest.close.toFixed(2)}</strong>
            <span className={absoluteChange >= 0 ? 'positive' : 'negative'}>
              {absoluteChange >= 0 ? '+' : ''}
              {absoluteChange.toFixed(2)} ({absoluteChange >= 0 ? '+' : ''}
              {percentChange.toFixed(2)}%)
            </span>
          </div>
        </div>

        <div className="stock-chart-controls">
          <div className="stock-range-switch">
            {(Object.keys(RANGE_LABELS) as ChartRange[]).map((range) => (
              <button
                key={range}
                className={`range-toggle ${chartRange === range ? 'active' : ''}`}
                onClick={() => setChartRange(range)}
                type="button"
              >
                {RANGE_LABELS[range]}
              </button>
            ))}
          </div>
          <div className="stock-chart-mode-switch">
            <button className={`btn-toggle ${chartMode === 'line' ? 'active' : ''}`} onClick={() => setChartMode('line')} type="button">
              Line
            </button>
            <button className={`btn-toggle ${chartMode === 'candlestick' ? 'active' : ''}`} onClick={() => setChartMode('candlestick')} type="button">
              Candle
            </button>
          </div>
        </div>
      </div>

      <div className="stock-chart-metrics">
        <div className="stock-chart-metric">
          <span>Open</span>
          <strong>₹{latest.open.toFixed(2)}</strong>
        </div>
        <div className="stock-chart-metric">
          <span>High</span>
          <strong>₹{latest.high.toFixed(2)}</strong>
        </div>
        <div className="stock-chart-metric">
          <span>Low</span>
          <strong>₹{latest.low.toFixed(2)}</strong>
        </div>
        <div className="stock-chart-metric">
          <span>Close</span>
          <strong>₹{latest.close.toFixed(2)}</strong>
        </div>
        <div className="stock-chart-metric">
          <span>Trend</span>
          <strong className={trendChange >= 0 ? 'positive' : 'negative'}>
            {trendChange >= 0 ? 'Bullish' : 'Bearish'}
          </strong>
        </div>
      </div>

      <div className="main-price-pane broker-chart-pane" style={{ height }}>
        <ReactApexChart
          options={chartMode === 'candlestick' ? candleOptions : lineOptions}
          series={chartMode === 'candlestick' ? candleSeries : lineSeries}
          type={chartMode === 'candlestick' ? 'candlestick' : 'area'}
          height={height}
        />
      </div>
    </div>
  );
};

export default StockChart;
