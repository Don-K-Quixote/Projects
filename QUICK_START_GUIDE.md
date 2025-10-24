# Quick Start Guide: Using the Mesh Deformation Code

## Problem Solved

The original code had hardcoded paths that didn't work on local systems:
- ❌ Hardcoded mesh path: `/mnt/user-data/uploads/dino.off`
- ❌ Hardcoded output path: `/mnt/user-data/outputs/`

**Now fixed!** ✅ The code automatically finds your mesh file and saves to your current directory.

---

## Usage Options

### Option 1: Place dino.off in the Same Folder (Easiest!)

1. Put `dino.off` in the same folder as `mesh_deformation_FIXED.py`
2. Run the script:

```python
# In Python/Jupyter
from mesh_deformation_FIXED import main
main()
```

Or from command line:
```bash
python mesh_deformation_FIXED.py
```

**That's it!** The code will:
- ✅ Automatically find `dino.off` in the current directory
- ✅ Save output images to the current directory
- ✅ Create 5 PNG files with deformation results

---

### Option 2: Specify Custom Paths

If your mesh file is elsewhere, specify the path:

```python
from mesh_deformation_FIXED import main

# Use your own mesh file
main(mesh_path='path/to/your/mesh.off')

# Or specify both mesh and output directory
main(mesh_path='data/bunny.obj', output_dir='results/')
```

---

### Option 3: Use Different Mesh Files

The code works with any triangle mesh in these formats:
- `.off` - Object File Format
- `.ply` - Polygon File Format
- `.obj` - Wavefront OBJ
- `.stl` - Stereolithography

```python
from mesh_deformation_FIXED import main

# Use a bunny mesh
main(mesh_path='bunny.ply')

# Use a sphere mesh
main(mesh_path='sphere.obj')

# Specify output directory
main(mesh_path='models/dragon.stl', output_dir='output/')
```

---

## What the Code Does

1. **Loads your mesh** - Finds and loads the mesh file
2. **Selects constraints** - Automatically picks:
   - Anchors: Bottom vertices (fixed in place)
   - Handles: Top vertex (will be moved)
3. **Laplacian Deformation** - Fast, preserves local geometry
4. **ARAP Deformation** - Slower, more natural, preserves rigidity
5. **Saves 5 images**:
   - `Q2_original_mesh.png` - Your original mesh
   - `Q2_laplacian_result.png` - Laplacian deformed mesh
   - `Q2_arap_result.png` - ARAP deformed mesh
   - `Q2_convergence.png` - ARAP convergence plot
   - `Q2_comparison.png` - Side-by-side comparison

---

## Troubleshooting

### Error: "Mesh file not found"

**Current directory check:**
```python
import os
print("Current directory:", os.getcwd())
print("Files here:", os.listdir('.'))
```

**Solutions:**
1. Make sure `dino.off` is in the current directory
2. Or specify the full path:
   ```python
   main(mesh_path='/full/path/to/dino.off')
   ```

### Error: "No module named 'open3d'"

Install dependencies:
```bash
pip install open3d numpy scipy matplotlib gpytoolbox
```

### Where are my output files?

Check the output at the start:
```
Output directory: /your/current/directory
```

Or specify where to save:
```python
main(output_dir='my_results/')
```

---

## Examples

### Example 1: Basic Usage (Same Folder)

**File structure:**
```
my_project/
  ├── mesh_deformation_FIXED.py
  └── dino.off
```

**Code:**
```python
from mesh_deformation_FIXED import main
main()
```

**Result:** 5 PNG files saved in `my_project/`

---

### Example 2: Custom Paths

**File structure:**
```
my_project/
  ├── mesh_deformation_FIXED.py
  ├── data/
  │   └── bunny.ply
  └── results/
```

**Code:**
```python
from mesh_deformation_FIXED import main
main(mesh_path='data/bunny.ply', output_dir='results/')
```

**Result:** 5 PNG files saved in `my_project/results/`

---

### Example 3: Using in Jupyter Notebook

```python
# Cell 1: Import and run
from mesh_deformation_FIXED import main

# Make sure dino.off is in the same folder as the notebook
main()

# Cell 2: View results
from IPython.display import Image
Image('Q2_comparison.png')
```

---

### Example 4: Custom Deformation

You can also use the functions directly for custom deformations:

```python
import open3d as o3d
import numpy as np
from mesh_deformation_FIXED import laplacian_deformation, arap_deformation

# Load your mesh
mesh = o3d.io.read_triangle_mesh('your_mesh.off')
V = np.asarray(mesh.vertices)
F = np.asarray(mesh.triangles)

# Define your own constraints
anchors = np.array([0, 1, 2, 3])  # Fix these vertices
handles = np.array([100, 101])     # Move these vertices
handle_targets = V[handles] + [0.5, 0, 0]  # Move right by 0.5

# Run deformation
V_deformed = arap_deformation(V, F, anchors, handles, handle_targets)

# Save result
deformed_mesh = o3d.geometry.TriangleMesh()
deformed_mesh.vertices = o3d.utility.Vector3dVector(V_deformed)
deformed_mesh.triangles = o3d.utility.Vector3iVector(F)
o3d.io.write_triangle_mesh('deformed.ply', deformed_mesh)
```

---

## Common File Locations Checked

The code automatically searches for `dino.off` in these locations (in order):

1. ✅ `dino.off` - Current directory
2. ✅ `./dino.off` - Explicit current directory
3. ✅ `data/dino.off` - Data subdirectory
4. ✅ `../dino.off` - Parent directory
5. ✅ `/mnt/user-data/uploads/dino.off` - Original path

**So just put your file in the current directory and it will work!**

---

## Output Files Explained

### 1. Q2_original_mesh.png
- Shows your original mesh
- Red dots = Anchors (fixed vertices)
- Blue squares = Handles (vertices that will move)
- Green triangles = Target positions

### 2. Q2_laplacian_result.png
- Mesh after Laplacian deformation
- Fast method, preserves local geometry
- May not preserve rigidity perfectly

### 3. Q2_arap_result.png
- Mesh after ARAP deformation
- Slower method, better quality
- Preserves local rigidity (more natural)

### 4. Q2_convergence.png
- Shows how ARAP converges
- Y-axis (log scale): Change in vertex positions
- X-axis: Iteration number
- Should decrease exponentially

### 5. Q2_comparison.png
- Side-by-side: Original | Laplacian | ARAP
- Easy visual comparison of methods

---

## Summary

**What changed:**
- ✅ No more hardcoded paths!
- ✅ Works with local files
- ✅ Saves to current directory by default
- ✅ Can customize paths if needed

**To use:**
1. Put `dino.off` in the same folder
2. Run `main()`
3. Get 5 result images

**Simple!** 🎉

---

## Need Help?

1. Check file exists: `os.path.exists('dino.off')`
2. Check current directory: `os.getcwd()`
3. List files: `os.listdir('.')`
4. Specify full path: `main(mesh_path='/full/path/to/file.off')`

For more details, see `README_MESH_DEFORMATION.md`
