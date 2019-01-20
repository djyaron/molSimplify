## @file nn_prep.py
#  Helper routines for ANN integration
#  
#   Written by Nick Yang for HJK Group
#  
#  Dpt of Chemical Engineering, MIT

from molSimplify.Classes import *
from molSimplify.Informatics.autocorrelation import *
from molSimplify.Informatics.graph_analyze import *
from molSimplify.Informatics.partialcharges import *
from molSimplify.Classes.mol3D import *
from molSimplify.Classes.globalvars import *
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.kernel_ridge import KernelRidge
from sklearn.multioutput import MultiOutputRegressor
from math import exp
import numpy as np
import csv, glob, os, copy, pickle
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker
numpy.seterr(divide = 'ignore')

csvf = '/Users/tzuhsiungyang/Dropbox (MIT)/Work at the Kulik group/ts_build/Data/xyzf_optts/selected_xyzfs/label_1distance_descs_atRACs.csv'
colnum_i_label = 1
colnum_j_label = 2
colnum_desc = 2

def feature_prep(mol, idx):
    # setting up variables
    fidx_list = []
    sidx_list = []
    satno_list = []
    ref_list = []
    fd_list = []
    fa_list = []
    idx_list = [0] * 6
    exit_signal = True
    # getting bond-order matrix
    mol.convert2OBMol()
    BOMatrix = mol.populateBOMatrix()

    # preping for the loop
    fidx_list.append(mol.findMetal())
    for i in range(len(fidx_list)):
        for fidx in fidx_list[i]:
            for sidx in mol.getBondedAtoms(fidx):
                sidx_list.append([sidx])

    for i in range(len(fidx_list)):
        for fidx in fidx_list[i]:
            for j in range(len(sidx_list)):
                for sidx in sidx_list[j]:
                    BO = int(BOMatrix[fidx][sidx])
                    if BO == 0:
                        BO = 1
                    satno_str = str(mol.getAtom(sidx).atno)
                    satno_list.append(int(BO * satno_str))

    for satno in set(satno_list):
        satnocount = satno_list.count(satno)
        if satnocount > 1:
            s_sel_list = [i for i,atno in enumerate(satno_list) if atno is satno]
            exit_signal = False

    for i in range(len(fidx_list)):
        for fidx in fidx_list[i]:
            ref_list.append(fidx)

    # starting the loop
    tidx_list = []
    tatno_list = []
    for i in range(len(sidx_list)):
        tidx_list.append([])
        tatno_list.append([])

    while not exit_signal:
        fpriority_list = []
        for i in s_sel_list:
            t_list = []
            for sidx in sidx_list[i]:
                for tidx in mol.getBondedAtoms(sidx):
                    if tidx not in ref_list:
                        t_list.append(tidx)
            tidx_list[i] = t_list
        # print(sidx_list)
        # print(tidx_list)
        for i in s_sel_list:
            for sidx in sidx_list[i]:
                atno_list = tatno_list[i]
                ls = []
                for j in s_sel_list:
                    for tidx in tidx_list[j]:
                        BO = int(BOMatrix[sidx][tidx])
                        tatno_str = str(mol.getAtom(tidx).atno)
                        ls.append(BO * tatno_str)
                sorted(ls,reverse=True)
                for j in ls:
                    atno_list.append(j)
                a = ''.join(atno_list)
            tatno_list[i] = [a]
        sidx_list = []
        for i in range(len(tidx_list)):
            sidx_list.append(tidx_list[i])
        for i in s_sel_list:
            for sidx in sidx_list[i]:
                ref_list.append(sidx)
        test_list = []
        for i in range(len(sidx_list)):
            test_list.append([])
        # get priorities
        for i in range(len(satno_list)):
            atno_list = []
            atno_list.append(str(satno_list[i]))
            if tatno_list[i] == []:
                atno_list.append('')
            else:
                atno_list.append(tatno_list[i][0])
            a = '.'.join(atno_list)
            fpriority_list.append(float(a))
        if tidx_list == test_list or len(set(fpriority_list)) == 6:
        # if tidx_list == test_list:
            exit_signal = True
    # get distance
    # idx = np.argsort(np.array(fpriority_list))[-1]
    sidx_list = mol.getBondedAtomsByCoordNo(fidx_list[0][0], 6)
    refcoord = mol.getAtom(sidx_list[idx]).coords()
    mcoord = mol.getAtom(fidx_list[0][0]).coords()
    vMLs = [vecdiff(mcoord, mol.getAtom(i).coords()) for i in sidx_list]
    rMLs = [distance(mcoord, mol.getAtom(i).coords()) for i in sidx_list]
    idx0 = idx
    vangs = [vecangle(vML, vMLs[idx0]) for vML in vMLs]
    idxes = range(6)
    idx5 = np.argsort(np.array(vangs))[-1]
    idx1_4 = copy.deepcopy(idxes)
    idx1_4.remove(idx0)
    idx1_4.remove(idx5)
    fprio1_4 = copy.deepcopy(fpriority_list)
    vMLs1_4 = copy.deepcopy(vMLs)
    rMLs1_4 = copy.deepcopy(rMLs)
    if idx0 > idx5:
        fprio1_4.pop(idx0)
        fprio1_4.pop(idx5)
        vMLs1_4.pop(idx0)
        vMLs1_4.pop(idx5)
        rMLs1_4.pop(idx0)
        rMLs1_4.pop(idx5)
    else:
        fprio1_4.pop(idx5)
        fprio1_4.pop(idx0)
        vMLs1_4.pop(idx5)
        vMLs1_4.pop(idx0)
        rMLs1_4.pop(idx5)
        rMLs1_4.pop(idx0)
    # get ax, eq, ax idxes
    idx1_ = np.argsort(np.array(fprio1_4))[-1]
    idx1 = idx1_4[idx1_]
    vangs1_4 = [vecangle(vML, vMLs1_4[idx1_]) for vML in vMLs1_4]
    idx2_ = np.argsort(np.array(vangs1_4))[-1]
    idx2 = idx1_4[idx2_]
    idx3_4 = copy.deepcopy(idx1_4)
    fprio3_4 = copy.deepcopy(fprio1_4)
    idx3_4.remove(idx1)
    idx3_4.remove(idx2)
    if idx1_ > idx2_:
        fprio3_4.pop(idx1_)
        fprio3_4.pop(idx2_)
    else:
        fprio3_4.pop(idx2_)
        fprio3_4.pop(idx1_)
    idx3 = idx3_4[np.argsort(np.array(fprio3_4))[-1]]
    idx3_4.remove(idx3)
    idx4 = idx3_4[0]
    idx_list = [idx0,idx1,idx2,idx3,idx4,idx5]
    fpriority_list = np.array(fpriority_list)[idx_list].tolist()
    fd_list = np.array(rMLs)[idx_list].tolist()

    return fpriority_list, fd_list, idx_list

def normalize(data, mean, std):
    data = np.array(data)
    mean = np.array(mean)
    std = np.array(std)
    data_norm = np.divide((data - mean), std, out=np.zeros_like(data - mean), where=std!=0)
    # data_norm = np.nan_to_num(data_norm)

    return data_norm

## predict labels using krr with a given csv file
#  @param csvf the csv file containing headers (first row), data, and label
#  @param colnum_label the column number for the label column
#  @param colnum_desc the starting column number for the descriptor columns
#  @return y_train_data, y_train_pred, y_test_data, y_test_pred, score
def krr_model_training(csvf, colnum_label, colnum_desc, alpha=1, gamma=1):
    # read in desc and label
    f = open(csvf, 'r')
    fcsv = csv.reader(f)
    headers = np.array(next(f, None).rstrip('\r\n').split(','))[colnum_desc:]
    X = []
    y = []
    lines = [line for line in fcsv]
    lnums = [len(line) for line in lines]
    count = max(set(lnums), key=lnums.count)
    for line in lines:
        if len(line) == count:
            descs = []
            for desc in line[colnum_desc:]:
                descs.append(float(desc))
            X.append(descs)
            y.append(float(line[colnum_label]))
    X = np.array(X)
    y = np.array(y)
    ## process desc and label
    mean_X = np.mean(X, axis=0)
    std_X = np.std(X, axis=0)
    mean_y = np.mean(y, axis=0)
    std_y = np.std(y, axis=0)
    X_norm = normalize(X, mean_X, std_X)
    y_norm = normalize(y, mean_y, std_y)
    # stats
    mean_X_dict = dict(zip(headers, mean_X))
    std_X_dict = dict(zip(headers, std_X))
    stat_names = ['mean_X_dict', 'std_X_dict', 'mean_y', 'std_y']
    stats = [mean_X_dict, std_X_dict, mean_y, std_y]
    stat_dict = dict(zip(stat_names, stats))
    X_norm = normalize(X, mean_X, std_X)
    y_norm = normalize(y, mean_y, std_y)
    # split to train and test
    X_norm_train, X_norm_test, y_norm_train, y_norm_test = train_test_split(X_norm, y_norm, test_size=0.2, random_state=0)
    ## end
    # feature selection
    selector = RandomForestRegressor(random_state=0, n_estimators=100)
    selector.fit(X_norm_train, y_norm_train)
    X_norm_train_impts = selector.feature_importances_
    idxes = np.where(X_norm_train_impts > 0.001)[0]
    print(len(idxes))
    importances = X_norm_train_impts[idxes]
    features_sel = headers[idxes]
    # importance
    impt_dict = dict(zip(features_sel, importances))
    X_norm_train_sel = X_norm_train.T[idxes].T
    X_norm_test_sel = X_norm_test.T[idxes].T
    ## training with krr
    signal = True
    # krr parameters
    kernel = 'rbf'
    factor_lower = -4
    factor_higher = 4
    gamma_lower = gamma * exp(factor_lower)
    gamma_higher = gamma * exp(factor_higher)
    alpha_lower = alpha * exp(factor_lower)
    alpha_higher = alpha * exp(factor_higher)
    lin = 7
    # optimize hyperparameters
    while gamma == 1 or alpha == 1 or signal == False:
        gammas = np.linspace(gamma_lower, gamma_higher, lin)
        alphas = np.linspace(alpha_lower, alpha_higher, lin)
        tuned_parameters = [{'kernel': [kernel], 'gamma': gammas, 'alpha': alphas}]
        regr = GridSearchCV(KernelRidge(), tuned_parameters, cv=5, scoring='neg_mean_absolute_error')
        regr.fit(X_norm_train_sel, y_norm_train)
        gamma = regr.best_params_['gamma']
        alpha = regr.best_params_['alpha']
        if (gamma < gammas[lin / 2 - 1] or gamma > gammas[lin / 2]) or \
            (alpha < alphas[lin / 2 - 1] or alpha > alphas[lin / 2]):
            signal = False
            factor_lower *= 0.5
            factor_higher *= 0.5
            gamma_lower = gamma * exp(factor_lower)
            gamma_higher = gamma * exp(factor_higher)
            alpha_lower = alpha * exp(factor_lower)
            alpha_higher = alpha * exp(factor_higher)
        else:
            signal = True
        print('gamma is: ', gamma, '. alpha is: ', alpha)
    # final model
    regr = KernelRidge(kernel=kernel, alpha=alpha, gamma=gamma)
    regr.fit(X_norm_train_sel, y_norm_train)
    # predictions
    y_norm_train_pred = regr.predict(X_norm_train_sel)
    y_train_pred = y_norm_train_pred * std_y + mean_y
    y_train_data = y_norm_train * std_y + mean_y
    y_norm_test_pred = regr.predict(X_norm_test_sel)
    y_test_pred = y_norm_test_pred * std_y + mean_y
    y_test_data = y_norm_test * std_y + mean_y
    # data
    train_names = ['X_norm_sel_dict', 'y_data', 'y_pred']
    X_norm_train_sel_names = features_sel
    X_norm_train_sel_dict = dict(zip(X_norm_train_sel_names, X_norm_train_sel.T))
    trains = [X_norm_train_sel_dict, y_train_data, y_train_pred]
    train_dict = dict(zip(train_names, trains))
    test_names = ['X_norm_sel_dict', 'y_data', 'y_pred']
    X_norm_test_sel_names = features_sel
    X_norm_test_sel_dict = dict(zip(X_norm_test_sel_names, X_norm_test_sel.T))
    tests = [X_norm_test_sel_dict, y_test_data, y_test_pred]
    test_dict = dict(zip(test_names, tests))
    # performance
    score_train = regr.score(X_norm_train_sel, y_norm_train)
    score_test = regr.score(X_norm_test_sel, y_norm_test)
    MAE_train = mean_absolute_error(y_train_data, y_train_pred)
    MAE_test = mean_absolute_error(y_test_data, y_test_pred)
    perm_names = ['score_train', 'score_test', 'MAE_train', 'MAE_test']
    perms = [score_train, score_test, MAE_train, MAE_test]
    perm_dict = dict(zip(perm_names, perms))

    return stat_dict, impt_dict, train_dict, test_dict, perm_dict, regr

## predict labels using gradient boosting regressor (GBR) with a given csv file
#  @param csvf the csv file containing headers (first row), data, and label
#  @param colnum_i_label the starting column number for the label column
#  @param colnum_j_label the ending column number for the label column + 1
#  @param colnum_desc the starting column number for the descriptor columns
#  @return y_train_data, y_train_pred, y_test_data, y_test_pred, score
def gbr_model_training(csvf, colnum_i_label, colnum_j_label, colnum_desc):
    # read in desc and label
    f = open(csvf, 'r')
    fcsv = csv.reader(f)
    headers = np.array(next(f, None).rstrip('\r\n').split(','))[colnum_desc:]
    X = []
    y = []
    lines = [line for line in fcsv]
    lnums = [len(line) for line in lines]
    count = max(set(lnums), key=lnums.count)
    for line in lines:
        if len(line) == count:
            descs = []
            labels = []
            for desc in line[colnum_desc:]:
                descs.append(float(desc))
            for label in line[colnum_i_label:colnum_j_label]:
                labels.append(float(label))
            X.append(descs)
            y.append(labels)
    X = np.array(X)
    y = np.array(y)
    ## process desc and label
    mean_X = np.mean(X, axis=0)
    std_X = np.std(X, axis=0)
    mean_y = np.mean(y, axis=0)
    std_y = np.std(y, axis=0)
    # stats
    mean_X_dict = dict(zip(headers, mean_X))
    std_X_dict = dict(zip(headers, std_X))
    stat_names = ['mean_X_dict', 'std_X_dict', 'mean_y', 'std_y']
    stats = [mean_X_dict, std_X_dict, mean_y, std_y]
    stat_dict = dict(zip(stat_names, stats))
    X_norm = normalize(X, mean_X, std_X)
    y_norm = normalize(y, mean_y, std_y)
    # split to train and test
    X_norm_train, X_norm_test, y_norm_train, y_norm_test = train_test_split(X_norm, y_norm, test_size=0.2, random_state=0)
    ## end
    # feature selection
    selector = RandomForestRegressor(random_state=0, n_estimators=100)
    selector.fit(X_norm_train, y_norm_train.T[0])
    X_norm_train_impts = selector.feature_importances_
    scores = []
    results = []
    thresholds = np.logspace(-2,-2,1)
    for threshold in thresholds:
        idxes = np.where(X_norm_train_impts > threshold)[0]
        importances = X_norm_train_impts[idxes]
        features_sel = headers[idxes]
        # importance
        impt_dict = dict(zip(features_sel, importances))
        # idxes = range(len(X_norm_train.T))
        X_norm_train_sel = X_norm_train.T[idxes].T
        X_norm_test_sel = X_norm_test.T[idxes].T
        ## training with gbr
        regr = MultiOutputRegressor(GradientBoostingRegressor(random_state=0))
        # final model
        regr.fit(X_norm_train_sel, y_norm_train)
        # predictions
        y_norm_train_pred = regr.predict(X_norm_train_sel)
        y_train_pred = y_norm_train_pred * std_y + mean_y
        y_train_data = y_norm_train * std_y + mean_y
        y_norm_test_pred = regr.predict(X_norm_test_sel)
        y_test_pred = y_norm_test_pred * std_y + mean_y
        y_test_data = y_norm_test * std_y + mean_y
        # data
        train_names = ['X_norm_sel_dict', 'y_data', 'y_pred']
        X_norm_train_sel_names = features_sel
        X_norm_train_sel_dict = dict(zip(X_norm_train_sel_names, X_norm_train_sel.T))
        trains = [X_norm_train_sel_dict, y_train_data, y_train_pred]
        train_dict = dict(zip(train_names, trains))
        test_names = ['X_norm_sel_dict', 'y_data', 'y_pred']
        X_norm_test_sel_names = features_sel
        X_norm_test_sel_dict = dict(zip(X_norm_test_sel_names, X_norm_test_sel.T))
        tests = [X_norm_test_sel_dict, y_test_data, y_test_pred]
        test_dict = dict(zip(test_names, tests))
        # performance
        score_train = regr.score(X_norm_train_sel, y_norm_train)
        score_test = regr.score(X_norm_test_sel, y_norm_test)
        MAE_train = mean_absolute_error(y_train_data, y_train_pred)
        MAE_test = mean_absolute_error(y_test_data, y_test_pred)
        perm_names = ['score_train', 'score_test', 'MAE_train', 'MAE_test']
        perms = [score_train, score_test, MAE_train, MAE_test]
        perm_dict = dict(zip(perm_names, perms))
        scores.append(score_test)
        results.append([stat_dict, impt_dict, train_dict, test_dict, perm_dict, regr])
    idx = np.argsort(np.array(scores))[-1]
    stat_dict = results[idx][0]
    impt_dict = results[idx][1]
    train_dict = results[idx][2]
    test_dict = results[idx][3]
    perm_dict = results[idx][4]
    regr = results[idx][5]

    return stat_dict, impt_dict, train_dict, test_dict, perm_dict, regr

## predict labels using a given regr
#  @param core3D mol3D class of a molecule
#  @param spin the spin multiplicity of the core3D
#  @param train_dict th dictionary that contains the training data
#  @param stat_dict the dictionary that contains the statistics of the training data (e.g. mean, std)
#  @param impt_dict the dictionary that contains the important features
#  @param regr the regression model
#  @return bondl_dict, ds (a list of Euclidean distances)
def ML_model_predict(core3D, spin, train_dict, stat_dict, impt_dict, regr):
    bondl_keys = []
    bondls = []
    spin_ohe = [0] * 6
    spin_ohe[spin - 1] = 1
    mean_y = stat_dict['mean_y']
    std_y = stat_dict['std_y']
    mean_X_dict = stat_dict['mean_X_dict']
    std_X_dict = stat_dict['std_X_dict']
    midxes = core3D.findMetal()
    Xs_train = train_dict['X_norm_sel_dict']
    for midx in midxes:
        matno = core3D.getAtom(midx).atno
        fidxes = core3D.getBondedAtoms(midx)
        for fidx_i, fidx in enumerate(fidxes):
            fprio_list, fd_list, idx_list = feature_prep(core3D, fidx_i)
            descs = []
            desc_names = []
            descs.append(matno)
            desc_names.append('matno_0')
            descs += spin_ohe
            for i in range(len(spin_ohe)):
                desc_names.append('spin' + str(i) + '_ohe')
            for idx_i, idx in enumerate(idx_list):
                fidx_ = fidxes[idx]
                descriptor_names, descriptors = get_descriptor_vector_for_atidx(core3D, fidx_)
                for descriptor_name in descriptor_names:
                    desc_names.append(descriptor_name + '_' + str(idx_i))
                descs += descriptors
            desc_dict = dict(zip(desc_names, descs))
            descs = []
            Xs_train_sel = []
            d2s = [0] * len(Xs_train.values()[0])
            for key in impt_dict.keys():
                desc = np.divide((desc_dict[key] - mean_X_dict[key]), std_X_dict[key], out=np.zeros_like(desc_dict[key] - mean_X_dict[key]), where=std_X_dict[key]!= 0)
                descs.append(desc)
                X_train = Xs_train[key]
                Xs_train_sel.append(X_train.tolist())
                # d2s = d2s + np.square(np.array(desc * len(X_train)) - np.array(X_train))
            # print('The largest desc is ' + str(max(descs)))
            # ds = np.sqrt(d2s)
            ds = []
            for i in range(len(Xs_train_sel[0])):
                d = np.linalg.norm(np.array(descs) - np.array(Xs_train_sel).T[i])
                ds.append(np.linalg.norm(d))
            bondl = regr.predict([descs]) * std_y + mean_y
            bondl_keys.append(fidx)
            bondls.append(bondl)
    bondl_dict = dict(zip(bondl_keys, bondls))

    return bondl_dict, ds

## predict labels using a given regr
#  @param core3D mol3D class of a molecule
#  @param spin the spin multiplicity of the core3D
#  @param mligcaomt the external atom index of the mlig
#  @return bondl_dict, ds (a list of Euclidean distances)
def krr_model_predict(core3D, spin, mligcatom):
    bondl_keys = []
    bondls = []
    spin_ohe = [0] * 6
    spin_ohe[spin - 1] = 1
    globs = globalvars()
    if globs.custom_path: # test if a custom path is used:
        fpath = str(globs.custom_path).rstrip('/') + "/python_krr"
    else:
        fpath = resource_filename(Requirement.parse("molSimplify"),"molSimplify/python_krr")
    # load model
    f_model = fpath + '/hat_krr_model.pkl'
    f = open(f_model,'rb')
    regr = pickle.load(f)
    Xs_train = regr.X_fit_
    ## load stats
    # y stats
    f_stats = fpath + '/hat_y_mean_std.csv'
    f = open(f_stats, 'r')
    fcsv = csv.reader(f)
    for i, line in enumerate(fcsv):
        if i == 1:
            mean_y = float(line[0])
            std_y = float(line[1])
    # x stats
    f_stats = fpath + '/hat_X_mean_std.csv'
    f = open(f_stats, 'r')
    fcsv = csv.reader(f)
    for i, line in enumerate(fcsv):
        if i == 0:
            feature_names = line
        if i == 1:
            mean_X = [float(ele) for ele in line]
        if i == 2:
            std_X = [float(ele) for ele in line]
    mean_X_dict = dict(zip(feature_names, mean_X))
    std_X_dict = dict(zip(feature_names, std_X))
    # load feature names
    f_stats = fpath + '/hat_feature_names.csv'
    f = open(f_stats, 'r')
    fcsv = csv.reader(f)
    for i, line in enumerate(fcsv):
        keys = line
    ## rOH
    # load model2
    f_model = fpath + '/hat2_krr_model.pkl'
    f = open(f_model,'rb')
    regr2 = pickle.load(f)
    X2s_train = regr2.X_fit_
    ## load stats
    # y2 stats
    f_stats = fpath + '/hat2_y_mean_std.csv'
    f = open(f_stats, 'r')
    fcsv = csv.reader(f)
    for i, line in enumerate(fcsv):
        if i == 1:
            mean_y2 = float(line[0])
            std_y2 = float(line[1])
    # x2 stats
    f_stats = fpath + '/hat2_X_mean_std.csv'
    f = open(f_stats, 'r')
    fcsv = csv.reader(f)
    for i, line in enumerate(fcsv):
        if i == 0:
            feature2_names = line
        if i == 1:
            mean_X2 = [float(ele) for ele in line]
        if i == 2:
            std_X2 = [float(ele) for ele in line]
    mean_X2_dict = dict(zip(feature_names, mean_X))
    std_X2_dict = dict(zip(feature_names, std_X))
    # load feature2 names
    f_stats = fpath + '/hat2_feature_names.csv'
    f = open(f_stats, 'r')
    fcsv = csv.reader(f)
    for i, line in enumerate(fcsv):
        keys2 = line
    # # get train data
    # Xs_train_sel = []
    # f_X_train = '/Users/tzuhsiungyang/Dropbox (MIT)/Work at the Kulik group/ts_build/Data/xyzf_optts/selected_xyzfs/hat_krr_X_train.csv'
    # f = open(f_X_train, 'r')
    # fcsv = csv.reader(f)
    # for line in fcsv:
    #     Xs_train.append([float(ele) for ele in line])
    # # get kernel space coefs
    # coefs = []
    # f_coef = '/Users/tzuhsiungyang/Dropbox (MIT)/Work at the Kulik group/ts_build/Data/xyzf_optts/selected_xyzfs/hat_krr_dual_coef.csv'
    # f = open(f_coef, 'r')
    # fcsv = csv.reader(f)
    # for line in fcsv:
    #     coefs = [float(ele) for ele in line]
    # get features
    midxes = core3D.findMetal()
    for midx in midxes:
        matno = core3D.getAtom(midx).atno
        fidxes = core3D.getBondedAtoms(midx)
        ds1 = []
        for fidx_i, fidx in enumerate(fidxes):
            fprio_list, fd_list, idx_list = feature_prep(core3D, fidx_i)
            descs = []
            desc_names = []
            descs.append(matno)
            desc_names.append('matno_0')
            descs += spin_ohe
            for i in range(len(spin_ohe)):
                desc_names.append('spin' + str(i) + '_ohe')
            for idx_i, idx in enumerate(idx_list):
                fidx_ = fidxes[idx]
                descriptor_names, descriptors = get_descriptor_vector_for_atidx(core3D, fidx_)
                for descriptor_name in descriptor_names:
                    desc_names.append(descriptor_name + '_' + str(idx_i))
                descs += descriptors
            desc_dict = dict(zip(desc_names, descs))
            descs = []
            Xs_train_sel = []
            d2s = [0] * len(Xs_train[0])
            for key in keys:
                desc = np.divide((desc_dict[key] - mean_X_dict[key]), std_X_dict[key], out=np.zeros_like(desc_dict[key] - mean_X_dict[key]), where=std_X_dict[key]!= 0)
                descs.append(desc)
                # d2s = d2s + np.square(np.array(desc * len(X_train)) - np.array(X_train))
            # print('The largest desc is ' + str(max(descs)))
            # ds = np.sqrt(d2s)
            ds = []
            for i in range(len(Xs_train[0])):
                d = np.linalg.norm(np.array(descs) - np.array(Xs_train)[i])
                ds.append(d)
            ds1.append(ds)
            bondl = regr.predict([descs]) * std_y + mean_y
            bondl_keys.append(fidx)
            bondls.append(bondl)
            if fidx == mligcatom:
                descs = []
                d2s = [0] * len(X2s_train[0])
                for key in keys2:
                    desc = np.divide((desc_dict[key] - mean_X2_dict[key]), std_X2_dict[key],
                                     out=np.zeros_like(desc_dict[key] - mean_X2_dict[key]), where=std_X2_dict[key] != 0)
                    descs.append(desc)
                    # d2s = d2s + np.square(np.array(desc * len(X_train)) - np.array(X_train))
                # print('The largest desc is ' + str(max(descs)))
                # ds = np.sqrt(d2s)
                ds2 = []
                for i in range(len(X2s_train[0])):
                    d2 = np.linalg.norm(np.array(descs) - np.array(X2s_train)[i])
                    ds2.append(d2)
                bondl2 = regr2.predict([descs]) * std_y2 + mean_y2

    bondl_dict = dict(zip(bondl_keys, bondls))

    return bondl_dict, bondl2, ds1, ds2

# ## predict labels using gradient boosting regressor (GBR) with a given csv file
# #  @param csvf the csv file containing headers (first row), data, and label
# #  @param colnum_i_label the starting column number for the label column
# #  @param colnum_j_label the ending column number for the label column + 1
# #  @param colnum_desc the starting column number for the descriptor columns
# #  @return y_train_data, y_train_pred, y_test_data, y_test_pred, score
# def krr_model_predict(core3D, spin, stat_dict, impt_dict, regr):
#     bondl_keys = []
#     bondls = []
#     spin_ohe = [0] * 6
#     spin_ohe[spin - 1] = 1
#     mean_y = stat_dict['mean_y']
#     std_y = stat_dict['std_y']
#     mean_X = stat_dict['mean_X']
#     std_X = stat_dict['std_X']
#     midxes = core3D.findMetal()
#     for midx in midxes:
#         matno = core3D.getAtom(midx).atno
#         fidxes = core3D.getBondedAtoms(midx)
#         for fidx_i, fidx in enumerate(fidxes):
#             fprio_list, fd_list, idx_list = feature_prep(core3D, fidx_i)
#             descs = []
#             desc_names = []
#             descs.append(matno)
#             desc_names.append('matno_0')
#             descs += spin_ohe
#             for i in range(len(spin_ohe)):
#                 desc_names.append('spin' + str(i) + '_ohe')
#             for idx_i, idx in enumerate(idx_list):
#                 fidx_ = fidxes[idx]
#                 descriptor_names, descriptors = get_descriptor_vector_for_atidx(core3D, fidx_)
#                 for descriptor_name in descriptor_names:
#                     desc_names.append(descriptor_name + '_' + str(idx_i))
#                 descs += descriptors
#             normalize(descs, mean_X, std_X)
#             desc_dict = dict(zip(desc_names, descs))
#             descs = []
#             for key in impt_dict.keys():
#                 desc = desc_dict[key]
#                 descs.append(desc)
#             regr.fit()
#             bondl = regr.predict([descs]) * std_y + mean_y
#             bondl_keys.append(fidx)
#             bondls.append(bondl)
#     bondl_dict = dict(zip(bondl_keys, bondls))
#
#     return bondl_dict

## wrapper to get KRR predictions for bondl_core3D, bondl_m3D, bondl_m3Dsub from a known mol3D using partial charges
#  @param mol mol3D of the molecule
#  @param charge charge of the molecule
#  @return KRR-predicted bondl_core3D
#  KRR accuracies for bondl_core3D: 98.2% (training score) and 47.6 (test score)
#  KRR accuracies for bondl_m3D: 99.5% (training score) and 51.1 (test score)
def invoke_KRR_from_mol3d_dQ(mol,charge):
    X_norm_train = []
    y_norm_train = []
    # # find the metal from RACs
    # metal = mol.getAtom(mol.findMetal()[0]).symbol()
    # ox_modifier = {metal:oxidation_state}
    # get partialQs
    feature_names,features = ffeatures(mol,charge)
    # # get one-hot-encoding (OHE)
    # descriptor_names,descriptors = create_OHE(descriptor_names,descriptors, metal,oxidation_state)
    # # set exchange fraction
    # descriptor_names += ['alpha']
    # descriptors += [alpha]
    ## KRR initiation
    # defined variables
    globs = globalvars()
    if globs.custom_path: # test if a custom path is used:
         X_norm_train_csv = str(globs.custom_path).rstrip('/') + "/python_krr/X_norm_train_TS.csv"
         y_norm_train_csv = str(globs.custom_path).rstrip('/') + "/python_krr/y_norm_train_TS.csv"
    else:
        X_norm_train_csv = resource_filename(Requirement.parse("molSimplify"),"molSimplify/python_krr/X_norm_train_TS.csv")
        y_norm_train_csv = resource_filename(Requirement.parse("molSimplify"),"molSimplify/python_krr/y_norm_train_TS.csv")
    f = open(X_norm_train_csv,'r')
    for line in csv.reader(f):
        X_norm_train.append([float(i) for i in line])
    X_norm_train = np.array(X_norm_train)
    f = open(y_norm_train_csv,'r')
    for line in csv.reader(f):
        y_norm_train.append([float(i) for i in line])
    y_norm_train = np.array(y_norm_train)
    # X_norm_train = pd.read_csv(X_norm_train_csv,header=None)
    # y_norm_train = pd.read_csv(y_norm_train_csv,header=None)
    kernel = 'rbf'
    keys = []
    bondls = []
    for targets in ['bondl_core3D','bondl_m3D']:#,'bondl_m3Dsub']:
        keys.append(targets)
        if targets == 'bondl_core3D':
        # KRR parameters for bondl_core3D 
            alpha = 0.1
            gamma = 4.6415888336127775
            mean_y_norm_train = 1.8556069976566096
            std_y_norm_train = 0.08511267085380758
            mean_X_norm_train = np.array([1.1886128903870394, 1.0746595698697274, 1.0089390403652372, 1.0051636435711488, 
                                    0.9639844597149281, 1.5924309727104378])
            std_X_norm_train = np.array([1.4887238067607071, 1.4391120341824508, 1.351343230273359, 1.302911028297482,
                                    1.1511093513567663, 0.7366350688359029])

        if targets == 'bondl_m3D':
        # KRR parameters for bondl_core3D 
            alpha = 0.015848931924611134
            gamma = 8.531678524172808
            mean_y_norm_train = 1.1429284052746633
            std_y_norm_train = 0.04763054722349127
            mean_X_norm_train = np.array([-1.17136495, -1.09058534, -1.04062806, -1.01379334, -0.92612448, -1.30558513])
            std_X_norm_train = np.array([1.36359461, 1.32785945, 1.26392399, 1.21494676, 1.0253893, 0.5940198])

        # model initation
        X_norm_test = np.array(features[7:13])
        X_norm_test = (X_norm_test - mean_X_norm_train) / std_X_norm_train
        model = KernelRidge(kernel=kernel,alpha=alpha,gamma=gamma)
        model.fit(X_norm_train,y_norm_train)
        y_norm_test = model.predict([X_norm_test])
        y_norm_test = y_norm_test * std_y_norm_train + mean_y_norm_train
        bondl = y_norm_test[0][0]
        bondls.append(bondl)
    
    bondl_dict = dict(zip(keys,bondls))

    return bondl_dict

## wrapper to get KRR predictions for bondl_core3D from a known mol3D using RAC-190
#  @param mol mol3D of the molecule
#  @param charge charge of the molecule
#  @return KRR-predicted bondl_core3D
#  KRR accuracies: 98.2% (training score) and 47.6 (test score)
def invoke_KRR_from_mol3d_RACs(mol,charge):
    # # find the metal from RACs 
    # metal = mol.getAtom(mol.findMetal()[0]).symbol()
    # ox_modifier = {metal:oxidation_state}
    # get partialQs
    feature_names,features = ffeatures(mol,charge)
    # # get one-hot-encoding (OHE)
    # descriptor_names,descriptors = create_OHE(descriptor_names,descriptors, metal,oxidation_state)
    # # set exchange fraction
    # descriptor_names += ['alpha']
    # descriptors += [alpha]
    ## KRR initiation
    # defined variables
    X_norm_train = pd.read_csv('/Users/tzuhsiungyang/anaconda2/envs/molSimplify/molSimplify/molSimplify/python_krr/X_norm_train_TS.csv',header=None)
    y_norm_train = pd.read_csv('/Users/tzuhsiungyang/anaconda2/envs/molSimplify/molSimplify/molSimplify/python_krr/y_norm_train_TS.csv',header=None)
    kernel = 'rbf'
    alpha = 0.1
    gamma = 4.6415888336127775
    mean_y_norm_train = 1.8556069976566096
    std_y_norm_train = 0.08511267085380758
    mean_X_norm_train = np.array([1.1886128903870394, 1.0746595698697274, 1.0089390403652372, 1.0051636435711488, 0.9639844597149281, 1.5924309727104378])
    std_X_norm_train = np.array([1.4887238067607071, 1.4391120341824508, 1.351343230273359, 1.302911028297482, 1.1511093513567663, 0.7366350688359029])
    # model initation
    X_norm_test = np.array(features[7:13])
    X_norm_test = (X_norm_test - mean_X_norm_train) / std_X_norm_train
    model = KernelRidge(kernel=kernel,alpha=alpha,gamma=gamma)
    model.fit(X_norm_train,y_norm_train)
    y_norm_test = model.predict([X_norm_test])
    y_norm_test = y_norm_test * std_y_norm_train + mean_y_norm_train
    bondl_core3D = y_norm_test[0][0]

    return bondl_core3D

## Gets the RACs of a given atidx
#  @param mol mol3D of this molecule
#  @param atidx the index of the atom of concern
#  @return descriptor_names updated names
#  @return descriptors updated RACs
def get_descriptor_vector_for_atidx(mol, atidx, depth=4, oct=False):
    descriptor_names = []
    descriptors = []
    result_dictionary = generate_atomonly_autocorrelations(mol, atidx, False, depth, oct)
    for colnames in result_dictionary['colnames']:
        descriptor_names += colnames
    for results in result_dictionary['results']:
        descriptors += results.tolist()
    result_dictionary = generate_atomonly_deltametrics(mol, atidx, False, depth, oct)
    for colnames in result_dictionary['colnames']:
        for colname in colnames:
            descriptor_names.append('D_' + colname)
    for results in result_dictionary['results']:
        descriptors += results.tolist()

    return descriptor_names, descriptors

# commented out default_plot() as conda repo does not automatically conda install matplitlib
# def default_plot(x, y):
#     # defs for plt
#     xlabel = r'distance / ${\rm \AA}$'
#     ylabel = r'distance / ${\rm \AA}$'
#     colors = ['r', 'g', 'b', '.75', 'orange', 'k']
#     markers = ['o', 's', 'D', 'v', '^', '<', '>']
#     font = {'family': 'sans-serif',
#             # 'weight' : 'bold',
#             'size': 22}
#     # figure size
#     plt.figure(figsize=(7, 6))
#     # dealing with axes
#     x = np.array(x)
#     y = np.array(y)
#     x_min = float(format(np.amin(x),'.1f')) - 0.1
#     x_max = float(format(np.amax(x), '.1f')) + 0.1
#     # x_range = x_max - x_min
#     plt.xlim(x_min, x_max)
#     # y_min = round(y[0],2)
#     # y_max = round(y[-1],2)
#     plt.ylim(x_min, x_max)
#     plt.xlabel(xlabel)
#     plt.ylabel(ylabel)
#     # dealing with ticks
#     ax = plt.axes()
#     ax.xaxis.set_major_locator(ticker.MultipleLocator(0.4))
#     ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.2))
#     ax.yaxis.set_major_locator(ticker.MultipleLocator(0.4))
#     ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.2))
#     plt.tick_params(which='both', axis='both', direction='in', bottom=True, top=True, right=True, left=True)
#     plt.rcParams['axes.linewidth'] = 3
#     plt.rcParams['xtick.major.size'] = 10
#     plt.rcParams['xtick.major.width'] = 3
#     plt.rcParams['ytick.major.size'] = 10
#     plt.rcParams['ytick.major.width'] = 3
#     plt.rcParams['xtick.minor.size'] = 5
#     plt.rcParams['xtick.minor.width'] = 3
#     plt.rcParams['ytick.minor.size'] = 5
#     plt.rcParams['ytick.minor.width'] = 3
#     plt.tight_layout()
#
#     plt.rc('font', **font)
#     plt.plot(x, y, 'o', markeredgecolor='k')
#     plt.plot([x_min,x_max],[x_min,x_max],linestyle='dashed',color='k')
#     # plt.plot([x_min, x_max], [x_min, x_max], 'k', linestyle='dashed')
#     plt.show()
# # plt.imshow(data,interpolation='none')
# # # plt.imshow(data,interpolation='nearest')
# # plt.savefig('relative_energies_for_Fe-py4.eps',dpi=400)


