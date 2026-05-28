import React, { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

/**
 * HistoricalDataUpload Component
 * Handles file upload with drag-and-drop for CSV/Excel/Parquet files
 * Features: validation, preview, batch upload, progress tracking
 */
const HistoricalDataUpload = ({
  onUploadComplete,
  acceptedFormats = ['.csv', '.xlsx', '.xls', '.parquet'],
  maxFiles = 10,
  maxFileSize = 50 * 1024 * 1024, // 50MB default
}) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [previewData, setPreviewData] = useState(null);
  const [errors, setErrors] = useState([]);

  // Handle file drop
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const newErrors = rejectedFiles.map(({ file, errors }) => ({
        fileName: file.name,
        message: errors.map(e => e.message).join(', '),
      }));
      setErrors(prev => [...prev, ...newErrors]);
    }

    // Process accepted files
    if (acceptedFiles.length > 0) {
      const newFiles = acceptedFiles.map(file => ({
        file,
        id: `${file.name}-${Date.now()}`,
        status: 'pending',
        preview: null,
      }));
      setFiles(prev => [...prev, ...newFiles]);
      
      // Generate preview for first file
      if (newFiles.length > 0 && !previewData) {
        generatePreview(newFiles[0].file);
      }
    }
  }, [previewData]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFormats.reduce((acc, format) => {
      const mimeTypes = {
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.parquet': 'application/octet-stream',
      };
      acc[mimeTypes[format]] = [format];
      return acc;
    }, {}),
    maxFiles,
    maxSize: maxFileSize,
  });

  // Generate preview of first 10 rows
  const generatePreview = async (file) => {
    try {
      const text = await file.text();
      const lines = text.split('\n').slice(0, 11); // Header + 10 rows
      const rows = lines.map(line => line.split(','));
      
      setPreviewData({
        fileName: file.name,
        headers: rows[0],
        rows: rows.slice(1, 11),
      });
    } catch (error) {
      console.error('Preview generation failed:', error);
    }
  };

  // Remove file from list
  const removeFile = (fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
    setErrors(prev => prev.filter(e => e.fileId !== fileId));
  };

  // Upload files
  const handleUpload = async () => {
    setUploading(true);
    const results = [];

    for (const fileItem of files) {
      if (fileItem.status === 'completed') continue;

      try {
        // Simulate upload progress
        setUploadProgress(prev => ({ ...prev, [fileItem.id]: 0 }));

        const formData = new FormData();
        formData.append('file', fileItem.file);

        // Simulated upload with progress
        for (let progress = 0; progress <= 100; progress += 20) {
          await new Promise(resolve => setTimeout(resolve, 200));
          setUploadProgress(prev => ({ ...prev, [fileItem.id]: progress }));
        }

        // Update file status
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'completed' } : f
        ));

        results.push({
          fileName: fileItem.file.name,
          success: true,
          fileId: fileItem.id,
        });
      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'error' } : f
        ));
        
        results.push({
          fileName: fileItem.file.name,
          success: false,
          error: error.message,
          fileId: fileItem.id,
        });
      }
    }

    setUploading(false);
    
    if (onUploadComplete) {
      onUploadComplete(results);
    }
  };

  // Clear all errors
  const clearErrors = () => {
    setErrors([]);
  };

  return (
    <Box>
      {/* Error Display */}
      {errors.length > 0 && (
        <Alert 
          severity="error" 
          onClose={clearErrors}
          sx={{ mb: 2 }}
        >
          <Typography variant="subtitle2" gutterBottom>
            Upload Errors:
          </Typography>
          {errors.map((error, idx) => (
            <Typography key={idx} variant="body2">
              {error.fileName}: {error.message}
            </Typography>
          ))}
        </Alert>
      )}

      {/* Drag and Drop Area */}
      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          bgcolor: isDragActive ? 'action.hover' : 'background.paper',
          cursor: 'pointer',
          textAlign: 'center',
          mb: 3,
          transition: 'all 0.3s',
          '&:hover': {
            borderColor: 'primary.main',
            bgcolor: 'action.hover',
          },
        }}
      >
        <input {...getInputProps()} />
        <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          or click to select files
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Accepted formats: {acceptedFormats.join(', ')} (Max {maxFiles} files, {(maxFileSize / 1024 / 1024).toFixed(0)}MB each)
        </Typography>
      </Paper>

      {/* File List */}
      {files.length > 0 && (
        <Paper sx={{ mb: 3 }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">
              Uploaded Files ({files.length})
            </Typography>
          </Box>
          <List>
            {files.map((fileItem) => (
              <ListItem key={fileItem.id}>
                <ListItemText
                  primary={fileItem.file.name}
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                      <Typography variant="caption">
                        {(fileItem.file.size / 1024).toFixed(2)} KB
                      </Typography>
                      <Chip
                        size="small"
                        label={fileItem.status}
                        color={
                          fileItem.status === 'completed' ? 'success' :
                          fileItem.status === 'error' ? 'error' : 'default'
                        }
                        icon={
                          fileItem.status === 'completed' ? <CheckIcon /> :
                          fileItem.status === 'error' ? <ErrorIcon /> : null
                        }
                      />
                      {uploadProgress[fileItem.id] !== undefined && 
                       fileItem.status === 'pending' && (
                        <Box sx={{ width: 100 }}>
                          <LinearProgress 
                            variant="determinate" 
                            value={uploadProgress[fileItem.id]} 
                          />
                        </Box>
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => removeFile(fileItem.id)}
                    disabled={uploading}
                  >
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Preview Table */}
      {previewData && (
        <Paper sx={{ mb: 3 }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">
              Preview: {previewData.fileName} (First 10 rows)
            </Typography>
          </Box>
          <TableContainer sx={{ maxHeight: 400 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  {previewData.headers.map((header, idx) => (
                    <TableCell key={idx}>
                      <strong>{header}</strong>
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {previewData.rows.map((row, rowIdx) => (
                  <TableRow key={rowIdx}>
                    {row.map((cell, cellIdx) => (
                      <TableCell key={cellIdx}>{cell}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Upload Button */}
      {files.length > 0 && (
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          <Button
            variant="outlined"
            onClick={() => {
              setFiles([]);
              setPreviewData(null);
              setUploadProgress({});
            }}
            disabled={uploading}
          >
            Clear All
          </Button>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={handleUpload}
            disabled={uploading || files.every(f => f.status === 'completed')}
          >
            {uploading ? 'Uploading...' : 'Upload Files'}
          </Button>
        </Box>
      )}
    </Box>
  );
};

HistoricalDataUpload.propTypes = {
  onUploadComplete: PropTypes.func,
  acceptedFormats: PropTypes.arrayOf(PropTypes.string),
  maxFiles: PropTypes.number,
  maxFileSize: PropTypes.number,
};

export default HistoricalDataUpload;