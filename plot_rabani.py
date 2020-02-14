import os

import h5py
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors

# Setup
root_dir = "/home/mltest1/tmp/pycharm_project_883/Images/2020-02-14/20-21"
files = os.listdir(root_dir)

img_res = 128
axis_res = 4
kT_range = [0.1, 3]
mu_range = [3, 4]

kT_vals = np.linspace(kT_range[0], kT_range[1], axis_res)
mu_vals = np.linspace(mu_range[0], mu_range[1], axis_res)

# Place each image in an array
big_img_arr = np.zeros((img_res * axis_res, img_res * axis_res))
i = 0
for file in files:
    img_file = h5py.File(f"{root_dir}/{file}", "r")

    kT_ind = np.searchsorted(kT_vals, img_file.attrs["kT"])
    mu_ind = np.searchsorted(mu_vals, img_file.attrs["mu"])

    # Place in array
    big_img_arr[(mu_ind * 128):((mu_ind + 1) * 128), (kT_ind * 128):((kT_ind + 1) * 128)] = img_file["image"]
big_img_arr = np.fliplr(big_img_arr)

# Plot
cmap = colors.ListedColormap(["black", "white", "orange"])
boundaries = [0, 0.5, 1]
norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)

fig, ax = plt.subplots()
plt.imshow(big_img_arr, cmap=cmap, origin="lower")

# Make plot not look like trash
plt.xticks(rotation=90)
plt.xticks(np.arange(len(mu_vals)) * 128 + 64, np.round(mu_vals, 2))
plt.yticks(np.arange(len(kT_vals)) * 128 + 64, np.round(kT_vals, 2))

ax.set_xticks([x * img_res for x in range(axis_res)], minor=True)
ax.set_yticks([y * img_res for y in range(axis_res)], minor=True)

plt.grid(which="minor", ls="-", lw=2, color="r")

# Set labels
plt.xlabel("mu")
plt.ylabel("kT")
