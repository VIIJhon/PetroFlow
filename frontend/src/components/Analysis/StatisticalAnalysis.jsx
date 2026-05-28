import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Tabs,
  Tab,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendUpIcon,
  TrendingDown as TrendDownIcon,
  TrendingFlat as TrendFlatIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * StatisticalAnalysis Component
 * Comprehensive statistical analysis with descriptive stats, distributions, correlations
 * Features: summary tables, histograms, correlation matrix, trend analysis
 */
const StatisticalAnalysis = ({
  data,
  selectedVariables = [],
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedVariable, setSelectedVariable] = useState(
    selectedVariables.length > 0 ? selectedVariables[0] : ''
  );

  // Calculate descriptive statistics
  const descriptiveStats = useMemo(() => {
    if (!data || !selectedVariables.length) return {};

    const stats = {};
    
    selectedVariables.forEach(variable => {
      const values = data[variable]?.filter(v => !isNaN(v) && v !== null) || [];
      
      if (values.length > 0) {
        // Sort values for percentile calculations
        const sorted = [...values].sort((a, b) => a - b);
        const n = values.length;
        
        // Basic statistics
        const sum = values.reduce((a, b) => a + b, 0);
        const mean = sum / n;
        const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / n;
        const stdDev = Math.sqrt(variance);
        
        // Percentiles
        const q1 = sorted[Math.floor(n * 0.25)];
        const median = sorted[Math.floor(n * 0.5)];
        const q3 = sorted[Math.floor(n * 0.75)];
        
        // Skewness and Kurtosis
        const skewness = values.reduce((a, b) => a + Math.pow((b - mean) / stdDev, 3), 0) / n;
        const kurtosis = values.reduce((a, b) => a + Math.pow((b - mean) / stdDev, 4), 0) / n - 3;
        
        stats[variable] = {
          count: n,
          mean,
          stdDev,
          variance,
          min: Math.min(...values),
          max: Math.max(...values),
          range: Math.max(...values) - Math.min(...values),
          q1,
          median,
          q3,
          iqr: q3 - q1,
          skewness,
          kurtosis,
          coefficientOfVariation: (stdDev / mean) * 100,
        };
      }
    });

    return stats;
  }, [data, selectedVariables]);

  // Calculate correlation matrix
  const correlationMatrix = useMemo(() => {
    if (!data || selectedVariables.length < 2) return null;

    const matrix = {};
    
    selectedVariables.forEach(var1 => {
      matrix[var1] = {};
      
      selectedVariables.forEach(var2 => {
        const values1 = data[var1]?.filter(v => !isNaN(v)) || [];
        const values2 = data[var2]?.filter(v => !isNaN(v)) || [];
        
        if (values1.length > 0 && values2.length > 0) {
          const n = Math.min(values1.length, values2.length);
          const mean1 = values1.slice(0, n).reduce((a, b) => a + b, 0) / n;
          const mean2 = values2.slice(0, n).reduce((a, b) => a + b, 0) / n;
          
          let numerator = 0;
          let denom1 = 0;
          let denom2 = 0;
          
          for (let i = 0; i < n; i++) {
            const diff1 = values1[i] - mean1;
            const diff2 = values2[i] - mean2;
            numerator += diff1 * diff2;
            denom1 += diff1 * diff1;
            denom2 += diff2 * diff2;
          }
          
          const correlation = numerator / Math.sqrt(denom1 * denom2);
          matrix[var1][var2] = isNaN(correlation) ? 0 : correlation;
        } else {
          matrix[var1][var2] = 0;
        }
      });
    });

    return matrix;
  }, [data, selectedVariables]);

  // Calculate trend analysis
  const trendAnalysis = useMemo(() => {
    if (!data || !selectedVariables.length) return {};

    const trends = {};
    
    selectedVariables.forEach(variable => {
      const values = data[variable]?.filter(v => !isNaN(v)) || [];
      
      if (values.length > 1) {
        const n = values.length;
        const xMean = (n - 1) / 2;
        const yMean = values.reduce((a, b) => a + b, 0) / n;
        
        // Linear regression
        const slope = values.reduce((sum, y, x) => sum + (x - xMean) * (y - yMean), 0) /
                      values.reduce((sum, _, x) => sum + Math.pow(x - xMean, 2), 0);
        const intercept = yMean - slope * xMean;
        
        // R-squared
        const yPred = values.map((_, x) => slope * x + intercept);
        const ssRes = values.reduce((sum, y, i) => sum + Math.pow(y - yPred[i], 2), 0);
        const ssTot = values.reduce((sum, y) => sum + Math.pow(y - yMean, 2), 0);
        const rSquared = 1 - (ssRes / ssTot);
        
        // Trend direction
        let direction = 'flat';
        if (Math.abs(slope) > 0.01) {
          direction = slope > 0 ? 'increasing' : 'decreasing';
        }
        
        trends[variable] = {
          slope,
          intercept,
          rSquared,
          direction,
          percentChange: ((values[n - 1] - values[0]) / values[0]) * 100,
        };
      }
    });

    return trends;
  }, [data, selectedVariables]);

  // Generate histogram data
  const generateHistogram = (variable) => {
    const values = data[variable]?.filter(v => !isNaN(v)) || [];
    
    return [{
      x: values,
      type: 'histogram',
      name: variable,
      marker: {
        color: 'rgba(100, 149, 237, 0.7)',
        line: {
          color: 'rgba(100, 149, 237, 1)',
          width: 1,
        },
      },
      nbinsx: 30,
    }];
  };

  // Generate correlation heatmap data
  const generateCorrelationHeatmap = () => {
    if (!correlationMatrix) return [];

    const variables = Object.keys(correlationMatrix);
    const zValues = variables.map(var1 => 
      variables.map(var2 => correlationMatrix[var1][var2])
    );

    return [{
      z: zValues,
      x: variables,
      y: variables,
      type: 'heatmap',
      colorscale: [
        [0, 'rgb(49,54,149)'],
        [0.5, 'rgb(255,255,255)'],
        [1, 'rgb(165,0,38)'],
      ],
      zmid: 0,
      zmin: -1,
      zmax: 1,
      colorbar: {
        title: 'Correlation',
        titleside: 'right',
      },
      hovertemplate: '%{y} vs %{x}<br>Correlation: %{z:.3f}<extra></extra>',
    }];
  };

  // Render trend icon
  const renderTrendIcon = (direction) => {
    switch (direction) {
      case 'increasing':
        return <TrendUpIcon color="success" />;
      case 'decreasing':
        return <TrendDownIcon color="error" />;
      default:
        return <TrendFlatIcon color="action" />;
    }
  };

  // Render descriptive statistics table
  const renderDescriptiveStats = () => (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell><strong>Variable</strong></TableCell>
            <TableCell align="right"><strong>Count</strong></TableCell>
            <TableCell align="right"><strong>Mean</strong></TableCell>
            <TableCell align="right"><strong>Std Dev</strong></TableCell>
            <TableCell align="right"><strong>Min</strong></TableCell>
            <TableCell align="right"><strong>Q1</strong></TableCell>
            <TableCell align="right"><strong>Median</strong></TableCell>
            <TableCell align="right"><strong>Q3</strong></TableCell>
            <TableCell align="right"><strong>Max</strong></TableCell>
            <TableCell align="right"><strong>CV %</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {selectedVariables.map(variable => (
            descriptiveStats[variable] && (
              <TableRow key={variable}>
                <TableCell>{variable}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].count}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].mean.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].stdDev.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].min.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].q1.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].median.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].q3.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].max.toFixed(2)}</TableCell>
                <TableCell align="right">{descriptiveStats[variable].coefficientOfVariation.toFixed(2)}</TableCell>
              </TableRow>
            )
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  // Render distribution analysis
  const renderDistribution = () => (
    <Box>
      <Box sx={{ mb: 2 }}>
        <FormControl fullWidth size="small">
          <InputLabel>Select Variable</InputLabel>
          <Select
            value={selectedVariable}
            onChange={(e) => setSelectedVariable(e.target.value)}
          >
            {selectedVariables.map(variable => (
              <MenuItem key={variable} value={variable}>
                {variable}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {selectedVariable && (
        <>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Plot
              data={generateHistogram(selectedVariable)}
              layout={{
                title: `Distribution of ${selectedVariable}`,
                xaxis: { title: 'Value' },
                yaxis: { title: 'Frequency' },
                height: 400,
                margin: { l: 60, r: 40, t: 60, b: 60 },
              }}
              config={{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
              }}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </Paper>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Shape Characteristics
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  {descriptiveStats[selectedVariable] && (
                    <Box>
                      <Typography variant="body2">
                        Skewness: <strong>{descriptiveStats[selectedVariable].skewness.toFixed(3)}</strong>
                        <Chip
                          size="small"
                          label={
                            Math.abs(descriptiveStats[selectedVariable].skewness) < 0.5 ? 'Symmetric' :
                            descriptiveStats[selectedVariable].skewness > 0 ? 'Right-skewed' : 'Left-skewed'
                          }
                          sx={{ ml: 1 }}
                        />
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Kurtosis: <strong>{descriptiveStats[selectedVariable].kurtosis.toFixed(3)}</strong>
                        <Chip
                          size="small"
                          label={
                            Math.abs(descriptiveStats[selectedVariable].kurtosis) < 0.5 ? 'Normal' :
                            descriptiveStats[selectedVariable].kurtosis > 0 ? 'Heavy-tailed' : 'Light-tailed'
                          }
                          sx={{ ml: 1 }}
                        />
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Spread Measures
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  {descriptiveStats[selectedVariable] && (
                    <Box>
                      <Typography variant="body2">
                        Range: <strong>{descriptiveStats[selectedVariable].range.toFixed(2)}</strong>
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        IQR: <strong>{descriptiveStats[selectedVariable].iqr.toFixed(2)}</strong>
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        Variance: <strong>{descriptiveStats[selectedVariable].variance.toFixed(2)}</strong>
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );

  // Render correlation matrix
  const renderCorrelation = () => (
    <Box>
      {correlationMatrix && selectedVariables.length >= 2 ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Plot
            data={generateCorrelationHeatmap()}
            layout={{
              title: 'Correlation Matrix',
              height: 500,
              margin: { l: 100, r: 100, t: 60, b: 100 },
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
            }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        </Paper>
      ) : (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            Select at least 2 variables to display correlation matrix
          </Typography>
        </Paper>
      )}
    </Box>
  );

  // Render trend analysis
  const renderTrend = () => (
    <Grid container spacing={2}>
      {selectedVariables.map(variable => (
        trendAnalysis[variable] && (
          <Grid item xs={12} md={6} lg={4} key={variable}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {renderTrendIcon(trendAnalysis[variable].direction)}
                  <Typography variant="h6" sx={{ ml: 1 }}>
                    {variable}
                  </Typography>
                </Box>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="body2" gutterBottom>
                  Direction: <Chip
                    size="small"
                    label={trendAnalysis[variable].direction}
                    color={
                      trendAnalysis[variable].direction === 'increasing' ? 'success' :
                      trendAnalysis[variable].direction === 'decreasing' ? 'error' : 'default'
                    }
                  />
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Slope: <strong>{trendAnalysis[variable].slope.toFixed(4)}</strong>
                </Typography>
                <Typography variant="body2" gutterBottom>
                  R²: <strong>{trendAnalysis[variable].rSquared.toFixed(4)}</strong>
                </Typography>
                <Typography variant="body2">
                  Change: <strong>{trendAnalysis[variable].percentChange.toFixed(2)}%</strong>
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )
      ))}
    </Grid>
  );

  return (
    <Box>
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab label="Descriptive Statistics" />
          <Tab label="Distribution" />
          <Tab label="Correlation" />
          <Tab label="Trend Analysis" />
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        {activeTab === 0 && renderDescriptiveStats()}
        {activeTab === 1 && renderDistribution()}
        {activeTab === 2 && renderCorrelation()}
        {activeTab === 3 && renderTrend()}
      </Box>
    </Box>
  );
};

StatisticalAnalysis.propTypes = {
  data: PropTypes.object.isRequired,
  selectedVariables: PropTypes.arrayOf(PropTypes.string),
};

export default StatisticalAnalysis;