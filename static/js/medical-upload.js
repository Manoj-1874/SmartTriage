// Medical Document Upload and Auto-Fill Handler

class MedicalDocumentUploader {
    constructor() {
        this.uploadBtn = document.getElementById('uploadDocBtn');
        this.fileInput = document.getElementById('medicalFileInput');
        this.uploadPreview = document.getElementById('uploadPreview');
        this.previewContent = document.getElementById('previewContent');
        this.applyDataBtn = document.getElementById('applyDataBtn');
        this.closePreviewBtn = document.getElementById('closePreview');

        this.extractedData = null;

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Upload button click
        this.uploadBtn.addEventListener('click', () => {
            this.fileInput.click();
        });

        // File selection
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        // Apply data button
        this.applyDataBtn.addEventListener('click', () => {
            this.applyDataToForm();
        });

        // Close preview button
        this.closePreviewBtn.addEventListener('click', () => {
            this.hidePreview();
        });
    }

    async handleFileUpload(file) {
        console.log('Handling file upload:', file.name);
        // Validate file type
        const allowedTypes = [
            'application/pdf', 
            'image/png', 
            'image/jpeg', 
            'text/plain', 
            'text/csv', 
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ];
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|png|jpg|jpeg|txt|csv|xlsx|xls)$/i)) {
            alert('Please upload a PDF, PNG, JPG, TXT, CSV, or Excel file');
            return;
        }

        // Show loading state on button
        const originalText = this.uploadBtn.innerHTML;
        this.uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        this.uploadBtn.disabled = true;

        // Create form data
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Upload file to backend
            console.log('Sending request to /api/upload-medical-doc');
            const response = await fetch('/api/upload-medical-doc', {
                method: 'POST',
                body: formData
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('Response data:', data);

            // Reset button
            this.uploadBtn.innerHTML = '<i class="fas fa-plus"></i> Upload Document';
            this.uploadBtn.disabled = false;

            if (data.success) {
                console.log('Extracted data:', data.parsed_data);
                this.extractedData = data.parsed_data;
                this.showPreview(data.parsed_data);
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('Failed to upload file. Error: ' + error.message);

            // Reset button
            this.uploadBtn.innerHTML = '<i class="fas fa-plus"></i> Upload Document';
            this.uploadBtn.disabled = false;
        }
    }

    showPreview(parsedData) {
        console.log('Showing preview with data:', parsedData);
        
        // Clear previous content
        this.previewContent.innerHTML = '';

        // Create preview items for each field
        const fields = [
            { key: 'age', label: 'Age' },
            { key: 'gender', label: 'Gender' },
            { key: 'symptoms', label: 'Symptoms' },
            { key: 'blood_pressure', label: 'Blood Pressure' },
            { key: 'heart_rate', label: 'Heart Rate' },
            { key: 'temperature', label: 'Temperature' },
            { key: 'medical_history', label: 'Medical History' }
        ];

        let fieldsFound = 0;
        fields.forEach(field => {
            const value = parsedData[field.key];
            console.log(`Field ${field.key}:`, value);
            if (value) {
                fieldsFound++;
                const item = document.createElement('div');
                item.className = 'preview-item';
                item.innerHTML = `
                    <label>${field.label}</label>
                    <div class="value">${value}</div>
                `;
                this.previewContent.appendChild(item);
            }
        });

        console.log(`Found ${fieldsFound} fields with values`);
        
        // Show preview section
        this.uploadPreview.style.display = 'block';
    }

    hidePreview() {
        this.uploadPreview.style.display = 'none';
        this.extractedData = null;

        // Reset file input
        this.fileInput.value = '';
    }

    applyDataToForm() {
        if (!this.extractedData) {
            console.error('No extracted data available');
            return;
        }

        console.log('Applying data to form:', this.extractedData);
        const form = document.getElementById('triageForm');

        if (!form) {
            console.error('Form not found');
            return;
        }

        // Apply age
        if (this.extractedData.age) {
            const ageInput = form.querySelector('input[name="age"]');
            console.log('Age input:', ageInput, 'Value:', this.extractedData.age);
            if (ageInput) ageInput.value = this.extractedData.age;
        }

        // Apply gender
        if (this.extractedData.gender) {
            const genderSelect = form.querySelector('select[name="gender"]');
            if (genderSelect) {
                const option = Array.from(genderSelect.options).find(
                    opt => opt.value.toLowerCase() === this.extractedData.gender.toLowerCase()
                );
                if (option) genderSelect.value = option.value;
            }
        }

        // Apply symptoms
        if (this.extractedData.symptoms) {
            const symptomsInput = form.querySelector('textarea[name="symptom"]'); // Changed from "symptoms"
            if (symptomsInput) symptomsInput.value = this.extractedData.symptoms;
        }

        // Apply blood pressure (Split into sys_bp and dia_bp)
        if (this.extractedData.blood_pressure) {
            console.log('Applying blood pressure:', this.extractedData.blood_pressure);
            const parts = this.extractedData.blood_pressure.split('/');
            if (parts.length === 2) {
                const sysInput = form.querySelector('input[name="sys_bp"]');
                const diaInput = form.querySelector('input[name="dia_bp"]');
                console.log('Systolic input:', sysInput, 'Value:', parts[0]);
                console.log('Diastolic input:', diaInput, 'Value:', parts[1]);
                if (sysInput) {
                    sysInput.value = parts[0].trim();
                    console.log('Set systolic to:', sysInput.value);
                }
                if (diaInput) {
                    diaInput.value = parts[1].trim();
                    console.log('Set diastolic to:', diaInput.value);
                }
            }
        }

        // Apply heart rate
        if (this.extractedData.heart_rate) {
            console.log('Applying heart rate:', this.extractedData.heart_rate);
            const hrInput = form.querySelector('input[name="hr"]');
            console.log('Heart rate input:', hrInput);
            if (hrInput) {
                hrInput.value = this.extractedData.heart_rate;
                console.log('Set heart rate to:', hrInput.value);
            }
        }

        // Apply temperature
        if (this.extractedData.temperature) {
            console.log('Applying temperature:', this.extractedData.temperature);
            const tempInput = form.querySelector('input[name="temp"]');
            console.log('Temperature input:', tempInput);
            if (tempInput) {
                tempInput.value = this.extractedData.temperature;
                console.log('Set temperature to:', tempInput.value);
            }
        }

        // Apply medical history
        if (this.extractedData.medical_history) {
            console.log('Applying medical history:', this.extractedData.medical_history);
            const historySelect = form.querySelector('select[name="history"]');
            console.log('Medical history select:', historySelect);
            
            if (historySelect) {
                const history = this.extractedData.medical_history.toLowerCase().trim();
                console.log('Looking for match in options:', Array.from(historySelect.options).map(o => o.value));

                // Try to find matching option (skip empty values)
                const matchingOption = Array.from(historySelect.options).find(opt => {
                    const optValue = opt.value.toLowerCase().trim();
                    
                    // Skip empty option values
                    if (!optValue) return false;
                    
                    const matches = history.includes(optValue) || optValue.includes(history);
                    console.log(`Checking option '${opt.value}' (value: '${optValue}'): ${matches}`);
                    return matches;
                });

                console.log('Matching option found:', matchingOption);

                if (matchingOption) {
                    historySelect.value = matchingOption.value;
                    console.log('Set medical history to:', historySelect.value);
                } else if (history.includes('none') || history === '') {
                    historySelect.value = 'None';
                    console.log('Set medical history to: None (default)');
                } else {
                    historySelect.value = 'Other';
                    console.log('Set medical history to: Other (no match found)');
                }
            }
        }

        // Scroll to form
        console.log('Scrolling to form...');
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Show success message
        console.log('All data applied successfully!');
        alert('✅ Form auto-filled successfully! Please review and submit.');

        // Hide preview
        this.hidePreview();
        console.log('Apply data complete!');
    }
}

// Initialize when DOM is loaded or if already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('Initializing MedicalDocumentUploader on DOMContentLoaded');
        new MedicalDocumentUploader();
    });
} else {
    console.log('Initializing MedicalDocumentUploader immediately');
    new MedicalDocumentUploader();
}
