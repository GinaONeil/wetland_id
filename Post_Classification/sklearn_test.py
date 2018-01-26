# -*- coding: utf-8 -*-
"""
Created on Mon Oct 16 10:30:11 2017

@author: Gina O'Neil
"""
#
import subprocess
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from osgeo import gdal, gdal_array, ogr
import numpy as np
import sys

#******direct script to files********
shp = r"H:\P06_RT29\Data\VDOT_Verification\P06_LimitsP.shp"
# composite is a multidimensional raster file where each dimensions represents an input variable (i.e., input variable rasters are "stacked" into one)
composite = r"D:\Wetlands_2\Rt29\Composites\RF_A_clipenvebm.tif"

#train_tif is the training raster file (and path to) used in the RF classification
train_tif = r"D:\Wetlands_2\Rt29\Training\50p_100ar3_snap.tif"

#test is the VDOT wetland delineations raster file, training data has not been separated from these delineations
test = r"H:\P06_RT29\Data\VDOT_Verification\p06_vals_str_clip.tif"

#******read files as gdal datasets********

comp_ds = gdal.Open(composite, gdal.GA_ReadOnly)

train_ds = gdal.Open(train_tif, gdal.GA_ReadOnly)

test_ds = gdal.Open(test, gdal.GA_ReadOnly)

num_bands = comp_ds.RasterCount

print "Number of bands in composite: {n}\n".format(n=num_bands) #bands = dimensions

#need these attributes to write a new georeferenced file
driver = comp_ds.GetDriver()
prj = comp_ds.GetProjection()
ncol = comp_ds.RasterXSize
nrow = comp_ds.RasterYSize
ext = comp_ds.GetGeoTransform()

print "Composite's Y size is: "
print nrow 

print "Composite's X Size is: "
print ncol

print 'Raster driver: {d}\n'.format(d=driver.ShortName)

gdal.UseExceptions()
gdal.AllRegister()

num_bands = train_ds.RasterCount
print "Number of bands in training raster: {n}\n".format(n=num_bands)

train_arr = train_ds.GetRasterBand(1).ReadAsArray().astype('int')

test_arr = test_ds.GetRasterBand(1).ReadAsArray().astype('int')

print "Shape of entire roi training area: {n} \n".format(n=train_arr.shape)

#printing to quickly find the NaN of train_arr, \
#data values should be either =0 for wetland or =1 for non-wetland another number must be NaN
#this part needs to be automated in the future
print np.min(train_arr)
print np.max(train_arr)

#creating an empty array that is the size I want
img = np.zeros((comp_ds.RasterYSize, comp_ds.RasterXSize, comp_ds.RasterCount), \
               gdal_array.GDALTypeCodeToNumericTypeCode(comp_ds.GetRasterBand(1).DataType))

#populating the empty array
for b in range(img.shape[2]):
    img[:, :, b] = comp_ds.GetRasterBand(b + 1).ReadAsArray()

#masking img array to only include where train_arr is not NaN (i.e., <3, the NaN value)
#this is not a sophisticated way to do it
    
X = img[train_arr < 3, :] #pixels that will be used for training
Y = train_arr[train_arr < 3] #"class labels" that indicate which class (w/nw/) training pixels belong to

print('Our X matrix is sized: {sz}'.format(sz=X.shape))
print('Our y array is sized: {sz}'.format(sz=Y.shape))

#uncomment for a stopping point to check progress so far
##sys.exit(0) 

# Initialize our model with 100 trees
rf = RandomForestClassifier(n_estimators=100, oob_score=True, n_jobs = 8)


# Fit our model to training data
rf = rf.fit(X, Y)
print('Our OOB prediction of accuracy is: {oob}%'.format(oob=rf.oob_score_ * 100))
bands = [1, 2, 3]

#show variable importance output from RF classification
for b, imp in zip(bands, rf.feature_importances_):
    print('Band {b} importance: {imp}'.format(b=b, imp=imp))

#need to flatten array into 2D to classify   
new_shape = (img.shape[0] * img.shape[1], img.shape[2])

img_as_array = img[:, :, :].reshape(new_shape)
print('Reshaped from {o} to {n}'.format(o=img.shape,
                                        n=img_as_array.shape))

# Now predict for each pixel
class_prediction = rf.predict(img_as_array)

# Reshape our classification map
class_prediction = class_prediction.reshape(img[:, :, 0].shape)

print np.shape(class_prediction)

# save results to a geotiff file so we can view them in ArcGIS
sklearn_results_name = 'sklearn_RF_geo6.tif'

out_raster_ds = driver.Create(sklearn_results_name, ncol, nrow, 1, gdal.GDT_Byte)
out_raster_ds.SetProjection(prj)
out_raster_ds.SetGeoTransform(ext)
out_raster_ds.GetRasterBand(1).WriteArray(class_prediction)
# Close dataset
out_raster_ds = None

#module to clip the results to the study area boundary
def clip_rasters(raster, boundary):
    # Name of clip raster file(s)
    clipped = raster[:-4]+'_clip.tif'
    
    cmd = "gdalwarp.exe -cutline %s -crop_to_cutline -dstnodata 255 -tr 0.76200152 0.76200152 -r bilinear \
    %s %s" %(boundary, raster, clipped) 
    cmd_info = 'gdalinfo.exe -stats %s'%(clipped)
    subprocess.call(cmd)
    subprocess.call(cmd_info)
    print "%s has been clipped!" %(raster)
    
clip_rasters('.\\'+sklearn_results_name, shp)


