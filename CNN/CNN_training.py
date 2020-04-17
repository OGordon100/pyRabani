import datetime
import os
import subprocess

import h5py
import numpy as np
from keras.callbacks import EarlyStopping, ModelCheckpoint
from scipy.stats import bernoulli, mode
from sklearn.utils import class_weight
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import Sequence

from CNN.get_model import get_model, autoencoder
from CNN.get_stats import plot_model_history
from Rabani_Generator.plot_rabani import power_resize, visualise_autoencoder_preds


class h5RabaniDataGenerator(Sequence):
    def __init__(self, root_dir, batch_size, network_structure, output_parameters_list, output_categories_list,
                 is_train, imsize=None,
                 horizontal_flip=True, vertical_flip=True, x_noise=0.005, circshift=True, randomise_levels=True):
        """
        A keras data generator class for rabani simulations stored as h5 files in a directory

        Parameters
        ----------

        root_dir : str
            The folder directory to run through. Must only have h5 files in it
        batch_size : int
            Number of items to return every time __getitem__() is called
        network_structure : str
            The calling network type. Must be one of ["Supervised", "Autoencoder"]
        is_train : bool
            Boolean describing if the class is generating data for training or for testing.
            If True, no augmentations will be applied
        horizontal_flip : bool
            Randomly applies horizontal flips. Only occurs if is_train is True
        vertical_flip : bool
            Randomly applies vertical flips. Only occurs if is_train is True
        x_noise : float or None
            Applies a percentage of speckle noise if not None. Only occurs if is_train is True
        circshift : bool
            Randomly pans around the wrapped simulations. Only occurs if is_train is True
        randomise_levels : bool
            Randomly swaps the integer denoting substrate/liquid/nanoparticle batchwise. Only occurs if is_train is True
        output_parameters_list : iterable of str
            Unused for now. Used for prediction of specific rabani simulated parameters
        output_categories_list : iterable of str
            Categories to be predicted by the network if network_structure == "Supervised"
        """

        self.root_dir = root_dir
        self.batch_size = batch_size
        self.original_parameters_list = output_parameters_list
        self.original_categories_list = output_categories_list
        self.network_structure = network_structure

        self.is_training_set = is_train
        self.is_validation_set = False

        self.hflip = horizontal_flip
        self.vflip = vertical_flip
        self.xnoise = x_noise
        self.circshift = circshift
        self.randomise_levels = randomise_levels

        self.class_weights_dict = None
        self.__reset_file_iterator__()

        if imsize:
            self.image_res = imsize
        else:
            self._get_image_res()

        self._get_class_weights()

        self._batches_counter = 0
        self.x_true = np.empty((self.__len__() * self.batch_size, self.image_res, self.image_res, 1))
        self.y_true = np.empty((self.__len__() * self.batch_size, len(self.original_categories_list)))

    def _get_class_weights(self):
        """Compute the class weights by opening files in the directory"""
        self.__reset_file_iterator__()
        if self.is_training_set:
            # os.scandir random iterates, so can take a subset of max 50k files to make good approximation
            length = min(int(self.__len__()) * self.batch_size, 50000)
        else:
            length = int(self.__len__()) * self.batch_size

        if not self.is_validation_set:
            class_inds = np.zeros((length,))

            for i in range(length):
                file_entry = self._file_iterator.__next__().path
                h5_file = h5py.File(file_entry, "r")
                idx_find = self.original_categories_list.index(h5_file.attrs["category"])
                class_inds[i] = idx_find

            self.class_weights_dict = class_weight.compute_class_weight('balanced',
                                                                        np.arange(len(self.original_categories_list)),
                                                                        class_inds)

        self.__reset_file_iterator__()

    def _get_image_res(self):
        """Open one file to check the image resolution"""
        self.image_res = len(h5py.File(self._file_iterator.__next__().path, "r")["sim_results"]["image"])
        self.__reset_file_iterator__()

    def on_epoch_end(self):
        """Resets the file iterator at the end of an epoch"""
        self.__reset_file_iterator__()

    def __reset_file_iterator__(self):
        """Resets the file iterator (do this instead of os.listdir for speed on massive datasets!)"""
        self._file_iterator = os.scandir(self.root_dir)
        self._batches_counter = 0

    def __len__(self):
        """Get number of complete batches that can be formed"""
        n_files = int(
            subprocess.Popen([f"find '{self.root_dir}' -maxdepth 1 | wc -l"],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True).communicate()[0]) - 1
        return int(np.floor(n_files // self.batch_size))

    def __getitem__(self, idx):
        """Get self.batch_size number of items, shaped and augmented"""

        # Preallocate output
        batch_x = np.empty((self.batch_size, self.image_res, self.image_res, 1))
        batch_y = np.empty((self.batch_size, len(self.original_categories_list)))

        # For each file in the batch
        for i in range(self.batch_size):
            # Parse parameters from the h5 file
            file_entry = self._file_iterator.__next__().path
            h5_file = h5py.File(file_entry, "r")

            batch_x[i, :, :, 0] = power_resize(h5_file["sim_results"]["image"][()], self.image_res).astype(np.uint8)
            batch_x[i, 0, 0, 0] = 0
            batch_x[i, 1, 0, 0] = 1
            batch_x[i, 2, 0, 0] = 2

            idx_find = self.original_categories_list.index(h5_file.attrs["category"])
            batch_y[i, idx_find] = 1

        if self.network_structure is "autoencoder":
            batch_x /= 2  # TODO MAKE GLOBAL

        if self.is_validation_set:
            self.y_true[self._batches_counter * self.batch_size:(self._batches_counter + 1) * self.batch_size,
            :] = batch_y

            if self.network_structure is "autoencoder":
                self.x_true[self._batches_counter * self.batch_size:(self._batches_counter + 1) * self.batch_size,
                :, :, :] = batch_x

        if self.is_training_set:
            batch_x = self._augment(batch_x)

        self._batches_counter += 1
        if self._batches_counter >= self.__len__() and self.is_training_set is False:
            self.__reset_file_iterator__()

        if self.network_structure is "supervised":
            return batch_x, batch_y
        elif self.network_structure is "autoencoder":
            batch_x = self._patch_binarisation(batch_x)
            return batch_x, batch_x
        else:
            raise KeyError("network_structure must be one of ['supervised', 'autoencoder']")

    def _augment(self, batch_x):
        if self.vflip:
            batch_x = self.flip(batch_x, axis=1)
        if self.hflip:
            batch_x = self.flip(batch_x, axis=2)
        if self.circshift:
            batch_x = self.circ_shift(batch_x)
        if self.randomise_levels:
            batch_x = self.randomise_level_index(batch_x)
        if self.xnoise:
            batch_x = self.speckle_noise(batch_x, perc_noise=self.xnoise, perc_std=0.002)

        return batch_x

    def flip(self, batch_x, axis):
        augment_inds_vflip = np.random.choice(self.batch_size, size=(self.batch_size,), replace=False)
        batch_x[augment_inds_vflip, :, :, 0] = np.flip(batch_x[augment_inds_vflip, :, :, 0], axis=axis)

        return batch_x

    def circ_shift(self, batch_x):
        rand_shifts = np.random.choice(self.image_res, size=(self.batch_size, 2))
        for i, rand_shift in enumerate(rand_shifts):
            batch_x[i, :, :, 0] = np.roll(batch_x[i, :, :, 0], shift=rand_shift, axis=[0, 1])

        return batch_x

    @staticmethod
    def randomise_level_index(batch_x):
        tmp_x = batch_x.copy()
        for i, idx in enumerate(np.random.choice(np.arange(3), 3, replace=False)):
            tmp_x[batch_x == idx] = i

        return tmp_x

    @staticmethod
    def speckle_noise(batch_x, perc_noise, perc_std):
        if batch_x.ndim == 2:
            batch_x = np.expand_dims(np.expand_dims(batch_x, 0), -1)

        p_all = np.abs(np.random.normal(loc=perc_noise, scale=perc_std, size=(len(batch_x),)))
        rand_mask = np.zeros(batch_x.shape)
        for i, p in enumerate(p_all):
            rand_mask[i, :, :, 0] = bernoulli.rvs(p=p, size=batch_x[0, :, :, 0].shape)

        rand_arr = 2 * np.random.randint(0, 2, size=batch_x.shape)
        batch_x[rand_mask == 1] = rand_arr[rand_mask == 1]

        return batch_x

    @staticmethod
    def _patch_binarisation(batch_x):
        """
        Finds the least common level in each image in the batch, and replaces it weighted by the other levels
        """
        for i in range(len(batch_x)):
            level_vals, counts = np.unique(batch_x[i, :, :, 0], return_counts=True)
            level_inds = np.arange(3)

            least_common_ind = np.argmin(counts)
            least_common_val = level_vals[least_common_ind]

            other_vals = np.delete(level_vals, least_common_ind)
            other_inds = np.delete(level_inds, least_common_ind)

            prob_other_levels = counts[other_inds]/np.sum(counts[other_inds])

            replacement_inds = np.argwhere(batch_x[i, :, :, 0] == least_common_val)
            replacement_vals = np.random.choice(other_vals, size=(len(replacement_inds),), p=prob_other_levels)

            batch_x[i, replacement_inds[:, 0], replacement_inds[:, 0], 0] = replacement_vals

        return batch_x

def train_model(model_dir, train_datadir, test_datadir, y_params, y_cats, batch_size, epochs, imsize):
    # Set up generators
    train_generator = h5RabaniDataGenerator(train_datadir, network_structure="supervised", batch_size=batch_size,
                                            is_train=True, imsize=imsize,
                                            output_parameters_list=y_params, output_categories_list=y_cats)
    test_generator = h5RabaniDataGenerator(test_datadir, network_structure="supervised", batch_size=batch_size,
                                           is_train=False, imsize=imsize,
                                           output_parameters_list=y_params, output_categories_list=y_cats)

    # Set up model
    input_shape = (train_generator.image_res, train_generator.image_res, 1)
    model = get_model("VGG", input_shape, len(y_cats), Adam())
    early_stopping = EarlyStopping(monitor="val_loss", patience=10)
    model_checkpoint = ModelCheckpoint(get_model_storage_path(model_dir), monitor="val_loss", save_best_only=True)

    # Train
    model.fit_generator(generator=train_generator,
                        validation_data=test_generator,
                        steps_per_epoch=train_generator.__len__(),
                        validation_steps=test_generator.__len__(),
                        class_weight=train_generator.class_weights_dict,
                        epochs=epochs,
                        max_queue_size=100,
                        callbacks=[model_checkpoint, early_stopping])

    return model


def train_autoencoder(train_datadir, test_datadir, y_params, y_cats, batch_size, epochs, imsize):
    # Set up generators
    train_generator = h5RabaniDataGenerator(train_datadir, network_structure="autoencoder", batch_size=batch_size,
                                            is_train=True, imsize=imsize,
                                            output_parameters_list=y_params, output_categories_list=y_cats,
                                            horizontal_flip=False, vertical_flip=False, x_noise=None, circshift=False,
                                            randomise_levels=False)
    test_generator = h5RabaniDataGenerator(test_datadir, network_structure="autoencoder", batch_size=batch_size,
                                           is_train=False, imsize=imsize,
                                           output_parameters_list=y_params, output_categories_list=y_cats)

    (encoder, decoder, model) = autoencoder((imsize, imsize, 1), optimiser=Adam())
    early_stopping = EarlyStopping(monitor="val_loss", patience=10)
    model_checkpoint = ModelCheckpoint(get_model_storage_path("./"), monitor="val_loss", save_best_only=True)

    model.fit_generator(generator=train_generator,
                        validation_data=test_generator,
                        steps_per_epoch=train_generator.__len__(),
                        validation_steps=test_generator.__len__(),
                        epochs=epochs,
                        max_queue_size=100,
                        callbacks=[model_checkpoint, early_stopping])

    return model


def get_model_storage_path(root_dir):
    current_date = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M")
    os.mkdir(f"{root_dir}/{current_date}")
    model_path = f"{root_dir}/{current_date}/model.h5"

    return model_path


def save_model(model, root_dir):
    model_path = get_model_storage_path(root_dir)
    model.save(model_path)


if __name__ == '__main__':
    # Train
    training_data_dir = "/home/mltest1/tmp/pycharm_project_883/Data/Simulated_Images/2020-03-30/16-01"  # "/media/mltest1/Dat Storage/pyRabani_Images"
    testing_data_dir = "/home/mltest1/tmp/pycharm_project_883/Data/Simulated_Images/2020-03-30/16-44"  # "/home/mltest1/tmp/pycharm_project_883/Images/2020-03-09/16-51"
    validation_data_dir = "/home/mltest1/tmp/pycharm_project_883/Data/Simulated_Images/2020-03-25/13-59"

    original_categories = ["liquid", "hole", "cellular", "labyrinth", "island"]
    original_parameters = ["kT", "mu"]

    # trained_model = train_model(model_dir="Data/Trained_Networks", train_datadir=training_data_dir,
    #                             test_datadir=testing_data_dir,
    #                             y_params=original_parameters, y_cats=original_categories, batch_size=128, imsize=128,
    #                             epochs=75)

    trained_model = train_autoencoder(train_datadir=training_data_dir,
                                      test_datadir=testing_data_dir,
                                      y_params=original_parameters, y_cats=original_categories, batch_size=128,
                                      imsize=128,
                                      epochs=10)

    plot_model_history(trained_model)
    visualise_autoencoder_preds(trained_model, simulated_datadir=testing_data_dir,
                                good_datadir="/home/mltest1/tmp/pycharm_project_883/Data/Autoencoder_Testing/Good_Images",
                                bad_datadir="/home/mltest1/tmp/pycharm_project_883/Data/Autoencoder_Testing/Bad_Images")
