let map;

function initMap() {
    const today = new Date().toISOString().split('T')[0];
    
    map = new ol.Map({
        target: 'map',
        layers: [
            // Primary layer - VIIRS SNPP (Suomi NPP satellite)
            new ol.layer.Tile({
                source: new ol.source.TileWMS({
                    url: 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
                    params: {
                        'LAYERS': 'VIIRS_SNPP_CorrectedReflectance_TrueColor',
                        'FORMAT': 'image/jpeg',
                        'VERSION': '1.3.0',
                        'TIME': today,
                        'WIDTH': 512,
                        'HEIGHT': 512,
                        'TILED': true
                    },
                    projection: 'EPSG:4326',
                    wrapX: false,
                    crossOrigin: 'anonymous',
                    interpolate: true
                }),
                extent: [-180, -90, 180, 90]
            }),
            // Add coastlines
            new ol.layer.Tile({
                source: new ol.source.TileWMS({
                    url: 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
                    params: {
                        'LAYERS': 'Coastlines_15m',
                        'FORMAT': 'image/png',
                        'TRANSPARENT': true,
                        'VERSION': '1.3.0'
                    },
                    projection: 'EPSG:4326',
                    wrapX: false,
                    crossOrigin: 'anonymous'
                }),
                opacity: 0.7
            }),
            // Add country/administrative borders
            new ol.layer.Tile({
                source: new ol.source.TileWMS({
                    url: 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
                    params: {
                        'LAYERS': 'Reference_Features_15m',
                        'FORMAT': 'image/png',
                        'TRANSPARENT': true,
                        'VERSION': '1.3.0'
                    },
                    projection: 'EPSG:4326',
                    wrapX: false,
                    crossOrigin: 'anonymous'
                }),
                opacity: 0.7
            }),
            // Add place labels
            new ol.layer.Tile({
                source: new ol.source.TileWMS({
                    url: 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
                    params: {
                        'LAYERS': 'Reference_Labels_15m',
                        'FORMAT': 'image/png',
                        'TRANSPARENT': true,
                        'VERSION': '1.3.0'
                    },
                    projection: 'EPSG:4326',
                    wrapX: false,
                    crossOrigin: 'anonymous'
                }),
                opacity: 0.8
            })
        ],
        view: new ol.View({
            center: [0, 0],
            projection: 'EPSG:4326',
            zoom: 3,
            minZoom: 1,
            maxZoom: 12,
            extent: [-180, -90, 180, 90],
            constrainOnlyCenter: true,
            enableRotation: false,
            smoothExtentConstraint: true,
            multiWorld: false
        }),
        controls: ol.control.defaults({
            zoom: true,
            attribution: false,
            rotate: false
        })
    });

    // Add layer controls
    addLayerControls();
    // Add date slider
    addDateSlider();

    // Add animation button handler
    document.getElementById('generate-animation').addEventListener('click', generateSmoothAnimation);
}

// Add function to create hide button
function createHideButton(container, controlName) {
    const hideButton = document.createElement('button');
    hideButton.className = 'hide-button';
    hideButton.innerHTML = '×';
    hideButton.title = 'Hide ' + controlName;
    
    hideButton.addEventListener('click', () => {
        container.classList.add('hidden');
        updateRestoreButton();
    });
    
    container.appendChild(hideButton);
}

// Add restore button
function addRestoreButton() {
    const restoreButton = document.createElement('button');
    restoreButton.className = 'restore-controls';
    restoreButton.textContent = 'Show Hidden Controls';
    restoreButton.style.display = 'none';
    
    restoreButton.addEventListener('click', () => {
        document.querySelectorAll('.layer-select, .reference-controls, .date-slider-container').forEach(el => {
            el.classList.remove('hidden');
        });
        updateRestoreButton();
    });
    
    document.body.appendChild(restoreButton);
    return restoreButton;
}

// Update restore button visibility
function updateRestoreButton() {
    const restoreButton = document.querySelector('.restore-controls');
    const hasHiddenControls = document.querySelectorAll('.hidden').length > 0;
    restoreButton.style.display = hasHiddenControls ? 'block' : 'none';
}

function addLayerControls() {
    const controlsDiv = document.getElementById('controls');
    
    // Add satellite layer selector
    const layerSelect = document.createElement('select');
    layerSelect.id = 'layer-select';
    layerSelect.className = 'layer-select';
    
    Object.entries(availableLayers).forEach(([name, value]) => {
        const option = document.createElement('option');
        option.value = value;
        option.text = name;
        layerSelect.appendChild(option);
    });
    
    layerSelect.onchange = (e) => {
        const layer = map.getLayers().getArray()[0];
        layer.getSource().updateParams({
            'LAYERS': e.target.value
        });
    };

    // Add reference layer toggles
    const referenceDiv = document.createElement('div');
    referenceDiv.className = 'reference-controls';
    
    const referenceLabels = {
        'Coastlines': 1,
        'Borders': 2,
        'Labels': 3
    };

    Object.entries(referenceLabels).forEach(([name, index]) => {
        const container = document.createElement('div');
        container.className = 'reference-toggle';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `toggle-${name.toLowerCase()}`;
        checkbox.checked = true;

        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = name;

        checkbox.onchange = (e) => {
            const layer = map.getLayers().getArray()[index];
            layer.setVisible(e.target.checked);
        };

        container.appendChild(checkbox);
        container.appendChild(label);
        referenceDiv.appendChild(container);
    });

    // Add hide buttons to controls
    createHideButton(layerSelect, 'Layer Selector');
    createHideButton(referenceDiv, 'Reference Controls');

    // Add controls in correct order
    controlsDiv.appendChild(layerSelect);
    controlsDiv.appendChild(referenceDiv);
    
    // Add restore button
    addRestoreButton();
}

function updateWMSLayer(date) {
    const layer = map.getLayers().getArray()[0];  // Get the satellite layer
    layer.getSource().updateParams({
        'TIME': date
    });
}

// Update available layers to match Worldview's most useful options
const availableLayers = {
    'VIIRS SNPP True Color': 'VIIRS_SNPP_CorrectedReflectance_TrueColor',
    'MODIS Aqua True Color': 'MODIS_Aqua_CorrectedReflectance_TrueColor',
    'MODIS Terra True Color': 'MODIS_Terra_CorrectedReflectance_TrueColor',
    'VIIRS NOAA-20 True Color': 'VIIRS_NOAA20_CorrectedReflectance_TrueColor',
    'VIIRS NOAA-21 True Color': 'VIIRS_NOAA21_CorrectedReflectance_TrueColor'
};

function addDateSlider() {
    const controlsDiv = document.getElementById('controls');
    
    // Create date slider container
    const dateSliderContainer = document.createElement('div');
    dateSliderContainer.className = 'date-slider-container';
    
    // Add hide button to date slider
    createHideButton(dateSliderContainer, 'Date Controls');
    
    // Create date display
    const dateDisplay = document.createElement('div');
    dateDisplay.className = 'date-display';
    
    // Create slider controls
    const sliderControls = document.createElement('div');
    sliderControls.className = 'slider-controls';
    
    // Add play/pause button
    const playButton = document.createElement('button');
    playButton.className = 'play-button';
    playButton.innerHTML = '▶';
    playButton.title = 'Play/Pause';
    
    // Add date slider
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.className = 'date-slider';
    
    // Calculate date range (past 5 years to today)
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Normalize to start of day
    const past5Years = new Date(today);
    past5Years.setFullYear(today.getFullYear() - 5);
    past5Years.setHours(0, 0, 0, 0); // Normalize to start of day
    
    const dayInMs = 24 * 60 * 60 * 1000; // One day in milliseconds
    
    // Set slider attributes
    slider.min = past5Years.getTime();
    slider.max = today.getTime();
    slider.value = today.getTime();
    slider.step = dayInMs;
    
    // Update date display
    function updateDateDisplay(date) {
        const options = { 
            weekday: 'short', 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        };
        dateDisplay.textContent = date.toLocaleDateString(undefined, options);
    }
    
    // Function to update everything based on a date
    function updateAll(date) {
        const normalizedDate = new Date(date);
        normalizedDate.setHours(0, 0, 0, 0); // Normalize to start of day
        slider.value = normalizedDate.getTime();
        updateDateDisplay(normalizedDate);
        updateWMSLayer(normalizedDate.toISOString().split('T')[0]);
    }
    
    // Initialize date display
    updateDateDisplay(new Date(parseInt(slider.value)));
    
    // Add event listeners
    slider.addEventListener('input', (e) => {
        const date = new Date(parseInt(e.target.value));
        updateAll(date);
    });
    
    // Animation variables
    let isPlaying = false;
    let animationInterval;
    
    // Cleanup function
    function cleanup() {
        if (animationInterval) {
            clearInterval(animationInterval);
            animationInterval = null;
        }
        isPlaying = false;
        playButton.innerHTML = '▶';
    }
    
    // Play/Pause functionality
    playButton.addEventListener('click', () => {
        isPlaying = !isPlaying;
        playButton.innerHTML = isPlaying ? '⏸' : '▶';
        
        if (isPlaying) {
            animationInterval = setInterval(() => {
                const currentValue = parseInt(slider.value);
                const nextValue = currentValue + dayInMs;
                
                if (nextValue > parseInt(slider.max)) {
                    slider.value = slider.min;
                    updateAll(new Date(parseInt(slider.min)));
                } else {
                    updateAll(new Date(nextValue));
                }
            }, 1000); // Update every second
        } else {
            cleanup();
        }
    });
    
    // Cleanup on container removal
    dateSliderContainer.addEventListener('remove', cleanup);
    
    // Add step backward/forward buttons
    const stepBackward = document.createElement('button');
    stepBackward.className = 'step-button';
    stepBackward.innerHTML = '←';
    stepBackward.title = 'Previous Day';
    stepBackward.onclick = () => {
        cleanup(); // Stop animation if running
        const currentValue = parseInt(slider.value);
        if (currentValue > parseInt(slider.min)) {
            const newDate = new Date(currentValue - dayInMs);
            updateAll(newDate);
        }
    };
    
    const stepForward = document.createElement('button');
    stepForward.className = 'step-button';
    stepForward.innerHTML = '→';
    stepForward.title = 'Next Day';
    stepForward.onclick = () => {
        cleanup(); // Stop animation if running
        const currentValue = parseInt(slider.value);
        if (currentValue < parseInt(slider.max)) {
            const newDate = new Date(currentValue + dayInMs);
            updateAll(newDate);
        }
    };
    
    // Assemble the controls
    sliderControls.appendChild(stepBackward);
    sliderControls.appendChild(playButton);
    sliderControls.appendChild(stepForward);
    sliderControls.appendChild(slider);
    
    dateSliderContainer.appendChild(dateDisplay);
    dateSliderContainer.appendChild(sliderControls);
    
    // Insert after reference controls
    const referenceControls = controlsDiv.querySelector('.reference-controls');
    controlsDiv.insertBefore(dateSliderContainer, referenceControls.nextSibling);
}

async function generateSmoothAnimation() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const extent = map.getView().calculateExtent();
    const size = map.getSize();
    
    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = 'block';
    loadingDiv.textContent = 'Generating smooth animation...';
    
    try {
        const response = await fetch('/generate-rife-animation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                bbox: extent,
                start_date: startDate,
                end_date: endDate,
                size: size,
                fps: 30
            })
        });
        
        if (!response.ok) throw new Error('Animation generation failed');
        
        const data = await response.json();
        
        // Display the video
        const videoPlayer = document.getElementById('video-player');
        const video = document.getElementById('interpolated-video');
        const source = video.querySelector('source');
        source.src = data.video_url;
        video.load();  // Important: reload the video with new source
        videoPlayer.style.display = 'block';
        
    } catch (error) {
        console.error('Failed to generate animation:', error);
        alert('Failed to generate animation');
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// Initialize map when the window loads
window.onload = () => {
    initMap();
}; 