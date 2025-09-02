import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import jcmwave

def get_field(filename):
    cart = jcmwave.loadcartesianfields(filename) 

    X = cart.get("x", cart.get("X"))
    Y = cart.get("y", cart.get("Y"))

    X = np.squeeze(np.array(X))
    Y = np.squeeze(np.array(Y))

    E = cart["field"]                         
    #I = E[0][:,:,2]
    I = np.sum(np.abs(E)**2, axis=-1)     # drop vector components

    #I = np.squeeze(np.array(I))               # make it 2D (Nx, Ny)
    # plt.figure()
    # pcm = plt.pcolormesh(X, Y, I, shading="auto", vmin=0.0, vmax=1.0e5)
    # plt.xlabel("x (m)")
    # plt.ylabel("y (m)")
    # plt.title("|E|² on x–y")
    # plt.colorbar(pcm, label="a.u.")
    # plt.tight_layout()
    # plt.show()
    return X, Y, I


# --- normalize shapes to a rectilinear grid ---
# If X,Y are 1D axes, great; if 2D meshgrids, reduce to axes.
def to_axes_and_grid(X, Y, Z):
    X = np.squeeze(X); Y = np.squeeze(Y); Z = np.squeeze(Z)
    if X.ndim == 1 and Y.ndim == 1:
        x, y = X, Y
        # Z may be (Nx,Ny) or (Ny,Nx); fix if needed
        if Z.shape == (x.size, y.size):
            Zg = Z
        elif Z.shape == (y.size, x.size):
            Zg = Z.T
        else:
            raise ValueError(f"Unexpected Z shape {Z.shape} for axes {(x.size,y.size)}")
        return x, y, Zg
    else:
        # 2D grids: derive axes from unique values
        x = np.unique(X.ravel())
        y = np.unique(Y.ravel())
        # Try reshaping Z to (Nx,Ny) or (Ny,Nx)
        try:
            Zg = Z.reshape(x.size, y.size)
        except ValueError:
            Zg = Z.reshape(y.size, x.size).T
        return x, y, Zg

def get_depth(X, Y, I, y0):
    x_axis, y_axis, Igrid = to_axes_and_grid(X, Y, I)
    # --- pick the column at x ≈ 0 (nearest sample) ---
    ix = int(np.argmin(np.abs(x_axis - 10.0e-9)))
    x0 = x_axis[ix]

    # --- select y ≤ threshold; try raw then meters fallback ---
    y_thresh_raw = y0             # same units as your export (often nm)
    mask = y_axis <= y_thresh_raw

    if not np.any(mask):
        # fallback assuming export is in meters and -1443 was meant as nm
        y_thresh_m = (y_thresh_raw)*1e-9
        mask = y_axis <= y_thresh_m

    if not np.any(mask):
        # last resort: report ranges to help debug units
        print("No points matched the y-threshold.")
        print(f"x range: [{x_axis.min():.3e}, {x_axis.max():.3e}]")
        print(f"y range: [{y_axis.min():.3e}, {y_axis.max():.3e}]")
        raise SystemExit

    # --- extract line and sort by y for plotting ---
    y_line = y_axis[mask]
    I_line = Igrid[ix, mask]
    order = np.argsort(y_line)
    y_line = y_line[order]
    I_line = I_line[order]
    y_line = y0 - y_line * 1e9
    return y_line, I_line, x0


size = 15
X, Y, I = get_field("Graphene/project_results/fullbag2nm.jcm")
y_line, I_line, x0 = get_depth(X, Y, I, -1442.3)
plt.plot(y_line, np.log10(I_line), label="Graphene w/ 2nm Gap", ls="-", color="red")
#plt.scatter(y_line, np.log10(I_line), s=size, marker=".")

# X, Y, I = get_field("Graphene/project_results/fullbag10nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1450.3)
# plt.plot(y_line, np.log10(I_line), label="Graphene w/ 10nm Gap")

# X, Y, I = get_field("Graphene/project_results/fullbag20nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1460.3)
# ax[0].plot(y_line, np.log10(I_line), label="Graphene w/ 20nm Gap")

# X, Y, I = get_field("Graphene/project_results/fullbag30nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1470.3)
# ax[0].plot(y_line, np.log10(I_line), label="Graphene w/ 30nm Gap")

# X, Y, I = get_field("Graphene/project_results/fullbag40nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1480.3)
# ax[0].plot(y_line, np.log10(I_line), label="Graphene w/ 40nm Gap")

X, Y, I = get_field("Graphene/project_results/fullbag50nm.jcm")
y_line, I_line, x0 = get_depth(X, Y, I, -1490.3)
plt.plot(y_line, np.log10(I_line), label="Graphene w/ 50nm Gap", ls="-", color="green")
#plt.scatter(y_line, np.log10(I_line), s=size, marker=".")

X, Y, I = get_field("Graphene/project_results/fullbag.jcm")
y_line, I_line, x0 = get_depth(X, Y, I, -1540.3)
plt.plot(y_line, np.log10(I_line), label="Graphene w/ 100nm Gap", ls="-", color="blue")
#plt.scatter(y_line, np.log10(I_line), s=size, marker=".")






X, Y, I = get_field("Silicon Nitride/project_results/fullbag2nm.jcm")
y_line, I_line, x0 = get_depth(X, Y, I, -1457.0)
plt.plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 2nm Gap", ls="--", color="red")
#plt.scatter(y_line, np.log10(I_line), s=size, marker="x")

# X, Y, I = get_field("Silicon Nitride/project_results/fullbag10nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1465.0)
# plt.plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 10nm Gap")
# plt.scatter(y_line, np.log10(I_line), s=2, marker="x")

# X, Y, I = get_field("Silicon Nitride/project_results/fullbag20nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1475.0)
# ax[1].plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 20nm Gap")

# X, Y, I = get_field("Silicon Nitride/project_results/fullbag30nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1485.0)
# ax[1].plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 30nm Gap")

# X, Y, I = get_field("Silicon Nitride/project_results/fullbag40nm.jcm")
# y_line, I_line, x0 = get_depth(X, Y, I, -1495.0)
# ax[1].plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 40nm Gap")

X, Y, I = get_field("Silicon Nitride/project_results/fullbag50nm.jcm")
y_line, I_line, x0 = get_depth(X, Y, I, -1505.0)
plt.plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 50nm Gap", ls="--", color="green")
#plt.scatter(y_line, np.log10(I_line), s=size, marker="x")

X, Y, I = get_field("Silicon Nitride/project_results/fullbag100nm.jcm")
y_line, I_line, x0 = get_depth(X, Y, I, -1555.0)
plt.plot(y_line, np.log10(I_line), label="Silicon Nitride w/ 100nm Gap", ls="--", color="blue")
#plt.scatter(y_line, np.log10(I_line), s=size, marker="x")

plt.xlabel("y (nm)")
plt.ylabel("E Field (log10)")
plt.title(f"Intensity along x≈{x0:.3e} vs Water Depth")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()