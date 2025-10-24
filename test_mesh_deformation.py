"""Test script to validate mesh deformation code bugs"""
import numpy as np
from scipy.sparse import csr_matrix, lil_matrix

# Test 1: Sparse matrix assignment bug
print("="*70)
print("TEST 1: Sparse Matrix Assignment")
print("="*70)

# The buggy way (as in the original code)
n_constraints = 3
n = 10
print("\n[BUGGY APPROACH] Using csr_matrix with item assignment:")
constraint_matrix_buggy = csr_matrix((n_constraints, n))
print(f"Initial matrix:\n{constraint_matrix_buggy.toarray()}")

# Try to assign values (this is the bug!)
constrained_verts = np.array([2, 5, 8])
for i, idx in enumerate(constrained_verts):
    constraint_matrix_buggy[i, idx] = 1.0

print(f"After assignment:\n{constraint_matrix_buggy.toarray()}")
print(f"Sum of matrix: {constraint_matrix_buggy.sum()} (should be 3.0)")

# The correct way
print("\n[CORRECT APPROACH 1] Using lil_matrix:")
constraint_matrix_correct1 = lil_matrix((n_constraints, n))
for i, idx in enumerate(constrained_verts):
    constraint_matrix_correct1[i, idx] = 1.0
constraint_matrix_correct1 = constraint_matrix_correct1.tocsr()
print(f"Result:\n{constraint_matrix_correct1.toarray()}")
print(f"Sum of matrix: {constraint_matrix_correct1.sum()} (correct!)")

# Another correct way
print("\n[CORRECT APPROACH 2] Using proper constructor:")
row_indices = np.arange(n_constraints)
col_indices = constrained_verts
data = np.ones(n_constraints)
constraint_matrix_correct2 = csr_matrix((data, (row_indices, col_indices)),
                                        shape=(n_constraints, n))
print(f"Result:\n{constraint_matrix_correct2.toarray()}")
print(f"Sum of matrix: {constraint_matrix_correct2.sum()} (correct!)")

# Test 2: Check if scipy version matters
print("\n" + "="*70)
print("TEST 2: Scipy Version Check")
print("="*70)
import scipy
print(f"Scipy version: {scipy.__version__}")
print("Note: In some scipy versions, CSR assignment may work but is inefficient")

# Test 3: Numerical stability of normal equations
print("\n" + "="*70)
print("TEST 3: Normal Equations Numerical Stability")
print("="*70)
from scipy.sparse import random
from scipy.sparse.linalg import spsolve, lsqr

# Create a test system
np.random.seed(42)
m, n = 100, 50
A = random(m, n, density=0.1, format='csr')
x_true = np.random.randn(n)
b = A @ x_true + 0.01 * np.random.randn(m)  # Add noise

# Method 1: Normal equations (used in original code)
print("\n[BUGGY METHOD] Normal equations: A.T @ A @ x = A.T @ b")
try:
    x_normal = spsolve(A.T @ A, A.T @ b)
    error_normal = np.linalg.norm(x_normal - x_true)
    print(f"Error: {error_normal:.6f}")
except Exception as e:
    print(f"ERROR: {e}")

# Method 2: LSQR (better)
print("\n[BETTER METHOD] Using lsqr:")
x_lsqr = lsqr(A, b)[0]
error_lsqr = np.linalg.norm(x_lsqr - x_true)
print(f"Error: {error_lsqr:.6f}")

print(f"\nImprovement: {error_normal/error_lsqr:.2f}x (normal equations may be less stable)")

# Test 4: SVD rotation computation
print("\n" + "="*70)
print("TEST 4: SVD Rotation Computation")
print("="*70)

# Test the rotation computation logic
def test_rotation():
    # Create a simple test case
    # Original edge
    e = np.array([1.0, 0.0, 0.0])
    # Rotated edge (45 degrees around Z)
    theta = np.pi / 4
    e_prime = np.array([np.cos(theta), np.sin(theta), 0.0])

    # Build covariance matrix
    S = np.outer(e, e_prime)

    # SVD
    U, D, Vt = np.linalg.svd(S)
    R = Vt.T @ U.T

    print(f"Rotation matrix R:\n{R}")
    print(f"Determinant: {np.linalg.det(R):.6f} (should be 1.0)")

    # Check if it's a proper rotation
    is_orthogonal = np.allclose(R @ R.T, np.eye(3))
    print(f"Is orthogonal: {is_orthogonal}")

    # Apply rotation
    e_rotated = R @ e
    print(f"Original edge: {e}")
    print(f"Target edge: {e_prime}")
    print(f"Rotated edge: {e_rotated}")
    print(f"Error: {np.linalg.norm(e_rotated - e_prime):.6f}")

test_rotation()

print("\n" + "="*70)
print("SUMMARY OF BUGS FOUND")
print("="*70)
print("""
1. **CRITICAL BUG**: Sparse matrix assignment in laplacian_deformation()
   - Line: constraint_matrix[i, idx] = 1.0
   - Issue: CSR matrices don't support efficient item assignment
   - Fix: Use lil_matrix or proper constructor

2. **CRITICAL BUG**: Same issue in arap_deformation()
   - Line: C[i, idx] = 1.0
   - Issue: Same as above
   - Fix: Use lil_matrix or proper constructor

3. **NUMERICAL STABILITY**: Using normal equations A.T @ A
   - Issue: Can be numerically unstable, condition number squared
   - Fix: Use scipy.sparse.linalg.lsqr or other least squares solver

4. **POTENTIAL BUG**: Hardcoded file path
   - Line: igl.read_triangle_mesh("/mnt/user-data/uploads/dino.off")
   - Issue: Path may not exist in all environments
   - Fix: Make path a parameter or check existence

5. **EDGE CASE**: Empty neighbors in compute_cell_rotations
   - Currently handled with identity matrix (OK)
   - But could indicate mesh topology issues
""")
