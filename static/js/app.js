/**
 * KTP Detection Frontend Application
 * ===================================
 * 
 * JavaScript untuk aplikasi KTP Detection
 * Handles file upload, API calls, dan UI interactions
 */

class KTPDetectionApp {
    constructor() {
        this.apiBaseUrl = '/api';
        this.currentData = null;
        this.uploadedFile = null;
        
        this.initializeElements();
        this.bindEvents();
        this.initializeApp();
    }
    
    /**
     * Initialize DOM elements
     */
    initializeElements() {
        // Form elements
        this.uploadForm = document.getElementById('uploadForm');
        this.fileInput = document.getElementById('ktpFile');
        this.submitBtn = document.getElementById('submitBtn');
        
        // Preview elements
        this.previewContainer = document.getElementById('previewContainer');
        this.imagePreview = document.getElementById('imagePreview');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        
        // Loading elements
        this.loadingSection = document.getElementById('loadingSection');
        this.loadingText = document.getElementById('loadingText');
        this.progressFill = document.getElementById('progressFill');
        
        // Result elements
        this.resultSection = document.getElementById('resultSection');
        this.successResult = document.getElementById('successResult');
        this.errorResult = document.getElementById('errorResult');
        this.errorList = document.getElementById('errorList');
        
        // Face detection elements
        this.faceSection = document.getElementById('faceSection');
        this.extractedFace = document.getElementById('extractedFace');
        this.facePlaceholder = document.getElementById('facePlaceholder');
        this.faceConfidence = document.getElementById('faceConfidence');
        this.faceQuality = document.getElementById('faceQuality');
        this.downloadFace = document.getElementById('downloadFace');
        
        // Action buttons
        this.uploadAnotherBtn = document.getElementById('uploadAnotherBtn');
        this.copyDataBtn = document.getElementById('copyDataBtn');
        
        // Toast
        this.toast = document.getElementById('toast');
        
        // Database info
        this.databaseInfo = document.getElementById('databaseInfo');
        this.databaseId = document.getElementById('databaseId');
    }
    
    /**
     * Bind event listeners
     */
    bindEvents() {
        // File input change
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Form submission
        this.uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Action buttons
        this.uploadAnotherBtn.addEventListener('click', () => this.resetForm());
        this.copyDataBtn.addEventListener('click', () => this.copyDataToClipboard());
        
        // Face download button
        if (this.downloadFace) {
            this.downloadFace.addEventListener('click', () => this.downloadFaceImage());
        }
        
        // Drag and drop events
        const fileLabel = document.querySelector('.file-input-label');
        fileLabel.addEventListener('dragover', (e) => this.handleDragOver(e));
        fileLabel.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        fileLabel.addEventListener('drop', (e) => this.handleDrop(e));
    }
    
    /**
     * Initialize application
     */
    initializeApp() {
        this.showToast('Aplikasi KTP Detection siap digunakan!', 'info');
        this.checkAPIHealth();
    }
    
    /**
     * Check API health status
     */
    async checkAPIHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                console.log('✅ API health check passed');
            } else {
                console.warn('⚠️ API health check failed:', data);
                this.showToast('API tidak sepenuhnya berfungsi', 'error');
            }
        } catch (error) {
            console.error('❌ API health check error:', error);
            this.showToast('Tidak dapat terhubung ke API', 'error');
        }
    }
    
    /**
     * Handle file selection
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.processSelectedFile(file);
        }
    }
    
    /**
     * Handle drag over
     */
    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        event.currentTarget.style.borderColor = '#764ba2';
        event.currentTarget.style.background = 'rgba(118, 75, 162, 0.1)';
    }
    
    /**
     * Handle drag leave
     */
    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        event.currentTarget.style.borderColor = '#667eea';
        event.currentTarget.style.background = 'rgba(102, 126, 234, 0.05)';
    }
    
    /**
     * Handle file drop
     */
    handleDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const fileLabel = event.currentTarget;
        fileLabel.style.borderColor = '#667eea';
        fileLabel.style.background = 'rgba(102, 126, 234, 0.05)';
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            this.fileInput.files = files;
            this.processSelectedFile(file);
        }
    }
    
    /**
     * Process selected file
     */
    processSelectedFile(file) {
        // Validate file type
        if (!this.validateFileType(file)) {
            this.showToast('Format file tidak didukung. Gunakan JPG, PNG, WebP, atau BMP.', 'error');
            this.resetFileInput();
            return;
        }
        
        // Validate file size (10MB)
        if (!this.validateFileSize(file)) {
            this.showToast('File terlalu besar. Maksimal 10MB.', 'error');
            this.resetFileInput();
            return;
        }
        
        this.uploadedFile = file;
        this.showFilePreview(file);
        this.enableSubmitButton();
    }
    
    /**
     * Validate file type
     */
    validateFileType(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/bmp'];
        return allowedTypes.includes(file.type);
    }
    
    /**
     * Validate file size
     */
    validateFileSize(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        return file.size <= maxSize;
    }
    
    /**
     * Show file preview
     */
    showFilePreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            this.imagePreview.src = e.target.result;
            this.fileName.textContent = file.name;
            this.fileSize.textContent = this.formatFileSize(file.size);
            
            this.previewContainer.style.display = 'block';
            this.previewContainer.classList.add('fade-in');
        };
        reader.readAsDataURL(file);
    }
    
    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * Enable submit button
     */
    enableSubmitButton() {
        this.submitBtn.disabled = false;
        this.submitBtn.classList.add('fade-in');
    }
    
    /**
     * Handle form submission
     */
    async handleFormSubmit(event) {
        event.preventDefault();
        
        if (!this.uploadedFile) {
            this.showToast('Pilih file KTP terlebih dahulu', 'error');
            return;
        }
        
        await this.processKTPVerification();
    }
    
    /**
     * Process KTP verification
     */
    async processKTPVerification() {
        this.showLoading();
        
        try {
            // Create form data
            const formData = new FormData();
            formData.append('file', this.uploadedFile);
            
            // Simulate progress updates
            this.updateLoadingProgress();
            
            // Make API call
            const response = await fetch(`${this.apiBaseUrl}/verify-ktp`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.currentData = result;
            
            this.hideLoading();
            this.showResults(result);
            
        } catch (error) {
            console.error('KTP verification error:', error);
            this.hideLoading();
            this.showAPIError(error.message);
        }
    }
    
    /**
     * Show loading state
     */
    showLoading() {
        this.uploadForm.style.display = 'none';
        this.resultSection.style.display = 'none';
        this.loadingSection.style.display = 'block';
        this.loadingSection.classList.add('fade-in');
        
        this.updateLoadingText('Memproses gambar...');
    }
    
    /**
     * Update loading progress
     */
    updateLoadingProgress() {
        const stages = [
            { text: 'Memvalidasi gambar...', progress: 20 },
            { text: 'Menganalisis dengan AI...', progress: 40 },
            { text: 'Mengekstrak data KTP...', progress: 60 },
            { text: 'Mendeteksi foto wajah...', progress: 80 },
            { text: 'Menyimpan ke database...', progress: 90 },
            { text: 'Menyelesaikan...', progress: 100 }
        ];
        
        let currentStage = 0;
        
        const updateStage = () => {
            if (currentStage < stages.length) {
                const stage = stages[currentStage];
                this.updateLoadingText(stage.text);
                this.progressFill.style.width = `${stage.progress}%`;
                currentStage++;
                
                setTimeout(updateStage, 800);
            }
        };
        
        setTimeout(updateStage, 500);
    }
    
    /**
     * Update loading text
     */
    updateLoadingText(text) {
        this.loadingText.textContent = text;
    }
    
    /**
     * Hide loading state
     */
    hideLoading() {
        this.loadingSection.style.display = 'none';
    }
    
    /**
     * Show API error
     */
    showAPIError(errorMessage) {
        this.resultSection.style.display = 'block';
        this.successResult.style.display = 'none';
        this.errorResult.style.display = 'block';
        this.errorResult.classList.add('slide-up');
        
        // Clear and populate error list
        this.errorList.innerHTML = '';
        const errorItem = document.createElement('li');
        errorItem.textContent = errorMessage;
        this.errorList.appendChild(errorItem);
        
        this.showToast('Terjadi kesalahan saat memproses KTP', 'error');
    }
    
    /**
     * Show results
     */
    showResults(result) {
        this.resultSection.style.display = 'block';
        this.resultSection.classList.add('slide-up');
        
        if (result.is_valid_ktp) {
            this.showSuccessResult(result);
        } else {
            this.showErrorResult(result);
        }
    }
    
    /**
     * Show success result
     */
    showSuccessResult(result) {
        this.successResult.style.display = 'block';
        this.errorResult.style.display = 'none';
        
        // Update confidence score
        const confidenceScore = document.getElementById('confidenceScore');
        confidenceScore.textContent = `${Math.round(result.confidence_score * 100)}%`;
        
        // Update confidence score color based on value
        if (result.confidence_score >= 0.8) {
            confidenceScore.style.color = '#22c55e';
        } else if (result.confidence_score >= 0.6) {
            confidenceScore.style.color = '#f59e0b';
        } else {
            confidenceScore.style.color = '#ef4444';
        }
        
        // Populate KTP data
        if (result.extracted_data) {
            this.populateKTPData(result.extracted_data);
        }
        
        // Display face detection results
        this.displayFaceDetection(result.face_detection);
        
        // Show database info if saved
        if (result.database_id) {
            this.databaseInfo.style.display = 'block';
            this.databaseId.textContent = result.database_id;
            this.showToast('KTP berhasil diverifikasi dan data disimpan!', 'success');
        } else {
            this.databaseInfo.style.display = 'none';
            this.showToast('KTP berhasil diverifikasi!', 'success');
        }
        
        // Show copy button
        this.copyDataBtn.style.display = 'inline-flex';
    }
    
    /**
     * Display face detection results
     */
    displayFaceDetection(faceData) {
        if (!this.faceSection) return;
        
        // Always show face section for feedback
        this.faceSection.style.display = 'block';
        this.faceSection.classList.add('fade-in');
        
        if (faceData && faceData.found) {
            // Face detected - show image and info
            if (faceData.face_image_path && this.extractedFace) {
                this.extractedFace.src = `/${faceData.face_image_path}`;
                this.extractedFace.style.display = 'block';
                this.extractedFace.classList.add('fade-in');
                
                // Hide placeholder
                if (this.facePlaceholder) {
                    this.facePlaceholder.style.display = 'none';
                }
                
                // Show download button
                if (this.downloadFace) {
                    this.downloadFace.style.display = 'inline-flex';
                    this.downloadFace.classList.add('fade-in');
                }
            }
            
            // Update confidence
            if (this.faceConfidence) {
                this.faceConfidence.textContent = `${Math.round(faceData.confidence * 100)}%`;
            }
            
            // Update quality notes
            if (this.faceQuality) {
                this.faceQuality.textContent = faceData.quality_notes || 'Foto wajah berhasil diekstrak';
            }
            
            console.log('✅ Face detected and displayed');
            
        } else {
            // No face detected - show placeholder
            if (this.extractedFace) {
                this.extractedFace.style.display = 'none';
            }
            
            if (this.facePlaceholder) {
                this.facePlaceholder.style.display = 'flex';
            }
            
            if (this.downloadFace) {
                this.downloadFace.style.display = 'none';
            }
            
            // Update info
            if (this.faceConfidence) {
                this.faceConfidence.textContent = '--';
            }
            
            if (this.faceQuality) {
                this.faceQuality.textContent = faceData?.quality_notes || 'Foto wajah tidak ditemukan pada KTP';
            }
            
            console.log('⚠️ No face detected');
        }
    }
    
    /**
     * Download face image
     */
    async downloadFaceImage() {
        if (!this.currentData?.face_detection?.face_image_path) {
            this.showToast('Foto wajah tidak tersedia untuk didownload', 'error');
            return;
        }
        
        try {
            const imagePath = this.currentData.face_detection.face_image_path;
            const response = await fetch(`/${imagePath}`);
            
            if (!response.ok) {
                throw new Error('Gagal mengunduh foto wajah');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            
            // Create download link
            const a = document.createElement('a');
            a.href = url;
            a.download = `foto_wajah_${this.currentData.extracted_data?.nik || 'ktp'}.jpg`;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showToast('Foto wajah berhasil didownload!', 'success');
            
        } catch (error) {
            console.error('Download face image error:', error);
            this.showToast('Gagal mengunduh foto wajah', 'error');
        }
    }
    
    /**
     * Show error result
     */
    showErrorResult(result) {
        this.successResult.style.display = 'none';
        this.errorResult.style.display = 'block';
        
        // Populate error list
        this.errorList.innerHTML = '';
        if (result.validation_errors && result.validation_errors.length > 0) {
            result.validation_errors.forEach(error => {
                const errorItem = document.createElement('li');
                errorItem.textContent = error;
                this.errorList.appendChild(errorItem);
            });
        } else {
            const errorItem = document.createElement('li');
            errorItem.textContent = 'Gambar bukan KTP Indonesia yang valid';
            this.errorList.appendChild(errorItem);
        }
        
        // Hide copy button
        this.copyDataBtn.style.display = 'none';
        
        // Hide face section for invalid KTP
        if (this.faceSection) {
            this.faceSection.style.display = 'none';
        }
        
        this.showToast('KTP tidak valid atau tidak dapat diverifikasi', 'error');
    }
    
    /**
     * Populate KTP data fields
     */
    populateKTPData(data) {
        const fields = [
            'nik', 'nama', 'tempat_lahir', 'tanggal_lahir', 'jenis_kelamin',
            'alamat', 'rt_rw', 'kelurahan', 'kecamatan', 'kabupaten_kota',
            'provinsi', 'agama', 'status_perkawinan', 'pekerjaan',
            'kewarganegaraan', 'berlaku_hingga'
        ];
        
        fields.forEach(field => {
            const element = document.getElementById(`data${this.toPascalCase(field)}`);
            if (element) {
                const value = data[field];
                element.textContent = value || '-';
                
                // Add highlight animation for non-empty values
                if (value) {
                    element.parentElement.classList.add('fade-in');
                }
            }
        });
    }
    
    /**
     * Convert snake_case to PascalCase
     */
    toPascalCase(str) {
        return str.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join('');
    }
    
    /**
     * Copy data to clipboard
     */
    async copyDataToClipboard() {
        if (!this.currentData || !this.currentData.extracted_data) {
            this.showToast('Tidak ada data untuk disalin', 'error');
            return;
        }
        
        try {
            const jsonData = JSON.stringify(this.currentData.extracted_data, null, 2);
            await navigator.clipboard.writeText(jsonData);
            this.showToast('Data berhasil disalin ke clipboard!', 'success');
        } catch (error) {
            console.error('Copy to clipboard failed:', error);
            
            // Fallback for older browsers
            this.fallbackCopyToClipboard(JSON.stringify(this.currentData.extracted_data, null, 2));
        }
    }
    
    /**
     * Fallback copy to clipboard
     */
    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showToast('Data berhasil disalin ke clipboard!', 'success');
        } catch (error) {
            this.showToast('Gagal menyalin data', 'error');
        }
        
        document.body.removeChild(textArea);
    }
    
    /**
     * Reset form
     */
    resetForm() {
        // Reset form
        this.uploadForm.reset();
        this.resetFileInput();
        
        // Hide sections
        this.previewContainer.style.display = 'none';
        this.resultSection.style.display = 'none';
        this.loadingSection.style.display = 'none';
        
        // Hide face section
        if (this.faceSection) {
            this.faceSection.style.display = 'none';
        }
        
        // Show upload form
        this.uploadForm.style.display = 'block';
        
        // Disable submit button
        this.submitBtn.disabled = true;
        
        // Clear data
        this.currentData = null;
        this.uploadedFile = null;
        
        // Reset progress
        this.progressFill.style.width = '0%';
        
        this.showToast('Form berhasil direset', 'info');
    }
    
    /**
     * Reset file input
     */
    resetFileInput() {
        this.fileInput.value = '';
        this.uploadedFile = null;
    }
    
    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Set message
        const toastMessage = this.toast.querySelector('.toast-message');
        toastMessage.textContent = message;
        
        // Set type class
        this.toast.className = `toast ${type}`;
        
        // Show toast
        this.toast.classList.add('show');
        
        // Hide after 3 seconds
        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 3000);
    }
    
    /**
     * Format confidence score for display
     */
    formatConfidenceScore(score) {
        return `${Math.round(score * 100)}%`;
    }
    
    /**
     * Get confidence score color
     */
    getConfidenceScoreColor(score) {
        if (score >= 0.8) return '#22c55e';
        if (score >= 0.6) return '#f59e0b';
        return '#ef4444';
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing KTP Detection App...');
    window.ktpApp = new KTPDetectionApp();
    console.log('✅ KTP Detection App initialized');
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    if (window.ktpApp) {
        window.ktpApp.showToast('Terjadi kesalahan aplikasi', 'error');
    }
});

// Service worker registration (optional, for PWA)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Register service worker if available
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(error => console.log('SW registration failed'));
    });
}
