# ML Pipeline Data Requirements

## Quick Reference

This directory contains JSON files with metrics from the ML pipeline.

### Required Files

1. **anomaly_residue.json** - Dynamic anomaly scores per frame
2. **tica_importance.json** - tICA importance (static)
3. **rmsf_residue.json** - RMSF flexibility (static)
4. **hotspots_residue.json** - Original hotspot data (optional)

### Data Format

All residue indices should be **0-based strings**, and all metric values should be **normalized to [0, 1]**.

#### Frame-Dependent Metrics (anomaly, hotspots)
```json
{
  "0": {"0": 0.123, "1": 0.456, ...},
  "1": {"0": 0.234, "1": 0.567, ...}
}
```

#### Static Metrics (RMSF, tICA)
```json
{
  "min": <raw_min_value>,
  "max": <raw_max_value>,
  "normalized": {
    "0": 0.123,
    "1": 0.456,
    ...
  }
}
```

### Integration

The current files are **synthetic sample data**. Replace them with outputs from:
**https://github.com/siya7205/ensemble-anomaly-maps**

For detailed integration instructions, see: `../ML_PIPELINE_INTEGRATION.md`

### Environment Variables

You can specify custom paths:
```bash
export ASVS_ANOMALY=/path/to/anomaly_residue.json
export ASVS_TICA=/path/to/tica_importance.json
export ASVS_RMSF=/path/to/rmsf_residue.json
export ASVS_HOTSPOTS=/path/to/hotspots_residue.json
```
