import React, { useEffect, useRef } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

/**
 * Chart Component
 * 
 * Reusable chart wrapper using Chart.js with:
 * - Multiple chart types (line, bar, pie)
 * - Responsive design
 * - Loading state
 * - Error handling
 * - Customizable options
 */
const Chart = ({
  type = 'line',
  data,
  options = {},
  title,
  height = 300,
  loading = false,
  error = null,
  ...props
}) => {
  const chartRef = useRef(null);

  // Default options
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: !!title,
        text: title,
      },
    },
    ...options,
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, []);

  // Render chart based on type
  const renderChart = () => {
    switch (type) {
      case 'line':
        return <Line ref={chartRef} data={data} options={defaultOptions} />;
      case 'bar':
        return <Bar ref={chartRef} data={data} options={defaultOptions} />;
      case 'pie':
        return <Pie ref={chartRef} data={data} options={defaultOptions} />;
      default:
        return <Line ref={chartRef} data={data} options={defaultOptions} />;
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">Loading chart...</Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="error">{error}</Typography>
      </Paper>
    );
  }

  if (!data || !data.datasets || data.datasets.length === 0) {
    return (
      <Paper sx={{ p: 3, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data available</Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }} {...props}>
      <Box sx={{ height }}>
        {renderChart()}
      </Box>
    </Paper>
  );
};

export default Chart;