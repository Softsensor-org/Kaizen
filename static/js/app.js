// NEMT 837P EDI Generator - Client-side JavaScript

// DOM Elements
const fileInput = document.getElementById('fileInput');
const fileType = document.getElementById('fileType');
const payerCode = document.getElementById('payerCode');
const usageIndicator = document.getElementById('usageIndicator');
const useCR1Locations = document.getElementById('useCR1Locations');
const validateBtn = document.getElementById('validateBtn');
const generateBtn = document.getElementById('generateBtn');
const loadingSpinner = document.getElementById('loadingSpinner');
const resultsSection = document.getElementById('resultsSection');
const errorDisplay = document.getElementById('errorDisplay');
const statsDisplay = document.getElementById('statsDisplay');
const ediOutput = document.getElementById('ediOutput');
const validationOutput = document.getElementById('validationOutput');
const jsonOutput = document.getElementById('jsonOutput');
const copyEdiBtn = document.getElementById('copyEdiBtn');
const downloadEdiBtn = document.getElementById('downloadEdiBtn');

// Tab handling
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');

        // Remove active class from all tabs
        tabBtns.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));

        // Add active class to selected tab
        btn.classList.add('active');
        document.getElementById(tabName + 'Tab').classList.add('active');
    });
});

// Auto-detect file type from extension
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext === 'json') {
            fileType.value = 'json';
        } else if (ext === 'csv') {
            fileType.value = 'csv';
        }
    }
});

// Validate button handler
validateBtn.addEventListener('click', async () => {
    await processFile('validate');
});

// Generate button handler
generateBtn.addEventListener('click', async () => {
    await processFile('generate');
});

// Copy EDI button
copyEdiBtn.addEventListener('click', () => {
    const ediText = ediOutput.textContent;
    navigator.clipboard.writeText(ediText).then(() => {
        copyEdiBtn.textContent = '✓ Copied!';
        setTimeout(() => {
            copyEdiBtn.textContent = '📋 Copy';
        }, 2000);
    });
});

// Download EDI button
downloadEdiBtn.addEventListener('click', () => {
    const ediText = ediOutput.textContent;
    const blob = new Blob([ediText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `claim_${Date.now()}.edi`;
    a.click();
    URL.revokeObjectURL(url);
});

// Main processing function
async function processFile(action) {
    // Validate file selection
    const file = fileInput.files[0];
    if (!file) {
        showError('Please select a file to upload');
        return;
    }

    // Hide previous results/errors
    hideError();
    resultsSection.style.display = 'none';

    // Show loading
    loadingSpinner.style.display = 'block';
    validateBtn.disabled = true;
    generateBtn.disabled = true;

    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', fileType.value);
        formData.append('payer_code', payerCode.value);
        formData.append('usage_indicator', usageIndicator.value);
        formData.append('use_cr1_locations', useCR1Locations.checked ? 'true' : 'false');

        // Choose endpoint
        const endpoint = action === 'validate' ? '/api/validate' : '/api/generate-edi';

        // Make API call
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Unknown error occurred');
        }

        // Display results
        if (action === 'generate') {
            displayResults(data);
        } else {
            displayValidationResults(data);
        }

    } catch (error) {
        showError(error.message);
    } finally {
        // Hide loading
        loadingSpinner.style.display = 'none';
        validateBtn.disabled = false;
        generateBtn.disabled = false;
    }
}

// Display full generation results
function displayResults(data) {
    resultsSection.style.display = 'block';

    // Display stats
    if (data.stats) {
        statsDisplay.innerHTML = `
            <div class="stat-item">
                <div class="stat-label">Member ID</div>
                <div class="stat-value">${data.stats.member_id}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Payer</div>
                <div class="stat-value">${data.stats.payer}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Services</div>
                <div class="stat-value">${data.stats.services}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Total Charge</div>
                <div class="stat-value">$${data.stats.total_charge.toFixed(2)}</div>
            </div>
        `;
    }

    // Display EDI output (formatted with line breaks at ~)
    const formattedEdi = data.edi.replace(/~/g, '~\n');
    ediOutput.textContent = formattedEdi;

    // Display validation report
    validationOutput.textContent = data.validation_report || 'No validation issues';

    // Display parsed JSON
    jsonOutput.textContent = JSON.stringify(data.claim_data, null, 2);

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Display validation-only results
function displayValidationResults(data) {
    resultsSection.style.display = 'block';

    // Display validation status
    const statusClass = data.is_valid ? 'success' : 'error';
    const statusIcon = data.is_valid ? '✓' : '✗';
    const statusText = data.is_valid ? 'Valid' : 'Invalid';

    statsDisplay.innerHTML = `
        <div class="stat-item">
            <div class="stat-label">Validation Status</div>
            <div class="stat-value ${statusClass}">${statusIcon} ${statusText}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Errors</div>
            <div class="stat-value">${data.errors ? data.errors.length : 0}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Warnings</div>
            <div class="stat-value">${data.warnings ? data.warnings.length : 0}</div>
        </div>
    `;

    // Hide EDI tab for validation-only
    ediOutput.textContent = 'Generate EDI to see output';

    // Display validation report
    validationOutput.textContent = data.validation_report || 'No validation issues';

    // Switch to validation tab
    document.querySelector('[data-tab="validation"]').click();

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Show error message
function showError(message, details = null) {
    errorDisplay.style.display = 'block';
    document.getElementById('errorMessage').textContent = message;

    if (details) {
        document.getElementById('errorDetails').textContent = details;
        document.getElementById('errorDetails').style.display = 'block';
    }

    errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Hide error message
function hideError() {
    errorDisplay.style.display = 'none';
    document.getElementById('errorDetails').style.display = 'none';
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Initialize
console.log('NEMT 837P EDI Generator loaded');
console.log('Ready to process JSON and CSV files');
