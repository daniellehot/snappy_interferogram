#!/usr/bin/env python3.6
import os
import sys
sys.path.append('C:\\Users\\lehot\\.snap\\snap-python')
import snappy
from snappy import GPF
from snappy import ProductIO
from snappy import HashMap
from snappy import jpy
import subprocess
from time import *
# documentation: http://step.esa.int/docs/v2.0/apidoc/engine/overview-summary.html


# prints the path to the snappy configs.
#change in jpyconfig.py e.g. jvm_maxmem = '30G' and in snappy.ini java_max_mem: 30G (and uncomment)

# Hashmap is used to give us access to all JAVA oerators
HashMap = jpy.get_type('java.util.HashMap')
parameters = HashMap()

class Snappy_Utils(object):
    def __init__(self, master_file, slave_file, swath, polarizations, bursts):
        print("class init")
        self.master = master_file
        self.slave = slave_file
        self.swath = swath
        self.pol = polarization
        self.burst_s = bursts[0]
        self.burst_m = bursts[1]

        self.product_m = self.read(self.master)
        self.product_s = self.read(self.slave)

        print("product_m ", type(self.product_m))
        print("product_s ", type(self.product_s))

        #Split
        self.topsar_m = self.topsar_split(self.product_m, self.burst_m)
        self.topsar_s = self.topsar_split(self.product_s, self.burst_s)

        #Orbit File
        self.orbit_m = self.apply_orbit_file(self.topsar_m)
        self.orbit_s = self.apply_orbit_file(self.topsar_s)

        #Back Geocoding
        self.geocode = self.back_geocoding([self.orbit_m, self.orbit_s])

        #Interferogram Formation
        self.gram = self.interferogram(self.geocode)

    def read(self, product):
        print("read")
        return ProductIO.readProduct(product)

    def write(self, product, filename):
        print("write")
        ProductIO.writeProduct(product, filename, "GeoTIFF")
        # Allowed formats to write: GeoTIFF-BigTIFF,HDF5,Snaphu,BEAM-DIMAP,
        # GeoTIFF+XML,PolSARPro,NetCDF-CF,NetCDF-BEAM,ENVI,JP2,
        # Generic Binary BSQ,Gamma,CSV,NetCDF4-CF,GeoTIFF,NetCDF4-BEAM

    def topsar_split(self, product, burst):
        print("topsar_split")
        parameters.put('subswath', self.swath)
        parameters.put('selectedPolarisations', self.pol)
        parameters.put("bursts", burst)
        return GPF.createProduct("TOPSAR-Split", parameters, product)

    def apply_orbit_file(self, product):
        print("apply_orbit_file")
        parameters.put("Orbit State Vectors", "Sentinel Precise (Auto Download)")
        parameters.put("Polynomial Degree", 3)
        return GPF.createProduct("Apply-Orbit-File", parameters, product)


    def back_geocoding(self, product):
        print("back_geocoding")
        parameters.put("Digital Elevation Model", "SRTM 1Sec HGT (Auto Download)")
        parameters.put("DEM Resampling Method", "BICUBIC_INTERPOLATION")
        parameters.put("Resampling Type", "BISINC_5_POINT_INTERPOLATION")
        parameters.put("Mask out areas with no elevation", True)
        parameters.put("Output Deramp and Demod Phase", False)
        return GPF.createProduct("Back-Geocoding", parameters, product)


    def interferogram(self, product):
        print("interferogram")
        parameters.put("Subtract flat-earth phase", True)
        parameters.put("Degree of \"Flat Earth\" polynomial", 5)
        parameters.put("Number of \"Flat Earth\" estimation points", 501)
        parameters.put("Orbit interpolation degree", 3)
        parameters.put("Include coherence estimation", True)
        parameters.put("Square Pixel", False)
        parameters.put("Independent Window Sizes", False)
        parameters.put("Coherence Azimuth Window Size", 10)
        parameters.put("Coherence Range Window Size", 10)
        initial = GPF.createProduct("Interferogram", parameters, product)

        debursted = self.topsar_deburst(initial)
        topophase = self.topophase_removal(debursted)
        filtered = self.goldstein_phasefiltering(topophase)

        return filtered


    def topsar_deburst(self, product):
        print("topsar_deburst")
        parameters.put("Polarisations", "VV")
        return GPF.createProduct("TOPSAR-Deburst", parameters, product)

    def topophase_removal(self, product):
        print("topophase_removal")
        parameters.put("Orbit Interpolation Degree", 3)
        parameters.put("Digital Elevation Model", "SRTM 1Sec HGT (Auto Download)")
        parameters.put("Tile Extension[%]", 100)
        parameters.put("Output topographic phase band", True)
        parameters.put("Output elevation band", False)
        return GPF.createProduct("TopoPhaseRemoval", parameters, product)


    def goldstein_phasefiltering(self, product):
        print("goldstein_phasefiltering")
        parameters.put("Adaptive Filter Exponent in(0,1]:", 1.0)
        parameters.put("FFT Size", 64)
        parameters.put("Window Size", 3)
        parameters.put("Use coherence mask", False)
        parameters.put("Coherence Threshold in[0,1]:", 0.2)
        return GPF.createProduct("GoldsteinPhaseFiltering", parameters, product)

    def write_snaphu(self, product, filename):
        print("write_snaphu")
        ProductIO.writeProduct(product, filename, "Snaphu")


# input files can be .zip or unzpipped folders
if __name__ == "__main__":
    print("---------------------------------------")
    print('main -- snappy.__file__:', snappy.__file__)
    print("---------------------------------------")
    file_path = "C://Users//lehot//Downloads//snappy-interferogram"

    #should be "after" image
    master_file = os.path.join(file_path,'20191220//manifest.safe')

    #should be "before" image
    slave_file = os.path.join(file_path,'20191208//manifest.safe')

    output= os.path.join(file_path,'test.dim')

    swath = 'IW2'
    polarization = 'VV'
    bursts = ['6,9','7,10']

    Interferogram = Snappy_Utils(master_file, slave_file, swath, polarization, bursts)

    Interferogram.write(Interferogram.gram, output)
