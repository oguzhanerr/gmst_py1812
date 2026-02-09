# VSCode Environment Setup Guide for MST-GIS

This guide shows how to set up and test MST-GIS in VSCode on macOS.

---

## Quick Start

```bash
cd /Users/oz/Documents/gmst_py1812
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip first
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install Py1812
pip install ./github_Py1812/Py1812

# Install Jupyter kernel
python -m ipykernel install --user --name gmst_py1812
```

Then open VSCode and select the `.venv` interpreter.

---

---

## Detailed Setup

### Step 1: Create Python Virtual Environment

```bash
cd /Users/oz/Documents/gmst_py1812
python3 -m venv .venv
```

This creates a `.venv` folder with isolated Python environment.

### Step 2: Activate Virtual Environment

```bash
source .venv/bin/activate
```

You should see `(.venv)` prefix in your terminal.

### Step 3: Install Dependencies

#### Core Dependencies (required for batch processor)
```bash
pip install --upgrade pip
pip install numpy geojson psutil matplotlib
```

#### Development Tools (for notebooks and testing)
```bash
pip install jupyter jupyterlab ipython
```

#### Data Processing (required for notebooks)
```bash
pip install geopandas pandas rasterio requests shapely srtm
```

#### Radio Propagation Model (from local source)
```bash
pip install -e ./github_Py1812/Py1812
```

The `-e` flag means "editable" - it installs the local package.

### Step 4: Verify Installation

```bash
# Test point generation (no heavy dependencies)
python scripts/generate_receiver_points.py 0 0 5 --geojson --output /tmp/test.geojson

# Should output: ✅ GeoJSON saved to /tmp/test.geojson
```

---

## VSCode Configuration

### 1. Install Extensions

**Python Extension (Microsoft)**
- Open Extensions: `Cmd+Shift+X`
- Search: `Python`
- Click Install

**Jupyter Extension (Microsoft)**
- Search: `Jupyter`
- Click Install

**Optional but helpful:**
- Python Docstring Generator
- Pylance (language server)
- Remote - SSH (if working remotely)

### 2. Select Python Interpreter

- Press: `Cmd+Shift+P`
- Type: `Python: Select Interpreter`
- Choose: `./gmst_py1812/.venv/bin/python`

Or click the Python version in bottom-right corner of VSCode.

### 3. Configure Jupyter Kernel (for Notebooks)

After activating `.venv`:

```bash
python -m ipykernel install --user --name gmst_py1812
```

This makes the kernel available in VSCode's notebook interface.

### 4. Optional: Configure VSCode Settings

Create `.vscode/settings.json` in project root:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python"
  },
  "jupyter.kernels.preferred": "gmst_py1812"
}
```

---

## Testing in VSCode

### Test 1: Run Python Script

Create `tests/test_basic.py`:

```python
"""Test basic module imports and functionality."""

from gmst_py1812.propagation.point_generator import generate_phyllotaxis

# Generate 5 test points
points = generate_phyllotaxis(0, 0, 5, scale=1000)

print(f"✅ Generated {len(points)} points")
for i, (lat, lon) in enumerate(points, 1):
    print(f"   Point {i}: lat={lat:.6f}, lon={lon:.6f}")
```

Then in VSCode:
- Right-click the file
- Select "Run Python File"
- Output appears in Terminal

### Test 2: Run Entry Point Script

Open Terminal in VSCode (`Ctrl+`` or View → Terminal)

```bash
# Activate environment (should auto-activate if configured)
source .venv/bin/activate

# Test point generation
python scripts/generate_receiver_points.py 0 0 10 --geojson --output /tmp/points.geojson

# Expected output: ✅ GeoJSON saved to /tmp/points.geojson
```

### Test 3: Open and Run Notebook

1. File → Open File
2. Select `data/notebooks/read_geojson.ipynb`
3. VSCode should ask to select kernel
4. Choose: `gmst_py1812 (.venv)`
5. Run cells one by one (click play icon)

---

## Project Structure in VSCode

Recommended folder view:

```
MST-GIS (root)
├── 📁 .venv/              (virtual environment - ignore)
├── 📁 src/
│   └── 📁 gmst_py1812/        (main code)
├── 📁 data/               (all data files)
├── 📁 scripts/            (entry points)
├── 📁 tests/              (unit tests)
├── 📄 AGENTS.md
├── 📄 TESTING_REPORT.md
└── 📄 NOTEBOOK_IMPROVEMENTS.md
```

To hide `.venv` from explorer, add to `.vscode/settings.json`:

```json
{
  "files.exclude": {
    "**/.venv": true,
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

---

## Common Issues & Solutions

### Issue: "Python extension not found"

**Solution**: 
- Install Python extension from Microsoft
- Restart VSCode
- Press `Cmd+Shift+P` and run "Developer: Reload Window"

### Issue: "Module not found" errors

**Solution**:
1. Make sure `.venv` is activated: `source .venv/bin/activate`
2. Check interpreter is selected: `Cmd+Shift+P` → `Python: Select Interpreter`
3. Choose `./gmst_py1812/.venv/bin/python`

### Issue: Jupyter kernel not appearing

**Solution**:
```bash
# Install kernel
python -m ipykernel install --user --name gmst_py1812

# List kernels to verify
jupyter kernelspec list

# Should show: gmst_py1812  ~/.../gmst_py1812
```

### Issue: "Py1812 module not found"

**Solution**:
```bash
# Reinstall Py1812
pip install -e ./github_Py1812/Py1812

# Verify installation
python -c "import Py1812; print('OK')"
```

### Issue: "numpy/geojson not found"

**Solution**:
```bash
# Check if .venv is activated
which python
# Should show: /Users/oz/Documents/gmst_py1812/.venv/bin/python

# If not, activate:
source .venv/bin/activate

# Reinstall:
pip install numpy geojson
```

---

## Development Workflow

### 1. Start Your Day

```bash
cd /Users/oz/Documents/gmst_py1812
source .venv/bin/activate
code .
```

### 2. Make Changes

Edit files in VSCode, saving them automatically.

### 3. Test Modules

```bash
# Terminal in VSCode
python -m pytest tests/
```

Or run scripts:

```bash
python scripts/generate_receiver_points.py -h
```

### 4. Test Notebooks

Open `.ipynb` file in VSCode → Select kernel → Run cells

### 5. Check Progress

```bash
# See what's in data directories
ls -la data/output/geojson/
ls -la data/input/profiles/
```

---

## Dependency Summary

| Package | Purpose | Used By |
|---------|---------|---------|
| **numpy** | Numerical computing | batch_processor, profile_parser |
| **geojson** | GeoJSON I/O | batch_processor, geojson_builder |
| **psutil** | System monitoring | batch_processor |
| **matplotlib** | Plotting | notebooks (optional) |
| **geopandas** | Geospatial data | read_geojson.ipynb |
| **pandas** | Data manipulation | read_geojson.ipynb |
| **rasterio** | Raster I/O | mobile_get_input.ipynb |
| **requests** | HTTP requests | mobile_get_input.ipynb (API calls) |
| **shapely** | Geometry operations | mobile_get_input.ipynb |
| **srtm** | Elevation data | mobile_get_input.ipynb |
| **Py1812** | Radio propagation model | batch_processor |
| **jupyter** | Notebook server | Jupyter support |
| **jupyterlab** | Enhanced notebook UI | Alternative to jupyter notebook |
| **ipython** | Interactive Python | Better REPL experience |

---

## Next Steps After Setup

1. **Run basic test**: `python scripts/generate_receiver_points.py 0 0 5 --geojson --output /tmp/test.geojson`

2. **Open a notebook**: `data/notebooks/read_geojson.ipynb` (requires GeoJSON files first)

3. **Read documentation**: 
   - `AGENTS.md` - Quick reference
   - `docs/PROJECT_STRUCTURE_AND_ARCHITECTURE.md` - Complete guide
   - `TESTING_REPORT.md` - Test results

4. **Explore code**:
   - `src/gmst_py1812/propagation/point_generator.py` - Simple module to start
   - `src/gmst_py1812/propagation/batch_processor.py` - Main processing logic
   - `data/notebooks/` - Jupyter workflows

---

## Troubleshooting Checklist

- [ ] `.venv` folder exists in project root
- [ ] Terminal shows `(.venv)` prefix when activated
- [ ] `which python` shows path in `.venv`
- [ ] Python extension installed in VSCode
- [ ] Jupyter extension installed in VSCode
- [ ] Interpreter selected in VSCode
- [ ] `python scripts/generate_receiver_points.py 0 0 5 --geojson --output /tmp/test.geojson` works
- [ ] Notebooks can be opened in VSCode
- [ ] Jupyter kernel `gmst_py1812` appears in notebook kernel selector

---

## Quick Command Reference

```bash
# Activate environment
source .venv/bin/activate

# Install new package
pip install package_name

# List installed packages
pip list

# Generate requirements file
pip freeze > requirements.txt

# Run script
python scripts/generate_receiver_points.py 0 0 10 --geojson --output /tmp/points.geojson

# Start Jupyter
jupyter notebook

# Run tests
python -m pytest tests/

# Check Python version
python --version

# Deactivate environment
deactivate
```

---

**Setup complete!** You're ready to develop and test MST-GIS in VSCode. 🚀
