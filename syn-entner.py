"""

Reference: A Shah, K Shanmugam, K Ahuja 
"Finding Valid Adjustments under Non-ignorability with Minimal DAG Knowledge,"
In International Conference on Artificial Intelligence and Statistics (AISTATS), 2022

Last updated: February 22, 2022
Code author: Abhin Shah

File name: syn-entner.py

Description: Code to compare with Entner et al. (2013)

"""

import time
import argparse
import multiprocessing
import numpy as np
import pandas as pd
from functools import partial
from sklearn.preprocessing import StandardScaler
from scipy.special import softmax, expit
from contextlib import contextmanager
from multiprocessing import get_context
from multiprocessing import set_start_method
from sklearn.model_selection import train_test_split

import rpy2.robjects as ro
import rpy2.robjects.numpy2ri
rpy2.robjects.numpy2ri.activate()
from rpy2.robjects.packages import importr
importr('RCIT')
RCoT = ro.r('RCoT')

@contextmanager
def poolcontext(*args, **kwargs):
  pool = multiprocessing.Pool(*args, **kwargs)
  yield pool
  pool.terminate()

def get_u(number_observations,number_dimensions):
  u1 = np.random.uniform(1.0,2.0,(number_observations,1))
  u2 = np.random.uniform(1.0,2.0,(number_observations,number_dimensions))
  u3 = np.random.uniform(1.0,2.0,(number_observations,number_dimensions))
  u4 = np.random.uniform(1.0,2.0,(number_observations,number_dimensions))
  return u1,u2,u3,u4

def get_theta(number_dimensions,use_t_in_e,number_environments):
  theta1 = np.random.uniform(1.0,2.0,(number_dimensions+1,1))
  theta2 = np.random.uniform(1.0,2.0,(number_dimensions*2+1,number_dimensions))
  theta3 = np.random.uniform(1.0,2.0,(number_dimensions*2,number_dimensions))
  theta4 = np.random.uniform(1.0,2.0,(number_dimensions*2+1,1))
  theta5 = np.random.uniform(1.0,2.0,(2,1))
  if use_t_in_e == 0:
    theta6 = np.concatenate((np.random.uniform(1.0,2.0,(1,1)), np.zeros((1,1)), np.random.uniform(-1.0,-2.0,(1,1))), axis = 1)
  else:
    theta6 = np.concatenate((np.random.uniform(1.0,2.0,(2,1)), np.zeros((2,1)), np.random.uniform(-1.0,-2.0,(2,1))), axis = 1)
  return theta1, theta2, theta3, theta4, theta5, theta6

def get_data(u1,u2,u3,u4,theta1,theta2,theta3,theta4,theta5,theta6,number_observations,number_dimensions,use_t_in_e,number_environments):
  x1 = np.dot(np.concatenate((u1,u2),axis=1), theta1) + 0.1* np.random.normal(0,1,(number_observations,1))
  x2 = np.dot(np.concatenate((x1,u2,u3),axis=1), theta2) + 0.1* np.random.normal(0,1,(number_observations,number_dimensions))
  x3 = np.dot(np.concatenate((u3,u4),axis=1), theta3) + 0.1 * np.random.normal(0,1,(number_observations,number_dimensions))
  t = np.random.binomial(1, expit(np.dot(np.concatenate((u1, x1), axis = 1), theta5)-np.mean(np.dot(np.concatenate((u1, x1), axis = 1), theta5))))
  if use_t_in_e == 0:
    probabilites = softmax(np.dot(x1, theta6)-np.mean(np.dot(x1, theta6), axis = 0), axis = 1)
  else:
    probabilites = softmax(np.dot(np.concatenate((x1, t), axis = 1), theta6)-np.mean(np.dot(np.concatenate((x1, t), axis = 1), theta6), axis = 0 ),  axis = 1)
  e = np.zeros((number_observations,1), dtype=int)
  for i,probability in enumerate(probabilites):
    e[i,:] = np.random.choice(np.arange(number_environments), p = probability)

  zeros =  np.zeros((number_observations,1))
  ones =  np.ones((number_observations,1))
  noise = 0.1 * np.random.normal(0,1,(number_observations,1))
  y = np.dot(np.concatenate((x2,u4,t),axis=1),theta4) + noise
  y_0 = np.dot(np.concatenate((x2,u4,zeros),axis=1),theta4) + noise
  y_1 = np.dot(np.concatenate((x2,u4,ones),axis=1),theta4) + noise

  return x1,x2,x3,t,e,y,y_0,y_1

def get_train_test_data(number_observations,number_dimensions,use_t_in_e,number_environments):
  u1,u2,u3,u4 = get_u(number_observations,number_dimensions)
  theta1, theta2, theta3, theta4, theta5, theta6 = get_theta(number_dimensions,use_t_in_e,number_environments)
  x1,x2,x3,t,e,y,y_0,y_1 = get_data(u1,u2,u3,u4,theta1,theta2,theta3,theta4,theta5,theta6,number_observations,number_dimensions,use_t_in_e,number_environments)
  true_ate = np.round(np.mean(y_1 - y_0),6)
  features_train, features_test, t_train, t_test, y_train, y_test, e_train, e_test, y_0_train, y_0_test, y_1_train, y_1_test = train_test_split(np.concatenate((x1,x2,x3),axis=1), t, y, e, y_0, y_1, test_size=0.2)
  x_train = pd.DataFrame(features_train)
  x_train.columns = list(map(str, range(2*number_dimensions+1)))
  x_train.columns = pd.MultiIndex.from_arrays([['x1' for i in range(1)] + ['x2' for i in range(number_dimensions)] + ['x3' for i in range(number_dimensions)], list(x_train.columns)]) 
  t_train = pd.Series(t_train[:,0])
  y_train = pd.Series(y_train[:,0])
  e_train = pd.Series(e_train[:,0])
  y_0_train = pd.Series(y_0_train[:,0])
  y_1_train = pd.Series(y_1_train[:,0])
  x_test = pd.DataFrame(features_test)
  x_test.columns = list(map(str, range(2*number_dimensions+1)))
  x_test.columns = pd.MultiIndex.from_arrays([['x1' for i in range(1)] + ['x2' for i in range(number_dimensions)] + ['x3' for i in range(number_dimensions)], list(x_test.columns)]) 
  t_test = pd.Series(t_test[:,0])
  y_test = pd.Series(y_test[:,0])
  e_test = pd.Series(e_test[:,0])
  y_0_test = pd.Series(y_0_test[:,0])
  y_1_test = pd.Series(y_1_test[:,0])
  return x_train, t_train, y_train, e_train, y_0_train, y_1_train, x_test, t_test, y_test, e_test, y_0_test, y_1_test, true_ate


def main(args):

  starting_time = time.time()
  number_repetitions = args.nr
  number_observations = args.no
  use_t_in_e = args.use_t_in_e
  number_environments = args.ne
  number_dimensions_list = [2,7,12]

  pvalue_empty = np.zeros((number_repetitions,len(number_dimensions_list)))
  pvalue_x3 = np.zeros((number_repetitions,len(number_dimensions_list)))
  pvalue_x2x3 = np.zeros((number_repetitions,len(number_dimensions_list)))

  for r in range(number_repetitions):
    print(r+1)
    for i, number_dimensions in enumerate(number_dimensions_list):
        print(2*number_dimensions+1)
        x_train, t_train, y_train, e_train, y_0_train, y_1_train, x_test, t_test, y_test, e_test, y_0_test, y_1_test, true_ate = get_train_test_data(number_observations,number_dimensions,use_t_in_e,number_environments)

        x2_n = StandardScaler().fit_transform(np.array(x_train[['x2']]))
        x3_n = StandardScaler().fit_transform(np.array(x_train[['x3']]))
        y_n = StandardScaler().fit_transform(np.array(y_train).reshape(-1, 1))
        t = np.array(t_train).reshape(-1, 1)
        e = np.array(e_train).reshape(-1, 1)

        pvalue_empty[r,i] = RCoT(e,y_n,t)[0]
        pvalue_x3[r,i] = RCoT(e,y_n,np.concatenate((x3_n,t),axis=1))[0]
        pvalue_x2x3[r,i] = RCoT(e,y_n,np.concatenate((x2_n,x3_n,t),axis=1))[0]

    print(time.time() - starting_time)

  np.savetxt('syn-entner/pvalue_empty.csv', pvalue_empty, delimiter=",")
  np.savetxt('syn-entner/pvalue_x3.csv', pvalue_x3, delimiter=",")
  np.savetxt('syn-entner/pvalue_x2x3.csv', pvalue_x2x3, delimiter=",")

  avg_pvalue_empty = np.mean(pvalue_empty, axis=0).reshape(1, len(number_dimensions_list))
  avg_pvalue_x3 = np.mean(pvalue_x3, axis=0).reshape(1, len(number_dimensions_list))
  avg_pvalue_x2x3 = np.mean(pvalue_x2x3, axis=0).reshape(1, len(number_dimensions_list))

  std_pvalue_empty = np.std(pvalue_empty, axis=0).reshape(1, len(number_dimensions_list))/np.sqrt(number_repetitions)
  std_pvalue_x3 = np.std(pvalue_x3, axis=0).reshape(1, len(number_dimensions_list))/np.sqrt(number_repetitions)
  std_pvalue_x2x3 = np.std(pvalue_x2x3, axis=0).reshape(1, len(number_dimensions_list))/np.sqrt(number_repetitions)
  
  print(avg_pvalue_empty)
  print(avg_pvalue_x3)
  print(avg_pvalue_x2x3)

  print(std_pvalue_empty)
  print(std_pvalue_x3)
  print(std_pvalue_x2x3)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--nr',
      help='number of repetitions',
      default=100,
      type=int)
  parser.add_argument(
      '--no',
      help='number of observations',
      default=50000,
      type=int)
  parser.add_argument(
      '--use_t_in_e',
      help='indicator for whether t should be used to generate e',
      default=1,
      type=int)
  parser.add_argument(
      '--ne',
      help='number of environments',
      default=3,
      type=int)
  
  args = parser.parse_args()
  main(args)