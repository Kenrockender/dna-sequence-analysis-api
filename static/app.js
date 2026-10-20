// DNA Sequence Analysis - Frontend JavaScript

let currentFile = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    // File input
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
    
    // Sample selection
    document.getElementById('sampleSelect').addEventListener('change', handleSampleSelect);
    
    // Operation selection
    document.querySelectorAll('input[name="operation"]').forEach(radio => {
        radio.addEventListener('change', handleOperationChange);
    });
    
    // Run button
    document.getElementById('runButton').addEventListener('click', runAnalysis);
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    currentFile = file;
    document.getElementById('fileName').textContent = `Selected: ${file.name}`;
    document.getElementById('runButton').disabled = false;
    hideError();
}

async function handleSampleSelect(e) {
    const sample = e.target.value;
    if (!sample) {
        currentFile = null;
        document.getElementById('fileName').textContent = '';
        document.getElementById('runButton').disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`/static/samples/${sample}.fasta`);
        if (!response.ok) {
            // Try alternative path
            const altResponse = await fetch(`/Supporting Files/${sample}.fasta`);
            if (!altResponse.ok) throw new Error('Sample file not found');
            const blob = await altResponse.blob();
            currentFile = new File([blob], `${sample}.fasta`, { type: 'text/plain' });
        } else {
            const blob = await response.blob();
            currentFile = new File([blob], `${sample}.fasta`, { type: 'text/plain' });
        }
        
        document.getElementById('fileName').textContent = `Loaded: ${sample}.fasta`;
        document.getElementById('runButton').disabled = false;
        hideError();
    } catch (error) {
        showError('Failed to load sample file: ' + error.message);
    }
}

function handleOperationChange() {
    const operation = document.querySelector('input[name="operation"]:checked').value;
    const frameSection = document.getElementById('frameSection');
    
    if (operation === 'translate') {
        frameSection.style.display = 'block';
    } else {
        frameSection.style.display = 'none';
    }
    
    hideResults();
}

async function runAnalysis() {
    if (!currentFile) return;
    
    const operation = document.querySelector('input[name="operation"]:checked').value;
    const runButton = document.getElementById('runButton');
    const buttonText = runButton.querySelector('.button-text');
    const buttonLoader = runButton.querySelector('.button-loader');
    
    // Show loading state
    runButton.disabled = true;
    buttonText.style.display = 'none';
    buttonLoader.style.display = 'inline';
    hideError();
    hideResults();
    
    try {
        const formData = new FormData();
        formData.append('file', currentFile);
        
        let endpoint = `/api/${operation}`;
        if (operation === 'translate') {
            const frame = document.getElementById('frameSelect').value;
            formData.append('frame', frame);
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Analysis failed');
        }
        
        displayResults(operation, data);
    } catch (error) {
        showError(error.message);
    } finally {
        // Reset button state
        runButton.disabled = false;
        buttonText.style.display = 'inline';
        buttonLoader.style.display = 'none';
    }
}

function displayResults(operation, data) {
    const resultsSection = document.getElementById('resultsSection');
    const sequenceInfo = document.getElementById('sequenceInfo');
    
    resultsSection.style.display = 'block';
    
    // Display sequence info
    sequenceInfo.innerHTML = `
        <strong>Sequence ID:</strong> ${data.sequence_id}<br>
        ${data.reference_id ? `<strong>Reference:</strong> ${data.reference_id}` : ''}
    `;
    
    if (operation === 'align') {
        displayAlignmentResults(data);
    } else if (operation === 'translate') {
        displayTranslationResults(data);
    } else if (operation === 'analyze') {
        displayAnalyzeResults(data);
    }
}

function displayAlignmentResults(data) {
    document.getElementById('alignmentResults').style.display = 'block';
    
    // Stats
    const stats = document.getElementById('alignmentStats');
    stats.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Score</div>
                <div class="stat-value">${data.alignment.score.toFixed(1)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Identity</div>
                <div class="stat-value">${(data.alignment.identity * 100).toFixed(1)}%</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Variants</div>
                <div class="stat-value">${data.variants.length}</div>
            </div>
        </div>
    `;
    
    // Variants table
    const variantsTable = document.getElementById('variantsTable');
    if (data.variants.length > 0) {
        let tableHTML = '<h4>Variants</h4><table class="variants-table"><thead><tr>';
        tableHTML += '<th>Position</th><th>Type</th><th>Reference</th><th>Alternate</th></tr></thead><tbody>';
        
        data.variants.forEach(v => {
            tableHTML += `<tr>
                <td>${v.position}</td>
                <td><span class="variant-type ${v.type}">${v.type}</span></td>
                <td class="sequence-text">${v.ref}</td>
                <td class="sequence-text">${v.alt}</td>
            </tr>`;
        });
        
        tableHTML += '</tbody></table>';
        variantsTable.innerHTML = tableHTML;
    } else {
        variantsTable.innerHTML = '<p class="no-variants">No variants found (perfect match)</p>';
    }
    
    // Alignment viewer
    displayAlignment(data.alignment.reference_aligned, data.alignment.query_aligned);
}

function displayTranslationResults(data) {
    document.getElementById('translationResults').style.display = 'block';
    
    const translationData = document.getElementById('translationData');
    translationData.innerHTML = `
        <div class="translation-info">
            <p><strong>Frame:</strong> ${data.frame}</p>
            <p><strong>Length:</strong> ${data.length} amino acids</p>
            <p><strong>Stop Codon:</strong> ${data.has_stop_codon ? 'Yes' : 'No'}</p>
        </div>
        <div class="protein-sequence">
            <h4>Protein Sequence</h4>
            <div class="sequence-text monospace">${formatProteinSequence(data.protein)}</div>
        </div>
    `;
}

function displayAnalyzeResults(data) {
    document.getElementById('analyzeResults').style.display = 'block';
    
    let html = '';
    
    // Alignment stats
    html += `
        <h4>Alignment</h4>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Score</div>
                <div class="stat-value">${data.alignment.score.toFixed(1)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Identity</div>
                <div class="stat-value">${(data.alignment.identity * 100).toFixed(1)}%</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Variants</div>
                <div class="stat-value">${data.variants.length}</div>
            </div>
        </div>
    `;
    
    // Variants with effects
    if (data.variants.length > 0) {
        html += '<h4>Variants with Effects</h4><table class="variants-table effects-table"><thead><tr>';
        html += '<th>Position</th><th>Type</th><th>Ref→Alt</th><th>Effect</th><th>Details</th></tr></thead><tbody>';
        
        data.variants.forEach(v => {
            const refAlt = v.type === 'SNV' ? `${v.ref}→${v.alt}` : `${v.ref}/${v.alt}`;
            const effect = v.effect || 'N/A';
            let details = '';
            
            if (v.aa_change) {
                details = v.aa_change;
            } else if (v.notes) {
                details = v.notes;
            } else if (v.codon) {
                details = `Codon ${v.codon}`;
            }
            
            html += `<tr>
                <td>${v.position}</td>
                <td><span class="variant-type ${v.type}">${v.type}</span></td>
                <td class="sequence-text">${refAlt}</td>
                <td><span class="effect-badge ${effect}">${effect}</span></td>
                <td class="details-cell">${details}</td>
            </tr>`;
        });
        
        html += '</tbody></table>';
    }
    
    // Translation
    html += `
        <h4>Translation (Frame 1)</h4>
        <div class="translation-grid">
            <div>
                <strong>Reference:</strong> ${data.reference_translation.length} aa
                ${data.reference_translation.has_stop_codon ? '(has stop)' : ''}
            </div>
            <div>
                <strong>Query:</strong> ${data.query_translation.length} aa
                ${data.query_translation.has_stop_codon ? '(has stop)' : ''}
            </div>
        </div>
    `;
    
    document.getElementById('analyzeData').innerHTML = html;
}

function displayAlignment(refSeq, querySeq) {
    const viewer = document.getElementById('alignmentViewer');
    const blockSize = 60;
    let html = '<h4>Alignment</h4><div class="alignment-viewer">';
    
    for (let i = 0; i < refSeq.length; i += blockSize) {
        const refBlock = refSeq.substring(i, i + blockSize);
        const queryBlock = querySeq.substring(i, i + blockSize);
        
        html += `<div class="alignment-block">`;
        html += `<div class="alignment-position">${i + 1}</div>`;
        html += `<div class="alignment-row">`;
        html += `<span class="sequence-label">Ref:</span>`;
        html += `<span class="sequence-text monospace">${highlightDifferences(refBlock, queryBlock, 'ref')}</span>`;
        html += `</div>`;
        html += `<div class="alignment-row">`;
        html += `<span class="sequence-label">Query:</span>`;
        html += `<span class="sequence-text monospace">${highlightDifferences(queryBlock, refBlock, 'query')}</span>`;
        html += `</div>`;
        html += `</div>`;
    }
    
    html += '</div>';
    viewer.innerHTML = html;
}

function highlightDifferences(seq1, seq2, type) {
    let result = '';
    for (let i = 0; i < seq1.length; i++) {
        const char = seq1[i];
        if (char === '-') {
            result += `<span class="gap">${char}</span>`;
        } else if (seq2[i] !== char && seq2[i] !== '-') {
            result += `<span class="mismatch">${char}</span>`;
        } else {
            result += char;
        }
    }
    return result;
}

function formatProteinSequence(protein) {
    if (!protein) return '<em>No protein produced</em>';
    
    // Break into lines of 60 characters
    const lineLength = 60;
    let result = '';
    for (let i = 0; i < protein.length; i += lineLength) {
        if (i > 0) result += '\n';
        result += protein.substring(i, i + lineLength);
    }
    return result;
}

function showError(message) {
    const errorDisplay = document.getElementById('errorDisplay');
    errorDisplay.textContent = `❌ Error: ${message}`;
    errorDisplay.style.display = 'block';
}

function hideError() {
    document.getElementById('errorDisplay').style.display = 'none';
}

function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('alignmentResults').style.display = 'none';
    document.getElementById('translationResults').style.display = 'none';
    document.getElementById('analyzeResults').style.display = 'none';
}
