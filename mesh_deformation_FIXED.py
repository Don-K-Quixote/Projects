"""
Q2: 3D Mesh Deformation - CORRECTED VERSION
Implements Laplacian Deformation and ARAP (As-Rigid-As-Possible) Deformation

This version fixes all critical bugs from the original implementation.

Changes:
- Fixed sparse matrix construction (Bug #1, #2)
- Improved numerical stability using lsqr (Bug #3)
- Fixed rotation reflection handling (Bug #4)
- Added file existence check (Bug #5)
- Improved dense matrix conversion efficiency (Warning #1)
- Added relative convergence criterion (Warning #2)
"""

import igl
import numpy as np
from gpytoolbox import cotangent_laplacian
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.sparse import csr_matrix, lil_matrix, vstack, hstack, diags
from scipy.sparse.linalg import spsolve, lsqr
import time
import os

# ============================================================================
# PART 1: LAPLACIAN DEFORMATION (FIXED)
# ============================================================================

def laplacian_deformation(V, F, anchors, handles, handle_targets, iterations=1):
    """
    Laplacian deformation of a mesh.

    Method: Minimizes the Laplacian energy while satisfying hard constraints.
    Energy: E = ||L(V' - V)||^2

    Args:
        V: Vertices (n x 3)
        F: Faces (m x 3)
        anchors: Indices of fixed vertices
        handles: Indices of handle vertices to move
        handle_targets: Target positions for handles (k x 3)
        iterations: Number of iterations (1 for standard Laplacian)

    Returns:
        V_new: Deformed vertices
    """
    print("="*70)
    print("LAPLACIAN DEFORMATION")
    print("="*70)

    n = V.shape[0]  # Number of vertices

    # Step 1: Compute cotangent Laplacian matrix
    print("\n[Step 1] Computing cotangent Laplacian matrix...")
    L = cotangent_laplacian(V, F)
    print(f"  Laplacian matrix shape: {L.shape}")
    print(f"  Matrix type: {type(L)}")

    # Step 2: Compute differential coordinates (Laplacian coordinates)
    print("\n[Step 2] Computing differential coordinates...")
    delta = L @ V  # Laplacian coordinates: δᵢ = Σ wᵢⱼ(vᵢ - vⱼ)
    print(f"  Delta shape: {delta.shape}")
    print(f"  Delta represents the local geometry of the mesh")

    # Step 3: Set up constraints
    print("\n[Step 3] Setting up constraints...")
    constrained_verts = np.concatenate([anchors, handles])
    print(f"  Number of anchors (fixed): {len(anchors)}")
    print(f"  Number of handles (moved): {len(handles)}")
    print(f"  Total constrained vertices: {len(constrained_verts)}")

    # FIX #1: Create constraint matrix correctly using lil_matrix
    n_constraints = len(constrained_verts)
    constraint_matrix = lil_matrix((n_constraints, n))

    # Set rows for constrained vertices
    for i, idx in enumerate(constrained_verts):
        constraint_matrix[i, idx] = 1.0

    # Convert to CSR for efficient operations
    constraint_matrix = constraint_matrix.tocsr()

    # Step 4: Build the linear system
    print("\n[Step 4] Building linear system...")
    # Stack Laplacian and constraints: [L; C] @ V' = [δ; b]
    A = vstack([L, constraint_matrix])

    print(f"  System matrix A shape: {A.shape}")
    print(f"  A is formed by stacking:")
    print(f"    - Laplacian matrix L ({L.shape[0]} x {L.shape[1]})")
    print(f"    - Constraint matrix C ({constraint_matrix.shape[0]} x {constraint_matrix.shape[1]})")

    # Step 5: Solve for each coordinate separately
    print("\n[Step 5] Solving linear system for new vertex positions...")
    V_new = np.zeros_like(V)

    for coord in range(3):  # x, y, z
        # Right-hand side
        b = np.zeros(A.shape[0])

        # Laplacian energy preservation
        b[:n] = delta[:, coord]

        # Hard constraints
        b[n:n+len(anchors)] = V[anchors, coord]  # Anchors stay in place
        b[n+len(anchors):] = handle_targets[:, coord]  # Handles move to targets

        # FIX #3: Use lsqr for better numerical stability instead of normal equations
        # Old (unstable): V_new[:, coord] = spsolve(A.T @ A, A.T @ b)
        V_new[:, coord] = lsqr(A, b)[0]

    print(f"  ✓ Solved for all coordinates")

    # Step 6: Compute deformation statistics
    print("\n[Step 6] Deformation statistics:")
    displacement = np.linalg.norm(V_new - V, axis=1)
    print(f"  Average displacement: {displacement.mean():.6f}")
    print(f"  Max displacement: {displacement.max():.6f}")
    print(f"  Vertices moved: {np.sum(displacement > 1e-6)}")

    return V_new


# ============================================================================
# PART 2: ARAP (AS-RIGID-AS-POSSIBLE) DEFORMATION (FIXED)
# ============================================================================

def compute_cell_rotations(V, V_prime, F, L):
    """
    Compute optimal rotation for each vertex (local step in ARAP).

    For each vertex i, find rotation Rᵢ that best aligns:
        Σⱼ wᵢⱼ(vᵢ - vⱼ) with Σⱼ wᵢⱼ(v'ᵢ - v'ⱼ)

    This is solved using SVD: S = Σⱼ wᵢⱼ(vᵢ - vⱼ)(v'ᵢ - v'ⱼ)ᵀ
    Then R = V @ Uᵀ where S = U @ D @ Vᵀ
    """
    n = V.shape[0]
    rotations = np.zeros((n, 3, 3))

    # FIX #W1: Work with sparse matrix more efficiently
    # Instead of converting entire matrix to dense, use CSR properties
    L_csr = L.tocsr() if not isinstance(L, csr_matrix) else L

    for i in range(n):
        # Get neighbors using CSR structure
        start = L_csr.indptr[i]
        end = L_csr.indptr[i+1]
        neighbors = L_csr.indices[start:end]
        weights = -L_csr.data[start:end]  # Negate because L[i,j] = -w_ij

        # Filter out the diagonal entry (where j == i)
        mask = neighbors != i
        neighbors = neighbors[mask]
        weights = weights[mask]

        if len(neighbors) == 0:
            rotations[i] = np.eye(3)
            continue

        # Build covariance matrix
        S = np.zeros((3, 3))
        for j, w_ij in zip(neighbors, weights):
            # Edge vectors
            e_ij = V[i] - V[j]  # Original edge
            e_ij_prime = V_prime[i] - V_prime[j]  # Deformed edge

            # Accumulate: S = Σ wᵢⱼ(vᵢ - vⱼ)(v'ᵢ - v'ⱼ)ᵀ
            S += w_ij * np.outer(e_ij, e_ij_prime)

        # SVD: S = U @ D @ Vᵀ
        U, s, Vt = np.linalg.svd(S)

        # FIX #4: Handle reflection properly
        # Rotation: R = V @ Uᵀ
        R = Vt.T @ U.T

        # Ensure proper rotation (det(R) = 1), not reflection
        if np.linalg.det(R) < 0:
            # Flip the sign of the last row of Vt
            Vt_corrected = Vt.copy()
            Vt_corrected[-1, :] *= -1
            R = Vt_corrected.T @ U.T

        rotations[i] = R

    return rotations


def arap_deformation(V, F, anchors, handles, handle_targets, max_iterations=10, tolerance=1e-4):
    """
    ARAP (As-Rigid-As-Possible) deformation of a mesh.

    Method: Local-global optimization
    1. Local step: Compute optimal rotation for each vertex
    2. Global step: Solve for vertex positions given rotations
    3. Iterate until convergence

    Energy: E = Σᵢ Σⱼ wᵢⱼ ||(v'ᵢ - v'ⱼ) - Rᵢ(vᵢ - vⱼ)||²

    Args:
        V: Vertices (n x 3)
        F: Faces (m x 3)
        anchors: Indices of fixed vertices
        handles: Indices of handle vertices to move
        handle_targets: Target positions for handles (k x 3)
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance

    Returns:
        V_new: Deformed vertices
        convergence_history: Energy at each iteration
    """
    print("="*70)
    print("ARAP (AS-RIGID-AS-POSSIBLE) DEFORMATION")
    print("="*70)

    n = V.shape[0]

    # Step 1: Compute cotangent Laplacian
    print("\n[Step 1] Computing cotangent Laplacian matrix...")
    L = cotangent_laplacian(V, F)
    print(f"  Laplacian matrix shape: {L.shape}")

    # Step 2: Initialize with Laplacian deformation
    print("\n[Step 2] Initializing with Laplacian deformation...")
    V_prime = laplacian_deformation(V, F, anchors, handles, handle_targets, iterations=1)
    print("  ✓ Initial guess obtained")

    # Step 3: Set up constraints
    print("\n[Step 3] Setting up ARAP constraints...")
    constrained_verts = np.concatenate([anchors, handles])
    print(f"  Constrained vertices: {len(constrained_verts)}")

    # FIX #2: Create constraint matrix correctly using lil_matrix
    n_constraints = len(constrained_verts)
    C = lil_matrix((n_constraints, n))
    for i, idx in enumerate(constrained_verts):
        C[i, idx] = 1.0
    C = C.tocsr()  # Convert to CSR

    # Step 4: Iterative optimization
    print("\n[Step 4] Starting ARAP iterations...")
    print(f"  Max iterations: {max_iterations}")
    print(f"  Convergence tolerance: {tolerance}")

    convergence_history = []

    # Pre-convert L to CSR for efficiency
    L_csr = L.tocsr() if not isinstance(L, csr_matrix) else L

    for iteration in range(max_iterations):
        iter_start = time.time()

        # LOCAL STEP: Compute optimal rotations
        rotations = compute_cell_rotations(V, V_prime, F, L)

        # GLOBAL STEP: Solve for new positions
        # Build right-hand side using rotations
        b_local = np.zeros((n, 3))

        for i in range(n):
            # Use CSR structure to get neighbors
            start = L_csr.indptr[i]
            end = L_csr.indptr[i+1]
            neighbors = L_csr.indices[start:end]
            weights = -L_csr.data[start:end]

            # Filter diagonal
            mask = neighbors != i
            neighbors = neighbors[mask]
            weights = weights[mask]

            for j, w_ij in zip(neighbors, weights):
                # Rotated edge: Rᵢ(vᵢ - vⱼ)
                e_ij = V[i] - V[j]
                rotated_edge = rotations[i] @ e_ij
                b_local[i] += w_ij * rotated_edge

        # Build system matrix
        A = vstack([L, C])

        # Solve for each coordinate
        V_new = np.zeros_like(V)
        for coord in range(3):
            b = np.zeros(A.shape[0])
            b[:n] = b_local[:, coord]
            b[n:n+len(anchors)] = V[anchors, coord]
            b[n+len(anchors):] = handle_targets[:, coord]

            # FIX #3: Use lsqr for better numerical stability
            V_new[:, coord] = lsqr(A, b)[0]

        # FIX #W2: Check convergence using relative change
        change = np.linalg.norm(V_new - V_prime)
        relative_change = change / (np.linalg.norm(V_prime) + 1e-10)
        convergence_history.append(change)

        iter_time = time.time() - iter_start

        print(f"  Iteration {iteration+1:2d}: change = {change:.6f}, "
              f"relative = {relative_change:.2e}, time = {iter_time:.3f}s")

        if relative_change < tolerance:
            print(f"  ✓ Converged after {iteration+1} iterations!")
            break

        V_prime = V_new

    # Step 5: Final statistics
    print("\n[Step 5] Final deformation statistics:")
    displacement = np.linalg.norm(V_new - V, axis=1)
    print(f"  Average displacement: {displacement.mean():.6f}")
    print(f"  Max displacement: {displacement.max():.6f}")
    print(f"  Vertices moved: {np.sum(displacement > 1e-6)}")

    return V_new, convergence_history


# ============================================================================
# VISUALIZATION FUNCTIONS (unchanged)
# ============================================================================

def plot_mesh(V, F, title="Mesh", anchors=None, handles=None, handle_targets=None,
              elev=20, azim=45, color='lightblue', alpha=0.7):
    """Plot a 3D mesh with optional constraint markers."""
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot mesh surface
    ax.plot_trisurf(V[:, 0], V[:, 1], V[:, 2],
                    triangles=F, color=color, alpha=alpha,
                    edgecolor='gray', linewidth=0.1)

    # Plot anchors (fixed points)
    if anchors is not None and len(anchors) > 0:
        ax.scatter(V[anchors, 0], V[anchors, 1], V[anchors, 2],
                  c='red', s=100, marker='o', label='Anchors (Fixed)',
                  edgecolors='black', linewidths=2)

    # Plot handles (points to move)
    if handles is not None and len(handles) > 0:
        ax.scatter(V[handles, 0], V[handles, 1], V[handles, 2],
                  c='blue', s=100, marker='s', label='Handles (Original)',
                  edgecolors='black', linewidths=2)

    # Plot handle targets
    if handle_targets is not None and len(handle_targets) > 0:
        ax.scatter(handle_targets[:, 0], handle_targets[:, 1], handle_targets[:, 2],
                  c='green', s=100, marker='^', label='Handle Targets',
                  edgecolors='black', linewidths=2)

        # Draw arrows from handles to targets
        if handles is not None:
            for i, h in enumerate(handles):
                ax.plot([V[h, 0], handle_targets[i, 0]],
                       [V[h, 1], handle_targets[i, 1]],
                       [V[h, 2], handle_targets[i, 2]],
                       'g--', linewidth=2, alpha=0.6)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.view_init(elev=elev, azim=azim)

    if anchors is not None or handles is not None:
        ax.legend(loc='upper right')

    # Equal aspect ratio
    max_range = np.array([V[:, 0].max()-V[:, 0].min(),
                         V[:, 1].max()-V[:, 1].min(),
                         V[:, 2].max()-V[:, 2].min()]).max() / 2.0
    mid_x = (V[:, 0].max()+V[:, 0].min()) * 0.5
    mid_y = (V[:, 1].max()+V[:, 1].min()) * 0.5
    mid_z = (V[:, 2].max()+V[:, 2].min()) * 0.5
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)

    return fig, ax


def visualize_comparison(V_original, V_laplacian, V_arap, F,
                        anchors, handles, handle_targets):
    """Create side-by-side comparison of original, Laplacian, and ARAP."""
    fig = plt.figure(figsize=(18, 6))

    # Original mesh
    ax1 = fig.add_subplot(131, projection='3d')
    ax1.plot_trisurf(V_original[:, 0], V_original[:, 1], V_original[:, 2],
                     triangles=F, color='lightblue', alpha=0.7,
                     edgecolor='gray', linewidth=0.1)
    ax1.scatter(V_original[anchors, 0], V_original[anchors, 1], V_original[anchors, 2],
               c='red', s=80, marker='o', label='Anchors')
    ax1.scatter(V_original[handles, 0], V_original[handles, 1], V_original[handles, 2],
               c='blue', s=80, marker='s', label='Handles')
    ax1.set_title('Original Mesh', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.view_init(elev=20, azim=45)

    # Laplacian deformation
    ax2 = fig.add_subplot(132, projection='3d')
    ax2.plot_trisurf(V_laplacian[:, 0], V_laplacian[:, 1], V_laplacian[:, 2],
                     triangles=F, color='lightcoral', alpha=0.7,
                     edgecolor='gray', linewidth=0.1)
    ax2.scatter(V_laplacian[anchors, 0], V_laplacian[anchors, 1], V_laplacian[anchors, 2],
               c='red', s=80, marker='o')
    ax2.scatter(handle_targets[:, 0], handle_targets[:, 1], handle_targets[:, 2],
               c='green', s=80, marker='^', label='Targets')
    ax2.set_title('Laplacian Deformation', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.view_init(elev=20, azim=45)

    # ARAP deformation
    ax3 = fig.add_subplot(133, projection='3d')
    ax3.plot_trisurf(V_arap[:, 0], V_arap[:, 1], V_arap[:, 2],
                     triangles=F, color='lightgreen', alpha=0.7,
                     edgecolor='gray', linewidth=0.1)
    ax3.scatter(V_arap[anchors, 0], V_arap[anchors, 1], V_arap[anchors, 2],
               c='red', s=80, marker='o')
    ax3.scatter(handle_targets[:, 0], handle_targets[:, 1], handle_targets[:, 2],
               c='green', s=80, marker='^', label='Targets')
    ax3.set_title('ARAP Deformation', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.view_init(elev=20, azim=45)

    plt.tight_layout()
    return fig


def plot_convergence(convergence_history):
    """Plot ARAP convergence history."""
    fig, ax = plt.subplots(figsize=(10, 6))

    iterations = range(1, len(convergence_history) + 1)
    ax.plot(iterations, convergence_history, 'o-', linewidth=2, markersize=8)
    ax.set_xlabel('Iteration', fontsize=12)
    ax.set_ylabel('Change in Vertex Positions', fontsize=12)
    ax.set_title('ARAP Convergence History', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')

    return fig


# ============================================================================
# MAIN EXECUTION (with file check)
# ============================================================================

def main():
    print("="*70)
    print("3D MESH DEFORMATION: LAPLACIAN vs ARAP (FIXED VERSION)")
    print("="*70)

    # Step 1: Load mesh
    print("\n[STEP 1] Loading mesh...")

    # FIX #5: Check if file exists
    mesh_path = "/mnt/user-data/uploads/dino.off"
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    V, F = igl.read_triangle_mesh(mesh_path)
    print(f"✓ Loaded mesh: {V.shape[0]} vertices, {F.shape[0]} faces")
    print(f"  Vertex coordinates range:")
    print(f"    X: [{V[:, 0].min():.4f}, {V[:, 0].max():.4f}]")
    print(f"    Y: [{V[:, 1].min():.4f}, {V[:, 1].max():.4f}]")
    print(f"    Z: [{V[:, 2].min():.4f}, {V[:, 2].max():.4f}]")

    # Step 2: Select constraint vertices
    print("\n[STEP 2] Selecting constraint vertices...")

    # Strategy: Fix bottom vertices (anchors) and move top vertex (handle)
    z_min = V[:, 2].min()
    z_max = V[:, 2].max()

    # Anchors: vertices at the bottom (feet)
    anchors = np.where(V[:, 2] < z_min + 0.05)[0]
    print(f"  Selected {len(anchors)} anchor vertices at bottom")

    # Handle: vertex at the top (head/tail)
    handle_idx = np.argmax(V[:, 2])  # Highest point
    handles = np.array([handle_idx])
    print(f"  Selected handle vertex at index {handle_idx}")
    print(f"  Handle original position: {V[handle_idx]}")

    # Target: Move handle upward and to the right
    handle_targets = V[handles].copy()
    handle_targets[:, 0] += 0.1  # Move right (X)
    handle_targets[:, 2] += 0.15  # Move up (Z)
    print(f"  Handle target position: {handle_targets[0]}")

    # Step 3: Visualize original mesh with constraints
    print("\n[STEP 3] Visualizing original mesh...")
    fig1, _ = plot_mesh(V, F, "Original Mesh with Constraints",
                        anchors=anchors, handles=handles,
                        handle_targets=handle_targets)
    plt.savefig('/mnt/user-data/outputs/Q2_original_mesh.png', dpi=150, bbox_inches='tight')
    print("  ✓ Saved: Q2_original_mesh.png")
    plt.close()

    # Step 4: Laplacian deformation
    print("\n[STEP 4] Performing Laplacian deformation...")
    start_time = time.time()
    V_laplacian = laplacian_deformation(V, F, anchors, handles, handle_targets)
    laplacian_time = time.time() - start_time
    print(f"\n✓ Laplacian deformation completed in {laplacian_time:.3f} seconds")

    # Visualize Laplacian result
    fig2, _ = plot_mesh(V_laplacian, F, "Laplacian Deformation Result",
                        anchors=anchors, handles=handles,
                        handle_targets=handle_targets, color='lightcoral')
    plt.savefig('/mnt/user-data/outputs/Q2_laplacian_result.png', dpi=150, bbox_inches='tight')
    print("  ✓ Saved: Q2_laplacian_result.png")
    plt.close()

    # Step 5: ARAP deformation
    print("\n[STEP 5] Performing ARAP deformation...")
    start_time = time.time()
    V_arap, convergence = arap_deformation(V, F, anchors, handles, handle_targets,
                                          max_iterations=10, tolerance=1e-4)
    arap_time = time.time() - start_time
    print(f"\n✓ ARAP deformation completed in {arap_time:.3f} seconds")

    # Visualize ARAP result
    fig3, _ = plot_mesh(V_arap, F, "ARAP Deformation Result",
                        anchors=anchors, handles=handles,
                        handle_targets=handle_targets, color='lightgreen')
    plt.savefig('/mnt/user-data/outputs/Q2_arap_result.png', dpi=150, bbox_inches='tight')
    print("  ✓ Saved: Q2_arap_result.png")
    plt.close()

    # Step 6: Plot convergence
    print("\n[STEP 6] Plotting convergence history...")
    fig4 = plot_convergence(convergence)
    plt.savefig('/mnt/user-data/outputs/Q2_convergence.png', dpi=150, bbox_inches='tight')
    print("  ✓ Saved: Q2_convergence.png")
    plt.close()

    # Step 7: Side-by-side comparison
    print("\n[STEP 7] Creating comparison visualization...")
    fig5 = visualize_comparison(V, V_laplacian, V_arap, F,
                               anchors, handles, handle_targets)
    plt.savefig('/mnt/user-data/outputs/Q2_comparison.png', dpi=150, bbox_inches='tight')
    print("  ✓ Saved: Q2_comparison.png")
    plt.close()

    # Step 8: Compute quality metrics
    print("\n[STEP 8] Computing quality metrics...")

    # Displacement statistics
    disp_laplacian = np.linalg.norm(V_laplacian - V, axis=1)
    disp_arap = np.linalg.norm(V_arap - V, axis=1)

    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    print(f"\nTime Performance:")
    print(f"  Laplacian: {laplacian_time:.3f} seconds")
    print(f"  ARAP:      {arap_time:.3f} seconds")
    print(f"  Speedup:   {arap_time/laplacian_time:.2f}x slower (ARAP)")

    print(f"\nDisplacement Statistics:")
    print(f"  Laplacian - Mean: {disp_laplacian.mean():.6f}, Max: {disp_laplacian.max():.6f}")
    print(f"  ARAP      - Mean: {disp_arap.mean():.6f}, Max: {disp_arap.max():.6f}")

    print(f"\nHandle Accuracy (distance to target):")
    handle_error_lap = np.linalg.norm(V_laplacian[handles] - handle_targets, axis=1)
    handle_error_arap = np.linalg.norm(V_arap[handles] - handle_targets, axis=1)
    print(f"  Laplacian: {handle_error_lap[0]:.6f}")
    print(f"  ARAP:      {handle_error_arap[0]:.6f}")

    print(f"\nConvergence:")
    print(f"  ARAP iterations: {len(convergence)}")
    print(f"  Final change: {convergence[-1]:.8f}")

    print("\n" + "="*70)
    print("PROCESSING COMPLETE!")
    print("="*70)
    print("\nGenerated files:")
    print("  1. Q2_original_mesh.png - Original mesh with constraints")
    print("  2. Q2_laplacian_result.png - Laplacian deformation result")
    print("  3. Q2_arap_result.png - ARAP deformation result")
    print("  4. Q2_convergence.png - ARAP convergence plot")
    print("  5. Q2_comparison.png - Side-by-side comparison")


if __name__ == "__main__":
    main()
