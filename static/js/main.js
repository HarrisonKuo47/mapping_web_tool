/*
Main JavaScript for Lead Frame Mapping Tool
Date: 2025-08-27 02:31:47 UTC
User: HarrisonKuo47
*/

// Global variables for layer management
let availableLayers = [];
let defaultLayers = ['SH-01_OBJECT', 'SH-01_DIM', 'SH-01_PKG'];
let selectedLayers = new Set(defaultLayers);
let isLoading = false;

// Layer management functions
async function loadLayers() {
    const dxfFilename = document.getElementById('dxfFilename').value.trim();
    if (!dxfFilename) {
        showMessage('Please enter DXF filename first', 'error');
        return;
    }
    
    if (isLoading) return;
    
    const loadBtn = document.getElementById('loadLayersBtn');
    const originalText = loadBtn.innerHTML;
    
    try {
        isLoading = true;
        loadBtn.innerHTML = '<div class="spinner" style="margin: 0 5px 0 0;"></div>Loading...';
        loadBtn.disabled = true;
        
        showLoading('Extracting layers from DXF file...');
        
        const response = await fetch(`/api/leadframe/${encodeURIComponent(dxfFilename)}/layers`);
        const data = await response.json();
        
        if (data.status === 'success') {
            availableLayers = data.available_layers || [];
            defaultLayers = data.default_layers || ['SH-01_OBJECT', 'SH-01_DIM', 'SH-01_PKG'];
            
            // Auto-select defaults that exist in the file
            selectedLayers = new Set(defaultLayers.filter(layer => availableLayers.includes(layer)));
            
            renderLayerSelection();
            showLayerSection();
            showMessage(`Successfully loaded ${availableLayers.length} layers from ${dxfFilename}`, 'success');
        } else {
            showMessage('Failed to load layers. Please ensure the DXF file is uploaded and accessible.', 'error');
        }
    } catch (error) {
        console.error('Error loading layers:', error);
        showMessage('Error loading layers: ' + error.message, 'error');
    } finally {
        isLoading = false;
        loadBtn.innerHTML = originalText;
        loadBtn.disabled = false;
    }
}

function renderLayerSelection() {
    const container = document.getElementById('layer-container');
    
    if (availableLayers.length === 0) {
        container.innerHTML = '<div class="error-message">No layers found in DXF file</div>';
        return;
    }
    
    const layerGrid = document.createElement('div');
    layerGrid.className = 'layer-grid';
    
    availableLayers.forEach(layer => {
        const isSelected = selectedLayers.has(layer);
        const isDefault = defaultLayers.includes(layer);
        
        const layerItem = document.createElement('div');
        layerItem.className = `layer-item ${isSelected ? 'selected' : ''} ${isDefault ? 'default' : ''}`;
        layerItem.onclick = () => toggleLayer(layer);
        
        layerItem.innerHTML = `
            <input type="checkbox" class="layer-checkbox" ${isSelected ? 'checked' : ''} onchange="toggleLayer('${layer}')" />
            <span class="layer-name">${layer}</span>
            ${isDefault ? '<span class="layer-badge default">Default</span>' : ''}
        `;
        
        layerGrid.appendChild(layerItem);
    });
    
    container.innerHTML = '';
    container.appendChild(layerGrid);
    updateSummary();
}

function toggleLayer(layer) {
    if (selectedLayers.has(layer)) {
        selectedLayers.delete(layer);
    } else {
        selectedLayers.add(layer);
    }
    renderLayerSelection();
    updateSelectedLayersInput();
}

function selectAllLayers() {
    selectedLayers = new Set(availableLayers);
    renderLayerSelection();
    updateSelectedLayersInput();
}

function clearAllLayers() {
    selectedLayers.clear();
    renderLayerSelection();
    updateSelectedLayersInput();
}

function selectDefaultLayers() {
    selectedLayers = new Set(defaultLayers.filter(layer => availableLayers.includes(layer)));
    renderLayerSelection();
    updateSelectedLayersInput();
}

function showLayerSection() {
    const section = document.getElementById('layer-selection');
    section.classList.add('show');
}

function toggleLayerSection() {
    const section = document.getElementById('layer-selection');
    const isVisible = section.classList.contains('show');
    
    if (isVisible) {
        section.classList.remove('show');
        document.querySelector('.layer-controls button:last-child').innerHTML = '🔽 Show';
    } else {
        section.classList.add('show');
        document.querySelector('.layer-controls button:last-child').innerHTML = '🔼 Hide';
    }
}

function updateSummary() {
    document.getElementById('selected-count').textContent = selectedLayers.size;
    document.getElementById('total-count').textContent = availableLayers.length;
}

function updateSelectedLayersInput() {
    document.getElementById('selectedLayers').value = Array.from(selectedLayers).join(',');
}

function showLoading(message) {
    const container = document.getElementById('layer-container');
    container.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            ${message}
        </div>
    `;
}

function showMessage(message, type = 'info') {
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.error-message, .success-message');
    existingMessages.forEach(msg => msg.remove());
    
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'error' ? 'error-message' : 'success-message';
    messageDiv.textContent = message;
    
    const section = document.getElementById('layer-selection');
    section.appendChild(messageDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

// Clear results functionality
async function clearAllResults() {
    if (!confirm('Clear all analysis results? This cannot be undone.')) return;
    
    const btn = document.getElementById('clearBtn');
    const messageDiv = document.getElementById('clearMessage');
    
    try {
        btn.disabled = true;
        btn.innerHTML = '🔄 Clearing...';
        
        const response = await fetch('/api/results/clear', { method: 'DELETE' });
        const result = await response.json();
        
        if (result.status === 'success') {
            messageDiv.innerHTML = `
                <div style="background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    ✅ ${result.message} - Redirecting to home page...
                </div>
            `;
            
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
            
        } else {
            throw new Error(result.message);
        }
        
    } catch (error) {
        messageDiv.innerHTML = `
            <div style="background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin: 10px 0;">
                ❌ Error: ${error.message}
            </div>
        `;
        btn.disabled = false;
        btn.innerHTML = '🗑️ Clear All Results';
    }
}

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const analysisForm = document.getElementById('analysisForm');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(e) {
            if (selectedLayers.size === 0 && availableLayers.length > 0) {
                e.preventDefault();
                showMessage('Please select at least one layer for analysis', 'error');
                return false;
            }
            updateSelectedLayersInput();
        });
    }
    
    // Initialize
    updateSelectedLayersInput();
    console.log('🚀 Lead Frame Mapping Tool v2.0.0 initialized');
    console.log('📅 Date: 2025-08-27 02:31:47 UTC');
    console.log('👤 User: HarrisonKuo47');
});