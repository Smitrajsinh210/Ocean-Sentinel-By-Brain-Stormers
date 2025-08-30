// Utility Functions
function toggleLayer(layerType) {
    if (window.oceanSentinel && window.oceanSentinel.map && window.oceanSentinel.threatLayers) {
        console.log(`Toggling ${layerType} layer`);

        const layer = window.oceanSentinel.threatLayers[layerType];
        if (layer) {
            if (window.oceanSentinel.map.hasLayer(layer)) {
                window.oceanSentinel.map.removeLayer(layer);
                console.log(`${layerType} layer hidden`);
            } else {
                window.oceanSentinel.map.addLayer(layer);
                console.log(`${layerType} layer shown`);

                // Add some demo data to the layer if empty
                window.oceanSentinel.addLayerDemoData(layerType);
            }
        } else {
            console.log(`Layer ${layerType} not found`);
        }
    }
}

function closeAlert() {
    document.getElementById('alertModal').classList.add('hidden');
}

function acknowledgeAlert() {
    console.log('Alert acknowledged');
    closeAlert();

    const alertCount = document.getElementById('alertCount');
    const count = Math.max(0, parseInt(alertCount.textContent) - 1);
    alertCount.textContent = count;

    if (count === 0) {
        alertCount.classList.add('hidden');
        alertCount.classList.remove('alert-pulse');
    }
}

function viewDetails() {
    console.log('Viewing alert details');
    closeAlert();
    // Navigate to detailed threat analysis
}