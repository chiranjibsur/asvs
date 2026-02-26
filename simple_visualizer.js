let scene, camera, renderer, controls;
let molecule, hotspotMesh;
let isRibbonView = false;  // Toggle between points and ribbon
let residueScores = [];  // Store per-residue scores for each frame

// Color map for hotspots (blue to red)
const colormap = new THREE.Color();
const colorScale = d3.scaleSequential(d3.interpolateRdBu).domain([0, 1]);

// Load protein structure (points or ribbons)
function loadProteinStructure(coords, isRibbonView) {
    if (isRibbonView) {
        // Ribbon view visualization
        const geometry = new THREE.BufferGeometry();
        const material = new THREE.LineBasicMaterial({ color: 0x00ff00 });
        const positions = new Float32Array(coords.flat());  // Flatten 3D coordinates
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        molecule = new THREE.LineSegments(geometry, material);
    } else {
        // Points visualization
        const geometry = new THREE.BufferGeometry();
        const material = new THREE.PointsMaterial({ size: 0.1, color: 0xffffff });
        const positions = new Float32Array(coords.flat());
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        molecule = new THREE.Points(geometry, material);
    }

    scene.add(molecule);
}

// Update per-residue hotspot coloring based on frame scores
function updateResidueColors(frameIdx, hotspots) {
    const colors = [];
    for (let i = 0; i < hotspots.length; i++) {
        const score = hotspots[i];
        colormap.set(colorScale(score));  // Apply the colormap for each residue score
        colors.push(colormap.getHexString());
    }

    // Apply colors to each residue
    molecule.material.color.setHex(colors[frameIdx]);
}

// Animate and render the scene
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// Initialize the scene
function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);

    // Camera position
    camera.position.z = 5;

    // Load protein structure
    loadProteinStructure(coords, isRibbonView);

    // Start the animation
    animate();
}

// Switch between points and ribbon views
function toggleView() {
    isRibbonView = !isRibbonView;
    scene.clear();
    loadProteinStructure(coords, isRibbonView);
    animate();
}

// Fetch frame data and update visualizations
function fetchFrameData(frameIdx) {
    fetch(`/api/trajectory/frame/${frameIdx}`)
        .then(response => response.json())
        .then(data => {
            const coords = data.coords;
            const hotspots = data.hotspots;
            updateResidueColors(frameIdx, hotspots); // Update colors based on hotspots
        });
}

// Initialize and start the viewer
init();
