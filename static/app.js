// DNA Sequence Analysis - Frontend JavaScript

let currentFile = null;
let currentResults = null;
let currentOperation = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    initializeTheme();
    setupKeyboardShortcuts();
});

function setupEventListeners() {
    // File input
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    
    fileInput.addEventListener('change', handleFileSelect);

    // The whole drop area opens the file picker, not just a small text link.
    dropZone.addEventListener('click', (e) => {
        if (e.target === fileInput) return;
        fileInput.click();
    });
    
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

    dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
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
    
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
    // Download and copy buttons
    document.getElementById('downloadBtn').addEventListener('click', downloadResults);
    document.getElementById('copyBtn').addEventListener('click', copyResults);
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
    
    // Read file and calculate statistics
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        const sequence = parseFastaSequence(content);
        if (sequence) {
            displaySequenceStats(sequence);
        }
    };
    reader.readAsText(file);
}

async function handleSampleSelect(e) {
    const sample = e.target.value;
    if (!sample) {
        currentFile = null;
        document.getElementById('fileName').textContent = '';
        document.getElementById('runButton').disabled = true;
        document.getElementById('sequenceStats').style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`/static/samples/${sample}.fasta`);
        if (!response.ok) {
            // Try alternative path
            const altResponse = await fetch(`/Supporting Files/${sample}.fasta`);
            if (!altResponse.ok) throw new Error('Sample file not found');
            const text = await altResponse.text();
            const blob = new Blob([text], { type: 'text/plain' });
            currentFile = new File([blob], `${sample}.fasta`, { type: 'text/plain' });
        } else {
            const text = await response.text();
            const blob = new Blob([text], { type: 'text/plain' });
            currentFile = new File([blob], `${sample}.fasta`, { type: 'text/plain' });
        }
        
        document.getElementById('fileName').textContent = `Loaded: ${sample}.fasta`;
        document.getElementById('runButton').disabled = false;
        hideError();
        
        // Calculate statistics
        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            const sequence = parseFastaSequence(content);
            if (sequence) {
                displaySequenceStats(sequence);
            }
        };
        reader.readAsText(currentFile);
    } catch (error) {
        showError('Failed to load sample file: ' + error.message);
    }
}

function handleOperationChange() {
    const operation = document.querySelector('input[name="operation"]:checked').value;
    const frameSection = document.getElementById('frameSection');
    
    if (operation === 'translate') {
        frameSection.style.display = 'flex';
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
    buttonLoader.style.display = 'inline-flex';
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
        
        currentResults = data;
        currentOperation = operation;
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
    resultsSection.focus();
    
    // Display sequence info
    // sequence_id is derived from uploaded content, so add it as text rather
    // than interpolating it into HTML.
    sequenceInfo.replaceChildren();
    appendLabeledValue(sequenceInfo, 'Sequence ID:', data.sequence_id);
    if (data.reference_id) {
        appendLabeledValue(sequenceInfo, 'Reference:', data.reference_id);
    }
    
    if (operation === 'align') {
        displayAlignmentResults(data);
    } else if (operation === 'translate') {
        displayTranslationResults(data);
    } else if (operation === 'analyze') {
        displayAnalyzeResults(data);
    }
}

function appendLabeledValue(container, label, value) {
    const labelElement = document.createElement('strong');
    labelElement.textContent = `${label} `;
    container.append(labelElement, document.createTextNode(value));
    container.append(document.createElement('br'));
}

function escapeHtml(value) {
    const element = document.createElement('div');
    element.textContent = String(value);
    return element.innerHTML;
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
                <td class="sequence-text">${escapeHtml(v.ref)}</td>
                <td class="sequence-text">${escapeHtml(v.alt)}</td>
            </tr>`;
        });
        
        tableHTML += '</tbody></table>';
        variantsTable.innerHTML = tableHTML;
        
        // Display variant map
        displayVariantMap(data.variants, data.alignment.reference_aligned.length);
    } else {
        variantsTable.innerHTML = '<p class="no-variants">No variants found (perfect match)</p>';
    }
    
    // Alignment viewer
    lastDrawnData = { ref: data.alignment.reference_aligned, qry: data.alignment.query_aligned };
    displayAlignment(data.alignment.reference_aligned, data.alignment.query_aligned);
}

function displayTranslationResults(data) {
    document.getElementById('translationResults').style.display = 'block';
    
    const translationData = document.getElementById('translationData');
    translationData.innerHTML = `
        <div class="translation-info">
            <p><strong>Frame:</strong> ${escapeHtml(data.frame)}</p>
            <p><strong>Length:</strong> ${escapeHtml(data.length)} amino acids</p>
            <p><strong>Stop Codon:</strong> ${data.has_stop_codon ? 'Yes' : 'No'}</p>
        </div>
        <div class="protein-sequence">
            <h4>Protein Sequence</h4>
            <div class="sequence-text monospace">${escapeHtml(formatProteinSequence(data.protein))}</div>
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
    
    // Variant map
    if (data.variants.length > 0) {
        displayVariantMap(data.variants, data.alignment.reference_aligned.length);
    }
    
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
                <td class="sequence-text">${escapeHtml(refAlt)}</td>
                <td><span class="effect-badge ${escapeHtml(effect)}">${escapeHtml(effect)}</span></td>
                <td class="details-cell">${escapeHtml(details)}</td>
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
    
    // Calculate how many columns fit based on screen width (like the reference implementation)
    const blockSize = calculateColumnsPerBlock();
    console.log('Displaying alignment with block size:', blockSize);
    
    let html = '<h4>Alignment</h4><div class="aln-container">';
    
    let refCount = 0;
    let qryCount = 0;
    
    for (let i = 0; i < refSeq.length; i += blockSize) {
        const refBlock = refSeq.substring(i, i + blockSize);
        const queryBlock = querySeq.substring(i, i + blockSize);
        
        // Count non-gap bases for position numbering
        const refBases = refBlock.replace(/-/g, '').length;
        const qryBases = queryBlock.replace(/-/g, '').length;
        
        html += `<div class="aln-block">`;
        
        // Reference row
        html += `<div class="aln-row">`;
        html += `<span class="aln-label">REF</span>`;
        html += `<span class="aln-pos">${refBases ? refCount + 1 : ''}</span>`;
        
        for (let j = 0; j < refBlock.length; j++) {
            const refChar = refBlock[j];
            const queryChar = queryBlock[j];
            const state = getColumnState(refChar, queryChar);
            html += `<span class="aln-base ${refChar} ${state}">${refChar === '-' ? '–' : refChar}</span>`;
        }
        html += `</div>`;
        
        // Query row
        html += `<div class="aln-row">`;
        html += `<span class="aln-label">QRY</span>`;
        html += `<span class="aln-pos">${qryBases ? qryCount + 1 : ''}</span>`;
        
        for (let j = 0; j < queryBlock.length; j++) {
            const refChar = refBlock[j];
            const queryChar = queryBlock[j];
            const state = getColumnState(refChar, queryChar);
            html += `<span class="aln-base ${queryChar} ${state}">${queryChar === '-' ? '–' : queryChar}</span>`;
        }
        html += `</div>`;
        
        html += `</div>`;
        
        refCount += refBases;
        qryCount += qryBases;
    }
    
    html += '</div>';
    
    // Add legend
    html += `<div class="aln-legend">
        <span class="legend-item"><span class="legend-box match"></span> match</span>
        <span class="legend-item"><span class="legend-box mismatch"></span> mismatch (SNV)</span>
        <span class="legend-item"><span class="legend-box gap"></span> gap (insertion/deletion)</span>
        <span class="legend-item"><span class="legend-box nn"></span> N (unknown, not a variant)</span>
    </div>`;
    
    viewer.innerHTML = html;
}

function getColumnState(a, b) {
    if (a === '-' || b === '-') return 'gap';
    if (a === 'N' || b === 'N') return 'nn';
    return a === b ? 'match' : 'mismatch';
}

// Calculate optimal columns per block based on available width
function calculateColumnsPerBlock() {
    const viewer = document.getElementById('alignmentViewer');
    if (!viewer) return 60;
    
    // Create probe element exactly like the real alignment
    const probe = document.createElement('div');
    probe.className = 'aln-container';
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.left = '0';
    probe.style.right = '0';
    
    const testBase = document.createElement('span');
    testBase.className = 'aln-base A match';
    testBase.textContent = 'A';
    
    const gutter = document.createElement('span');
    gutter.className = 'aln-gutter';
    
    probe.appendChild(testBase);
    probe.appendChild(gutter);
    viewer.appendChild(probe);
    
    // Measure
    const cs = getComputedStyle(probe);
    const sidePadding = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight) + 2; // +border
    const cellWidth = testBase.getBoundingClientRect().width;
    const gutterWidth = 2.6 + 3.2; // label + pos width in rem, convert to px
    const gutterPx = gutterWidth * parseFloat(getComputedStyle(document.documentElement).fontSize);
    
    viewer.removeChild(probe);
    
    const availableWidth = viewer.clientWidth;
    const roomForBases = availableWidth - sidePadding - gutterPx;
    const columns = Math.floor(roomForBases / cellWidth);
    
    // Round down to multiple of 10, min 10
    return Math.max(10, Math.floor(columns / 10) * 10);
}

// Redraw alignment on window resize
let resizeTimer;
let lastDrawnData = null;
let lastDrawnWidth = 0;

window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        const currentWidth = document.getElementById('alignmentViewer')?.clientWidth || 0;
        if (lastDrawnData && currentWidth !== lastDrawnWidth) {
            console.log('Redrawing alignment for width:', currentWidth);
            lastDrawnWidth = currentWidth;
            displayAlignment(lastDrawnData.ref, lastDrawnData.qry);
        }
    }, 200);
});

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
    if (!protein) return 'No protein produced';
    
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
    errorDisplay.innerHTML = `
        <svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span><strong>Error:</strong> ${escapeHtml(message)}</span>
    `;
    errorDisplay.style.display = 'flex';
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


// ========== NEW FEATURES ==========

// Sequence Statistics
function parseFastaSequence(content) {
    const lines = content.split('\n');
    let sequence = '';
    for (let line of lines) {
        line = line.trim();
        if (!line.startsWith('>') && line.length > 0) {
            sequence += line.toUpperCase();
        }
    }
    return sequence;
}

function displaySequenceStats(sequence) {
    const stats = calculateSequenceStats(sequence);
    document.getElementById('statLength').textContent = stats.length;
    document.getElementById('statGC').textContent = stats.gcPercent.toFixed(1) + '%';
    document.getElementById('statA').textContent = stats.a;
    document.getElementById('statC').textContent = stats.c;
    document.getElementById('statG').textContent = stats.g;
    document.getElementById('statT').textContent = stats.t;
    document.getElementById('sequenceStats').style.display = 'block';
}

function calculateSequenceStats(sequence) {
    const counts = { A: 0, C: 0, G: 0, T: 0, N: 0 };
    for (let base of sequence) {
        if (counts.hasOwnProperty(base)) {
            counts[base]++;
        }
    }
    const total = sequence.length;
    const gcCount = counts.G + counts.C;
    const gcPercent = total > 0 ? (gcCount / total) * 100 : 0;
    
    return {
        length: total,
        gcPercent: gcPercent,
        a: counts.A,
        c: counts.C,
        g: counts.G,
        t: counts.T,
        n: counts.N
    };
}

// Variant Map Visualization
function displayVariantMap(variants, sequenceLength) {
    const container = document.getElementById('variantMap');
    if (!variants || variants.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    const width = container.offsetWidth || 800;
    const height = 60;
    const padding = 20;
    const barHeight = 8;
    const markerHeight = 20;
    
    let svg = `<h4>Variant Distribution</h4>`;
    svg += `<svg class="variant-map-svg" viewBox="0 0 ${width} ${height}">`;
    
    // Background line
    svg += `<line x1="${padding}" y1="${height/2}" x2="${width-padding}" y2="${height/2}" 
            stroke="var(--border)" stroke-width="2"/>`;
    
    // Start and end markers
    svg += `<text x="${padding}" y="${height-5}" fill="var(--muted)" font-size="10" text-anchor="middle">1</text>`;
    svg += `<text x="${width-padding}" y="${height-5}" fill="var(--muted)" font-size="10" text-anchor="middle">${sequenceLength}</text>`;
    
    // Variant markers
    const usableWidth = width - (2 * padding);
    const variantColors = {
        'SNV': '#5274b8',
        'insertion': '#4a9777',
        'deletion': '#c66b6b'
    };
    
    variants.forEach(v => {
        const x = padding + (v.position / sequenceLength) * usableWidth;
        const color = variantColors[v.type] || '#9eb1c8';
        
        svg += `<g class="variant-marker">
                <circle cx="${x}" cy="${height/2}" r="5" fill="${color}" 
                        data-type="${v.type}" data-pos="${v.position}" data-ref="${escapeHtml(v.ref)}" data-alt="${escapeHtml(v.alt)}">
                    <title>${v.type} at position ${v.position}: ${v.ref}→${v.alt}</title>
                </circle>
                <text x="${x}" y="${height/2 - 12}" fill="${color}" font-size="11" font-weight="600" 
                      text-anchor="middle" opacity="0" class="variant-position-label">${v.position}</text>
                </g>`;
    });
    
    svg += `</svg>`;
    container.innerHTML = svg;
}

// Theme Toggle
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const useDarkTheme = savedTheme ? savedTheme === 'dark' : prefersDark;
    document.body.classList.toggle('dark-theme', useDarkTheme);
}

function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Keyboard Shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + U: Upload
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            document.getElementById('fileInput').click();
        }
        
        // Ctrl/Cmd + Enter: Run analysis
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            const runBtn = document.getElementById('runButton');
            if (!runBtn.disabled) {
                runAnalysis();
            }
        }
        
        // Escape: Clear results
        if (e.key === 'Escape') {
            hideResults();
        }
    });
}

// Download Results
function downloadResults() {
    if (!currentResults || !currentOperation) return;

    const existingMenu = document.querySelector('.download-menu');
    if (existingMenu) {
        existingMenu.remove();
        return;
    }

    const downloadBtn = document.getElementById('downloadBtn');
    const menu = document.createElement('div');
    menu.className = 'download-menu';
    menu.setAttribute('role', 'menu');

    const options = [
        { label: 'Download JSON', handler: () => downloadJSON(currentResults, `results_${Date.now()}.json`) },
        { label: 'Variants as CSV', handler: () => downloadVariantsCSV(currentResults) },
    ];

    if (currentOperation === 'translate' || currentOperation === 'analyze') {
        options.push({
            label: 'Protein as FASTA',
            handler: () => downloadProteinFASTA(currentResults)
        });
    }

    options.forEach(opt => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.setAttribute('role', 'menuitem');
        btn.textContent = opt.label;
        btn.addEventListener('click', (event) => {
            event.stopPropagation();
            opt.handler();
            closeMenu();
        });
        menu.appendChild(btn);
    });

    document.body.appendChild(menu);
    const buttonRect = downloadBtn.getBoundingClientRect();
    const menuWidth = menu.offsetWidth || 170;
    menu.style.left = `${Math.max(8, Math.min(buttonRect.right - menuWidth, window.innerWidth - menuWidth - 8))}px`;
    menu.style.top = `${Math.min(buttonRect.bottom + 6, window.innerHeight - menu.offsetHeight - 8)}px`;

    function closeMenu() {
        menu.remove();
        document.removeEventListener('click', handleOutsideClick);
        document.removeEventListener('keydown', handleEscape);
    }

    function handleOutsideClick(event) {
        if (!menu.contains(event.target) && event.target !== downloadBtn && !downloadBtn.contains(event.target)) {
            closeMenu();
        }
    }

    function handleEscape(event) {
        if (event.key === 'Escape') {
            closeMenu();
            downloadBtn.focus();
        }
    }

    // Defer the outside-click listener so the click that opened the menu doesn't close it.
    setTimeout(() => {
        document.addEventListener('click', handleOutsideClick);
        document.addEventListener('keydown', handleEscape);
    }, 0);
}

function downloadJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function downloadVariantsCSV(data) {
    if (!data.variants || data.variants.length === 0) {
        alert('No variants to export');
        return;
    }
    
    let csv = 'Position,Type,Reference,Alternate';
    if (data.variants[0].effect) csv += ',Effect,Details';
    csv += '\n';
    
    data.variants.forEach(v => {
        csv += `${v.position},${v.type},"${v.ref}","${v.alt}"`;
        if (v.effect) {
            const details = v.aa_change || v.notes || '';
            csv += `,${v.effect},"${details}"`;
        }
        csv += '\n';
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `variants_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

function downloadProteinFASTA(data) {
    let protein = '';
    let header = '';
    
    if (data.protein) {
        protein = data.protein;
        header = `>${data.sequence_id}_frame${data.frame}`;
    } else if (data.query_translation && data.query_translation.protein) {
        protein = data.query_translation.protein;
        header = `>${data.sequence_id}_query_protein`;
    }
    
    if (!protein) {
        alert('No protein sequence to export');
        return;
    }
    
    const fasta = `${header}\n${protein}\n`;
    const blob = new Blob([fasta], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `protein_${Date.now()}.fasta`;
    a.click();
    URL.revokeObjectURL(url);
}

// Copy to Clipboard
async function copyResults() {
    if (!currentResults) return;
    
    let text = '';
    
    if (currentOperation === 'align') {
        text = `Sequence: ${currentResults.sequence_id}\n`;
        text += `Score: ${currentResults.alignment.score}\n`;
        text += `Identity: ${(currentResults.alignment.identity * 100).toFixed(1)}%\n`;
        text += `Variants: ${currentResults.variants.length}\n\n`;
        
        if (currentResults.variants.length > 0) {
            text += 'Variants:\n';
            currentResults.variants.forEach(v => {
                text += `${v.position}\t${v.type}\t${v.ref}\t${v.alt}\n`;
            });
        }
    } else if (currentOperation === 'translate') {
        text = `Sequence: ${currentResults.sequence_id}\n`;
        text += `Frame: ${currentResults.frame}\n`;
        text += `Protein (${currentResults.length} aa):\n${currentResults.protein}\n`;
    } else if (currentOperation === 'analyze') {
        text = JSON.stringify(currentResults, null, 2);
    }
    
    try {
        await navigator.clipboard.writeText(text);
        const copyBtn = document.getElementById('copyBtn');
        const originalText = copyBtn.innerHTML;
        copyBtn.classList.add('copied');
        copyBtn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>Copied!`;
        
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtn.innerHTML = originalText;
        }, 2000);
    } catch (err) {
        alert('Failed to copy to clipboard');
    }
}
