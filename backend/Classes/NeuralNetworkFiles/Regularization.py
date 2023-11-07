import base64

import pandas as pd
import numpy as np

from backend.Classes.NeuralNetworkFiles import Layer
from backend.Classes import HyperParameters

import matplotlib.pyplot as plt

from tensorflow import keras

# Create a list of core layers to select from.
list_Regularization = []

def getRegularization():
    return list_Regularization

## Dropout Layer
Name = "Dropout"
Display_Name = "Dropout"
Definition = ['Applies Dropout to the input.\n\nThe Dropout layer randomly sets input units to 0 with a frequency of rate at each step during training time, which helps prevent overfitting. Inputs not set to 0 are scaled up by 1/(1 - rate) such that the sum over all inputs is unchanged.\n\nNote that the Dropout layer only applies when training is set to True such that no values are dropped during inference. When using model.fit, training will be appropriately set to True automatically, and in other contexts, you can set the kwarg explicitly to True when calling the layer.'],

Parameter_0 = {"Name":"rate", 
               "Type": ["float"], 
               "Default_option":"", 
               "Default_value":"", 
               "Possible":["float"],
             "Definition":"Float between 0 and 1. Fraction of the input units to drop."}

# Only allows one number to reshape into a 1d array of (number, )
# may have to allow for more dimentions later.
Parameter_1 = {"Name":"noise_shape", 
               "Type": ["int"], 
               "Default_option":"", 
               "Default_value":"", 
               "Possible":["int"],
             "Definition":"1D integer tensor representing the shape of the binary dropout mask that will be multiplied with the input. For instance, if your inputs have shape (batch_size, timesteps, features) and you want the dropout mask to be the same for all timesteps, you can use noise_shape=(batch_size, 1, features)."}

Parameter_2 = {"Name":"seed", 
               "Type": ["int"], 
               "Default_option":"", 
               "Default_value":"", 
               "Possible":["int"],
             "Definition":"A Python integer to use as random seed."}

Parameters = {"Parameter_0":Parameter_0, "Parameter_1":Parameter_1, "Parameter_2":Parameter_2}

list_Regularization.append(Layer.Layer(Name, Display_Name, Definition, Parameters))

## NEW LAYER

def create_Layer(data, i):
    # get layer name
    layer = data["Layer_" + str(i)]

    # get the chosen settings for the layer
    Parameters = HyperParameters.getParameters(data["Layer_" + str(i)], list_Regularization)
    settings = HyperParameters.getSettings(data, Parameters, i, Layer.getName())

    new_layer = ""

    ## Dropout Layer
    if layer == "Dropout":

        # Create the layer
        new_layer = keras.layers.Dropout(rate=settings["Parameter_0"], noise_shape=settings["Parameter_1"], seed=settings["Parameter_2"])

        
    return new_layer