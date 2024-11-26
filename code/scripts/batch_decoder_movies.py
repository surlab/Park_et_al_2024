#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 11 07:53:57 2022

@author: jihopark
"""

"""

"""


import os
import glob
import numpy as np
import pandas as pd

from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import roc_auc_score

#%% Define variables

freqNeuro = 16
nRepeats = 32 # each series of movies is repeated 32 times 
nStim = 7
tOn = 14
tOff = 3
tMovOn = 2
tRepeat = tOn + tOff 

nTrials = nStim * nRepeats

t = 544

labels = ['1','2','3','4','5','6','7'] * nRepeats
# Save all data on the Google Drive from now on 

decoderFolder = os.path.join('/Users','jihopark','Google Drive','My Drive','mrcuts','analysis','decoder','')
saveFolder = os.path.join('/Users','jihopark','Google Drive','My Drive','mrcuts','analysis','decoder','auc_movies','')

anFolder = os.path.join('/Users','jihopark','Google Drive','My Drive','mrcuts','analysis','')

dataFolder = os.path.join('/Users','jihopark','Google Drive','My Drive','mrcuts','analysis','new','')

# Search for CSV files within subfolders
csvFiles = glob.glob(dataFolder + '**/*mov_neuro.csv', recursive=True)


#%% SVM-decoder 

param_grid = {'C': [10**-3,10**-2,10**-1,1,10**1,10**2,10**3]}

test_size = 0.33

# Define function to fit SVM model and compute AUC score
def fit_svm(X_train, y_train, X_test, y_test):
    # Optimizing 
    grid = GridSearchCV(SVC(),param_grid,refit=True,verbose=0)
    grid.fit(X_train,y_train)
    # print(grid.best_estimator_)
    svm = SVC(kernel='linear', probability=True, decision_function_shape='ovo',C=grid.best_params_['C'])
    svm.fit(X_train, y_train)
    y_pred = svm.predict_proba(X_test)
    auc_score = roc_auc_score(y_test, y_pred, multi_class='ovo')
    # Compute predictive probabilities on test data
    return auc_score, y_pred

#%%

# For loop to process each CSV file
for csvFile in csvFiles:
    print('Loading %s' % (csvFile))
    # Read CSV file
    dFF = pd.read_csv(csvFile, header=None)
    dFF.drop(0, inplace=True)
    data = dFF.to_numpy()
    data = np.transpose(data)
    sessionName = csvFile[-34:-4]
    date = csvFile[-34:-28]
    animalID = csvFile[-27:-19]

    # Reconstruct the dataset to make the trials by labels (time window = 2)
    nUnits = np.shape(data)[1]
    matrix = np.zeros([int(nUnits), int(nRepeats), (int(tRepeat) * int(freqNeuro))])
    print('nUnits=%s'%(nUnits))

    for i in range(nUnits):
        for j in range(nRepeats):
            hold = data[:, i]
            matrix[i, j, :] = hold[j * 272:(j + 1) * 272].T

    unitByRepeat = matrix
    unitDuringOff = unitByRepeat[:, :, 0:freqNeuro * tOff]
    unitDuringOn = unitByRepeat[:, :, freqNeuro * tOff:]
    unitConcat = np.reshape(unitDuringOn, (nUnits, 32 * 224))

    # Find the average neural response for each movie (trial)
    unitByTrial = np.reshape(unitConcat, (nUnits, (freqNeuro * tOn), nRepeats))
    # unitAvgPerTrial = np.mean(unitByTrial, axis=2)
    # samples = unitAvgPerTrial.T

    # For extracting data only last 1s window for decoding
    tWindow = 1
    matrix = np.zeros([int(nUnits), int(nTrials), int(tWindow * freqNeuro)])

    for i in range(nUnits):
        for j in range(nTrials):
            hold = unitByTrial[i, j, :]
            matrix[i, j, :] = hold[int(tWindow * freqNeuro):].T

    unitByTrial2 = matrix
    unitAvgPerTrial2 = np.mean(unitByTrial2, axis=2)
    samples = unitAvgPerTrial2.T

    # For loop to generate AUC scores (n_nIters, tr_nIters)
    testn = list(range(5, int(nUnits), 5))

    n_nIters = 250
    tr_nIters = 100
    results_auc = np.zeros([len(testn), n_nIters, tr_nIters])
    results_probs = np.zeros([n_nIters, tr_nIters, 74, 7])

    for nt in range(len(testn)):
        n = testn[nt]

        for j in range(n_nIters):
            if j % 10 == 0:
                print('Iterating %s th time during population size = %s' % (j, n))

            np.random.seed(j)
            idx_pre = np.random.choice(np.arange(nUnits), n)

            for i in range(tr_nIters):
                X_train, X_test, y_train, y_test = train_test_split(samples[:, idx_pre], labels, test_size=test_size,
                                                                    random_state=i, stratify=labels)
                auc_score, y_pred = fit_svm(X_train, y_train, X_test, y_test)
                results_auc[nt, j, i] = auc_score
                results_probs[j, i, :, :] = y_pred

                #Save results into a dataframe 

    resultsDF = pd.DataFrame()
    
    for nt in range(len(testn)):
        for j in range(n_nIters):
            hold = pd.DataFrame()
            hold['AUC'] = results_auc[nt,j,:] 
            hold['neuIteration'] = j
            hold['Pop Size'] = testn[nt]
            hold['trialIteration'] = np.arange(tr_nIters)
            hold['N'] = nUnits
            hold['Session'] = sessionName
            hold['Date'] = date
            hold['Animal'] = animalID
                        
            resultsDF = pd.concat([resultsDF, hold], ignore_index=True)
            
    fileName = sessionName + '_auc_scores.csv'    
   
    resultsDF.to_csv(saveFolder+fileName)
        
    print('resultsDF saved for %s' % (sessionName))

#%%                    
resultsDF['Date'] = resultsDF['Date'].astype(str)

def get_timepoint(date_value):
    if date_value == '230116' or date_value == '230117' or date_value == '230118' or date_value == '230120' or date_value == '221005' or date_value == '221006' or date_value == '221123' or date_value == '221126':
        return 'PRE'
    elif date_value == '230202':
        return 'POST (~1wk)'
    elif date_value == '230208' or date_value == '230209' or date_value == '230211' or date_value == '221214' or date_value == '221216' or date_value == '221025' or date_value == '221026':
        return 'POST (~2wk)'
    elif date_value == '230218' or date_value == '230219' or date_value == '221222' or date_value == '221110' or date_value == '221108' or date_value == '221109':
        return 'POST (~3wk)'
    else:
        return None
    
    
def get_group(anID):
    if anID == 'mrcut316' or anID == 'mrcut318' or anID == 'mrcuts07':
        return 'Control'
    elif anID == 'mrcut317' or anID == 'mrcuts13' or anID == 'mrcuts14' or anID == 'mrcuts15' or anID == 'mrcuts16' or anID == 'mrcuts17':
        return 'Exp'
    else:
        return None

resultsDF['Timepoint'] = resultsDF['Date'].apply(get_timepoint)
resultsDF['Group'] = resultsDF['Animal'].apply(get_group)

fileName = 'mov_auc_scores_2.csv'    

os.chdir(decoderFolder)    
resultsDF.to_csv(fileName)