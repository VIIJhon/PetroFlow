/**
 * Utility functions for form validation
 */

/**
 * Validate email address
 */
export const validateEmail = (email) => {
  if (!email) return 'Email is required';
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return 'Invalid email address';
  }
  return null;
};

/**
 * Validate password
 */
export const validatePassword = (password, minLength = 8) => {
  if (!password) return 'Password is required';
  if (password.length < minLength) {
    return `Password must be at least ${minLength} characters`;
  }
  if (!/[A-Z]/.test(password)) {
    return 'Password must contain at least one uppercase letter';
  }
  if (!/[a-z]/.test(password)) {
    return 'Password must contain at least one lowercase letter';
  }
  if (!/[0-9]/.test(password)) {
    return 'Password must contain at least one number';
  }
  return null;
};

/**
 * Validate required field
 */
export const validateRequired = (value, fieldName = 'This field') => {
  if (!value || (typeof value === 'string' && !value.trim())) {
    return `${fieldName} is required`;
  }
  return null;
};

/**
 * Validate number
 */
export const validateNumber = (value, options = {}) => {
  const { min, max, fieldName = 'Value' } = options;
  
  if (value === null || value === undefined || value === '') {
    return `${fieldName} is required`;
  }
  
  const num = Number(value);
  if (isNaN(num)) {
    return `${fieldName} must be a number`;
  }
  
  if (min !== undefined && num < min) {
    return `${fieldName} must be at least ${min}`;
  }
  
  if (max !== undefined && num > max) {
    return `${fieldName} must be at most ${max}`;
  }
  
  return null;
};

/**
 * Validate phone number
 */
export const validatePhone = (phone) => {
  if (!phone) return 'Phone number is required';
  const phoneRegex = /^[\d\s\-\(\)]+$/;
  if (!phoneRegex.test(phone)) {
    return 'Invalid phone number';
  }
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 10) {
    return 'Phone number must have at least 10 digits';
  }
  return null;
};

/**
 * Validate URL
 */
export const validateUrl = (url) => {
  if (!url) return 'URL is required';
  try {
    new URL(url);
    return null;
  } catch {
    return 'Invalid URL';
  }
};

/**
 * Validate date
 */
export const validateDate = (date, options = {}) => {
  const { min, max, fieldName = 'Date' } = options;
  
  if (!date) return `${fieldName} is required`;
  
  const d = new Date(date);
  if (isNaN(d.getTime())) {
    return `Invalid ${fieldName.toLowerCase()}`;
  }
  
  if (min) {
    const minDate = new Date(min);
    if (d < minDate) {
      return `${fieldName} must be after ${minDate.toLocaleDateString()}`;
    }
  }
  
  if (max) {
    const maxDate = new Date(max);
    if (d > maxDate) {
      return `${fieldName} must be before ${maxDate.toLocaleDateString()}`;
    }
  }
  
  return null;
};

/**
 * Validate string length
 */
export const validateLength = (value, options = {}) => {
  const { min, max, fieldName = 'Field' } = options;
  
  if (!value) return `${fieldName} is required`;
  
  const length = value.length;
  
  if (min !== undefined && length < min) {
    return `${fieldName} must be at least ${min} characters`;
  }
  
  if (max !== undefined && length > max) {
    return `${fieldName} must be at most ${max} characters`;
  }
  
  return null;
};

/**
 * Validate file
 */
export const validateFile = (file, options = {}) => {
  const { maxSize, allowedTypes, fieldName = 'File' } = options;
  
  if (!file) return `${fieldName} is required`;
  
  if (maxSize && file.size > maxSize) {
    const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(2);
    return `${fieldName} size must be less than ${maxSizeMB}MB`;
  }
  
  if (allowedTypes && allowedTypes.length > 0) {
    const fileType = file.type;
    if (!allowedTypes.includes(fileType)) {
      return `${fieldName} type must be one of: ${allowedTypes.join(', ')}`;
    }
  }
  
  return null;
};

/**
 * Validate IP address
 */
export const validateIpAddress = (ip) => {
  if (!ip) return 'IP address is required';
  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
  if (!ipRegex.test(ip)) {
    return 'Invalid IP address format';
  }
  const parts = ip.split('.');
  for (const part of parts) {
    const num = parseInt(part, 10);
    if (num < 0 || num > 255) {
      return 'Invalid IP address';
    }
  }
  return null;
};

/**
 * Validate form with multiple fields
 */
export const validateForm = (formData, validationRules) => {
  const errors = {};
  
  for (const [field, rules] of Object.entries(validationRules)) {
    const value = formData[field];
    
    for (const rule of rules) {
      const error = rule(value);
      if (error) {
        errors[field] = error;
        break; // Stop at first error for this field
      }
    }
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
};