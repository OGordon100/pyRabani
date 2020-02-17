import os

import h5py
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from matplotlib.ticker import MultipleLocator
from skimage import measure
from skimage.filters import gaussian


def dualscale_plot(xaxis, yaxis, root_dir, target_axis_labels=15):
    files = os.listdir(root_dir)

    # Find image details
    axis_res = int(np.sqrt(len(files)))
    x_range_all = np.zeros((len(files),))
    y_range_all = np.zeros((len(files),))
    m_all = np.zeros((len(files),))
    for i, file in enumerate(files):
        img_file = h5py.File(f"{root_dir}/{file}", "r")
        x_range_all[i] = img_file.attrs[xaxis]
        y_range_all[i] = img_file.attrs[yaxis]
        m_all[i] = img_file.attrs["num_mc_steps"]
        img_res = len(img_file["image"])

    x_range = [np.min(x_range_all), np.max(x_range_all)]
    y_range = [np.min(y_range_all), np.max(y_range_all)]

    # Place each image in an array
    big_img_arr = np.zeros((img_res * axis_res, img_res * axis_res))
    x_vals = np.linspace(x_range[0], x_range[1], axis_res)
    y_vals = np.linspace(y_range[0], y_range[1], axis_res)
    eulers = np.zeros((axis_res, axis_res))

    for i, file in enumerate(files):
        img_file = h5py.File(f"{root_dir}/{file}", "r")

        x_ind = np.searchsorted(x_vals, img_file.attrs[xaxis])
        y_ind = np.searchsorted(y_vals, img_file.attrs[yaxis])
        big_img_arr[(y_ind * 128):((y_ind + 1) * 128), (x_ind * 128):((x_ind + 1) * 128)] = np.flipud(
            img_file["image"])

        eulers[y_ind, x_ind] = measure.regionprops((img_file["image"][()] != 0).astype(int) + 1)[0][
                                   "euler_number"] / np.sum(img_file["image"][()] == 2)

    # Plot
    cmap = colors.ListedColormap(["black", "white", "orange"])
    boundaries = [0, 0.5, 1]
    norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)

    num_tick_skip = len(y_vals) // np.min((target_axis_labels, len(y_vals)))

    x_labels = [f"{x_val:.2f}" for x_val in x_vals]
    x_labels = [f"{y_val:.2f}" for y_val in y_vals]

    blank_labels_mu = [None] * len(x_labels)
    blank_labels_y = [None] * len(x_labels)
    blank_labels_mu[::num_tick_skip] = x_labels[::num_tick_skip]
    blank_labels_y[::num_tick_skip] = x_labels[::num_tick_skip]

    # Sample grid
    fig1, ax1 = plt.subplots()
    plt.imshow(big_img_arr, cmap=cmap, origin="lower")

    plt.xticks(np.arange(len(y_vals)) * img_res + img_res / 2, blank_labels_mu, rotation=90)
    plt.yticks(np.arange(len(x_vals)) * img_res + img_res / 2, blank_labels_y)
    ax1.set_xticks([x * img_res for x in range(axis_res)], minor=True)
    ax1.set_yticks([y * img_res for y in range(axis_res)], minor=True)

    ax1.set_xlabel(xaxis)
    ax1.set_ylabel(yaxis)

    plt.grid(which="minor", ls="-", lw=2, color="r")

    # Euler
    fig2, ax2 = plt.subplots()
    cax2 = ax2.matshow(eulers, origin="lower", cmap="jet")

    X2, Y2 = np.meshgrid(np.arange(len(eulers)), np.arange(len(eulers)))
    cnts2 = plt.contour(X2, Y2, gaussian(eulers, 1), levels=15, colors="w", linestyles="solid")

    # Remove small contour circles
    for level in cnts2.collections:
        for kp, path in reversed(list(enumerate(level.get_paths()))):
            verts = path.vertices
            diameter = np.max(verts.max(axis=0) - verts.min(axis=0))
            if diameter < 10:
                del (level.get_paths()[kp])

    # Pretty up axis
    ax2.xaxis.tick_bottom()
    ax2.set_xticklabels([''] + x_labels[::num_tick_skip], rotation=90)
    ax2.set_yticklabels([''] + x_labels[::num_tick_skip])
    ax2.xaxis.set_major_locator(MultipleLocator(num_tick_skip))
    ax2.yaxis.set_major_locator(MultipleLocator(num_tick_skip))

    cbar = fig2.colorbar(cax2)
    cbar.add_lines(cnts2)
    cbar.set_label('Normalised Euler Characteristic', rotation=270)
    cbar.ax.get_yaxis().labelpad = 15

    ax2.set_xlabel(xaxis)
    ax2.set_ylabel(yaxis)


if __name__ == '__main__':
    dualscale_plot(xaxis="mu", yaxis="kT", root_dir="/home/mltest1/tmp/pycharm_project_883/Images/2020-02-17/09-44")
