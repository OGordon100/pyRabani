# Code offers a selection of preprocessing techniques, saving a figure of all the results

# To-Do:
## Write in Ostu Mask and old Poly BG sub method if required
## Comment the code you ape
## Add the toggle to simply save the images produced by plot-all and a simple format for final preprocessed image in 2-ste
## Make a separate code that
## Make it so spline dof 1 can be used by changing it from df -1 to df +1

# Images
## 'C12b_Ci_ring8_0006.ibw'
## Si_d10_ring5_05mgmL_0003.ibw - Filters poorly
## SiO2_d10_ring5_1mgmL_0003.ibw

# eu_testsR/C12_Ci4_ring5_0001.ibw
# eu_testsR/C12b_Ci_ring8_0001.ibw x
# eu_testsR/s5b_th_ring_Eout_0001.ibw
# eu_testsR/Si_d10th_ring5_05mgmL_0005.ibw you forgot this one :P
# eu_testsR/SiO2_contacts_21_0000.ibw

import h5py
import numpy as np
import matplotlib.pyplot as plt
import pycroscopy as scope
from rpy2.robjects.packages import importr
from rpy2 import robjects as ro
import rpy2.robjects.numpy2ri
splines = importr('splines')   # Imports the splines package in R


# Change the file here!
file_name = 'eu_testsR/C12_Ci4_ring5_0001.ibw'
# Change the file path if needed
file_path = r'imageR/' + file_name
# Change the preprocessing methods here, comment out all but one in each string
aligner = (
    "mod"   # Median of differences
    #"otsu"
    #"maskotsu"  #TBI
)
detrender = (
    "spline"
    #"poly"
    #"oldpoly"  # TBI?  Old redundant method
)
plot_all = (  # Choose whether to ignore the above two options and perform all of them
    "yes"
    # "no"
)

# Define a degree of freedom to be used in detrenders, Df acts as the DoF in spline while DoF in the polynomial
# detrend DoF acts as Df - 1.  Default is 4.
Df = 2

# Assign DoF to a variable in R space
DoF = ro.r.matrix(Df)
ro.r.assign("df", DoF)

# Where to save the resulting files, all appended with the file name, method and detrender degrees of freedom
if plot_all == 'no':
    append = '_'+aligner+'_'+detrender+str(Df)
elif plot_all == 'yes':
    append = '_all_' + str(Df)
sav_loc = r'resR/' + file_name.replace('.ibw', append)


def trace_loader(filepath):
    # Create an object capable of translating .ibw files
    TranslateObj = scope.io.translators.IgorIBWTranslator(max_mem_mb=1024)
    # Translate the requisite file
    Output = TranslateObj.translate(
        file_path=filepath, verbose=False)
    print(Output)
    # Opening this file to read in sections as a numpy array
    read_path = Output
    h5_File = h5py.File(Output, mode='r')
    data_Trace = h5_File['Measurement_000/Channel_000/Raw_Data']
    # phase_Trace = h5_File['Measurement_000/Channel_002/Raw_Data']
    data_Trace_Array = np.array(data_Trace[:])
    # phase_Trace_Array = np.array(phase_Trace[:])
    h5_File.close()
    return data_Trace_Array

# Load the ibw file from the chosen file path and save the data trace as a numpy array
data_Trace_Array = trace_loader(file_path)

# Identify the size of the data trace array and reshape the array accordingly
if data_Trace_Array.shape[0] == 65536:
    row_num = 256
elif data_Trace_Array.shape[0] == 262144:
    row_num = 512
elif data_Trace_Array.shape[0] == 1048576:
    row_num = 1024

shaped_data_Trace_Array = np.reshape(data_Trace_Array, (row_num, row_num))

plt.rc('font', size=4)  # Set the fonts in graphs to 4
def noticks():   # Define a unction to remove ticks on graph axes
    plt.xticks([])
    plt.yticks([])


# Define a function that sets an image numpy array's values (pixel intensities) to be between 0 and 1
def normalise(array):
    norm_array = (array - np.min(array)) \
                 / (np.max(array) - np.min(array))
    return norm_array


ro.numpy2ri.activate()  # Converts all R-objects entering the python variable space into numpy-able formats

norm_data_Trace_Array = normalise(shaped_data_Trace_Array)

# Return the raw image as a plot
plt.figure()
if plot_all == 'yes':
    plt.subplot(2, 4, 1)
elif plot_all == 'no':
    plt.subplot(3, 1, 1)
plt.imshow(norm_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
           cmap='RdGy')
plt.title(file_name)
noticks()


if aligner == 'mod' or plot_all == 'yes':
# ## Median Alignment approach # ###
# # Align every median in the normalised array to be equal by finding the difference between the 1st and i-th row's
# # medians, and then offset all the data in that row by the same amount in order to equate them
    def line_align(row1, row2):
        diff = row1 - row2
        bins = np.linspace(np.min(diff), np.max(diff), 1000)
        binned_indices = np.digitize(diff, bins, right=True)
        np.sort(binned_indices)
        median_index = np.median(binned_indices)
        return bins[int(median_index)]


    def mod_align(img, row_number):
        img = normalise(img)
        for j in range(1, row_number):
            row_jless1 = img[j - 1, :]
            row_j = img[j, :]
            offset = line_align(row_jless1, row_j)
            img[j, :] = img[j, :] + offset
        return img

    aligned_data_Trace_Array = mod_align(shaped_data_Trace_Array, row_num)
    aligned_data_Trace_Array = normalise(aligned_data_Trace_Array)

    # Plot the result
    if plot_all == 'yes':
        plt.subplot(2, 4, 2)
        mod_aligned_data_Trace_Array = aligned_data_Trace_Array
    elif plot_all =='no':
        plt.subplot(3, 1, 2)

    plt.imshow(aligned_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
           cmap='RdGy')
    plt.title('MoD')
    noticks()
    plt.imsave(sav_loc + '_mod.png', aligned_data_Trace_Array, origin='lower', cmap='RdGy')

if aligner == 'otsu' or plot_all == 'yes':
# Otsu aligner description goes here

    # Write a string for calling in R space that defines the functions and code required for thresholding
    otsustring = '''
      otsu_thresh<-function(y) {
      breaks<-(0:255)/255
      h = hist.default(y, breaks = breaks, plot = FALSE)
      counts = as.double(h$counts)
      mids = as.double(h$mids)
      len = length(counts)
      w1 = cumsum(counts)
      w2 = w1[len] + counts - w1
      cm = counts * mids
      m1 = cumsum(cm)
      m2 = m1[len] + cm - m1
      var = w1 * w2 * (m2/w2 - m1/w1)^2
      maxi = which(var == max(var, na.rm = TRUE))
      (mids[maxi[1]] + mids[maxi[length(maxi)]])/2
    }
    # normalise<-function(img) {
    #   return((img - min(img))/(max(img)-min(img)))
    # }
    col_otsu<-apply(normim,1,otsu_thresh) #First step in Otsu alignment, needed to change from margin 2 to 1
    row_num<-dim(normim)[1]
    otsudiff<-col_otsu-min(col_otsu) #Second step in Otsu alignment
    otsumatrix<-(matrix(rep(otsudiff,row_num),row_num,row_num)) # Third step in Otsu alignment, needed to remove transpose function
    otsualign = normim-otsumatrix # Fourth step in Otsu alignment

    '''
    # Assign the normalised data trace array to a variable in R space
    data_matrix = ro.r.matrix(norm_data_Trace_Array, nrow=row_num, ncol=row_num)
    ro.r.assign("r_data_matrix", data_matrix)
    ro.r("normim <- r_data_matrix")
    # Run the pre-defined string and return the last assigned variable in R, the aligned image, as a numpy array
    aligned_data_Trace_Array = ro.r(otsustring)
    aligned_data_Trace_Array = normalise(aligned_data_Trace_Array)

    # Plot the result
    if plot_all == 'yes':
        plt.subplot(2, 4, 3)
        otsu_aligned_data_Trace_Array = aligned_data_Trace_Array
    elif plot_all == 'no':
        plt.subplot(3, 1, 2)

    plt.imshow(aligned_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
           cmap='RdGy')
    plt.title('Otsu')
    noticks()
    plt.imsave(sav_loc + '_otsu.png', aligned_data_Trace_Array, origin='lower', cmap='RdGy')

# elif aligner == 'maskotsu' or plot_all == 'yes':
# else:
#     aligned_data_Trace_Array = normalise(shaped_data_Trace_Array)

# aligned_data_Trace_Array = normalise(aligned_data_Trace_Array)
# plt.subplot()
# noticks()

if detrender == 'spline' or plot_all == 'yes':
# Description of Quadratic Spline Detrender goes here

    splinestring = '''
      row_num<-dim(alignim)[1]
      im1data<-data.frame(as.vector(alignim)) # Turning image1 into a dataframe of columns x, y and intensity
      names(im1data)<-"intensity"
      im1data$x<-rep(1:row_num,row_num)
      im1data$y<-as.vector(t(matrix(rep(1:row_num,row_num),row_num,row_num)))

      im4mod3<-lm(intensity~ns(x,df)*ns(y,df),data=im1data) # 1st step of spline detrend
    # replace ns(x,4) for poly(x,3) for polynomial fit (df = degrees of freedom) (n-1 takes into account constant)
      im1data$lmresid<-(im4mod3$residuals -min(im4mod3$residuals))/(max(im4mod3$residuals)-min(im4mod3$residuals))  # 2nd step of spline detrend

      spline_dt<-(matrix(im1data$lmresid,row_num,row_num))
    '''

    if plot_all == 'no':
        data_matrix = ro.r.matrix(aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
        ro.r.assign("r_data_matrix", data_matrix)
        ro.r("alignim <- r_data_matrix")
        detrended_data_Trace_Array = ro.r(splinestring)
        detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)

        plt.subplot(3, 1, 3)
        plt.imshow(aligned_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
            cmap='RdGy')
        plt.title('Spline')
        noticks()
    if plot_all == 'yes':
        data_matrix = ro.r.matrix(mod_aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
        ro.r.assign("r_data_matrix", data_matrix)
        ro.r("alignim <- r_data_matrix")
        detrended_data_Trace_Array = ro.r(splinestring)
        detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)

        plt.subplot(2, 4, 5)
        plt.imshow(detrended_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
                   cmap='RdGy')
        plt.title('MoD-Spline')
        noticks()
        plt.imsave(sav_loc + '_mod_spline.png', detrended_data_Trace_Array, origin='lower', cmap='RdGy')

        data_matrix = ro.r.matrix(otsu_aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
        ro.r.assign("r_data_matrix", data_matrix)
        ro.r("alignim <- r_data_matrix")
        detrended_data_Trace_Array = ro.r(splinestring)
        detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)

        plt.subplot(2, 4, 7)
        plt.imshow(detrended_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
                   cmap='RdGy')
        plt.title('Otsu-Spline')
        noticks()
        plt.imsave(sav_loc + '_otsu_spline.png', detrended_data_Trace_Array, origin='lower', cmap='RdGy')

if detrender == 'poly' or plot_all == 'yes':
    # Description of Polynomial goes here

    polystring = '''
      row_num<-dim(alignim)[1]
      im1data<-data.frame(as.vector(alignim)) # Turning image1 into a dataframe of columns x, y and intensity
      names(im1data)<-"intensity"
      im1data$x<-rep(1:row_num,row_num)
      im1data$y<-as.vector(t(matrix(rep(1:row_num,row_num),row_num,row_num)))

      im4mod3<-lm(intensity~poly(x,df-1)*poly(y,df-1),data=im1data) # 1st step of poly detrend
    # replace ns(x,4) for poly(x,3) for polynomial fit (df = degrees of freedom) (n-1 takes into account constant)
      im1data$lmresid<-(im4mod3$residuals -min(im4mod3$residuals))/(max(im4mod3$residuals)-min(im4mod3$residuals))  # 2nd step of poly detrend

      poly_dt<-(matrix(im1data$lmresid,row_num,row_num))
    '''

    if plot_all == 'no':
        data_matrix = ro.r.matrix(aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
        ro.r.assign("r_data_matrix", data_matrix)
        ro.r("alignim <- r_data_matrix")
        detrended_data_Trace_Array = ro.r(polystring)
        detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)

        plt.subplot(3, 1, 3)
        plt.imshow(aligned_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
                   cmap='RdGy')
        plt.title('Poly')
        noticks()
    if plot_all == 'yes':
        data_matrix = ro.r.matrix(mod_aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
        ro.r.assign("r_data_matrix", data_matrix)
        ro.r("alignim <- r_data_matrix")
        detrended_data_Trace_Array = ro.r(polystring)
        detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)

        plt.subplot(2, 4, 6)
        plt.imshow(detrended_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
                   cmap='RdGy')
        plt.title('MoD-Poly')
        noticks()
        plt.imsave(sav_loc + '_mod_poly.png', detrended_data_Trace_Array, origin='lower', cmap='RdGy')

        data_matrix = ro.r.matrix(otsu_aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
        ro.r.assign("r_data_matrix", data_matrix)
        ro.r("alignim <- r_data_matrix")
        detrended_data_Trace_Array = ro.r(polystring)
        detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)

        plt.subplot(2, 4, 8)
        plt.imshow(detrended_data_Trace_Array, extent=(0, row_num, 0, row_num), origin='lower',
                   cmap='RdGy')
        plt.title('Otsu-Poly')
        noticks()
        plt.imsave(sav_loc + '_otsu_poly.png', detrended_data_Trace_Array, origin='lower', cmap='RdGy')

# elif detrender == 'oldpoly' or plot_all == 'yes':
# else:
#     detrended_data_Trace_Array = normalise(shaped_data_Trace_Array)

# detrended_data_Trace_Array = normalise(detrended_data_Trace_Array)
# plt.subplot()
# noticks()

plt.ion()
plt.savefig(sav_loc + '.svg')


# data_matrix = ro.r.matrix(mod_aligned_data_Trace_Array, nrow=row_num, ncol=row_num)
# ro.r.assign("r_data_matrix", data_matrix)
# ro.r("normim <- r_data_matrix")
# aligned_data_Trace_Array = ro.r(otsustring)
# aligned_data_Trace_Array = normalise(aligned_data_Trace_Array)
# plt.imsave(sav_loc + '_eu_test.png', aligned_data_Trace_Array, origin='lower', cmap='RdGy')