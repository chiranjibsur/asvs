/**
 * Scientific Context Panel - Shared module for molecular visualizers
 * Provides consistent metric explanations across all visualization modes
 */

const METRIC_CONTEXTS = {
  hotspot: {
    icon: '#ff6666',
    title: 'Dynamic Hotspot',
    measures: 'Identifies residues undergoing statistically significant dynamic changes or transitions during the simulation.',
    biological: 'High hotspot values often indicate functionally important regions such as active sites, allosteric sites, or regions undergoing conformational changes. These residues may be critical for protein function.',
    interpretation: 'Peak values (red) suggest residues that are dynamically active and potentially involved in biological function. Low values (blue) indicate stable structural regions.'
  },
  anomaly: {
    icon: '#ff9933',
    title: 'Dynamic Anomaly',
    measures: 'Detects residues adopting statistically rare conformations using machine learning-based anomaly detection.',
    biological: 'Anomalous conformations may represent functional transition states, induced-fit binding events, or rare but biologically relevant conformational changes.',
    interpretation: 'High anomaly scores (red) indicate conformations that deviate significantly from the equilibrium ensemble. These may warrant further investigation for functional significance.'
  },
  rmsf: {
    icon: '#ffcc00',
    title: 'RMSF (Flexibility)',
    measures: 'Root Mean Square Fluctuation - quantifies time-averaged positional variance of each residue relative to the mean structure.',
    biological: 'Flexible regions (high RMSF) often correspond to loop regions, linkers, or functionally important dynamic elements. Rigid regions (low RMSF) typically form the structural core.',
    interpretation: 'Red indicates highly flexible residues, often in loops or termini. Blue indicates rigid residues, typically in alpha-helices or beta-sheets.'
  },
  tica: {
    icon: '#66ff66',
    title: 'tICA Importance',
    measures: 'Time-lagged Independent Component Analysis importance - identifies residues contributing to the slowest collective motions.',
    biological: 'Residues with high tICA importance drive large-scale conformational changes and may be involved in allosteric regulation, domain movements, or functional transitions.',
    interpretation: 'High values (red) identify residues at the core of collective dynamics. These are often allosteric hotspots or hinge regions.'
  }
};

/**
 * Update the Scientific Context Panel with the current metric's information
 * @param {string} metric - The metric key (hotspot, anomaly, rmsf, tica)
 */
function updateScientificContext(metric) {
  const ctx = METRIC_CONTEXTS[metric];
  if (!ctx) return;
  
  const contextSection = document.getElementById('currentMetricContext');
  if (!contextSection) return;
  
  contextSection.innerHTML = `
    <h4><span class="metric-icon" style="background:${ctx.icon};"></span>${ctx.title}</h4>
    <p><strong>What it measures:</strong> ${ctx.measures}</p>
    <p style="margin-top:8px;"><strong>Biological meaning:</strong> ${ctx.biological}</p>
    <p style="margin-top:8px;"><strong>Interpretation:</strong> ${ctx.interpretation}</p>
  `;
}

/**
 * Initialize the Scientific Context Panel with toggle functionality
 */
function initScientificContextPanel() {
  const toggle = document.getElementById('scientificContextToggle');
  const panel = document.getElementById('scientificContextPanel');
  const closeBtn = document.getElementById('closeContextPanel');
  const metricSelect = document.getElementById('metricSelect');
  
  if (toggle && panel) {
    toggle.addEventListener('click', () => {
      panel.classList.toggle('open');
      toggle.classList.toggle('open');
    });
  }
  
  if (closeBtn && panel && toggle) {
    closeBtn.addEventListener('click', () => {
      panel.classList.remove('open');
      toggle.classList.remove('open');
    });
  }
  
  if (metricSelect) {
    metricSelect.addEventListener('change', (e) => {
      updateScientificContext(e.target.value);
    });
  }
}

/**
 * Generate the Metric Definitions HTML content
 * @returns {string} HTML content for metric definitions
 */
function getMetricDefinitionsHTML() {
  return Object.entries(METRIC_CONTEXTS).map(([key, ctx]) => {
    if (key === 'hotspot') return ''; // Skip hotspot as it's the default shown in currentMetricContext
    return `<p style="margin-top:6px;"><strong style="color:${ctx.icon};">${ctx.title}:</strong> ${ctx.measures}</p>`;
  }).join('');
}

// Export for use in other modules
window.ScientificContext = {
  METRIC_CONTEXTS,
  updateScientificContext,
  initScientificContextPanel,
  getMetricDefinitionsHTML
};
