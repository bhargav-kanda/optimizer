set FOOD;
set NUTR;
# Parameters
param cost { FOOD } > 0;
param f_min { FOOD } >= 0;
param f_max {j in FOOD } >= f_min [j];
param n_min { NUTR } >= 0;
param n_max {i in NUTR } >= n_min [i];
param amt {NUTR , FOOD } >= 0;
# Variables
var Buy {j in FOOD } >= f_min [j], <= f_max [j];
# Objective
minimize total_cost : sum {j in FOOD } cost [j] * Buy[j];
# Contraints
subject to diet {i in NUTR }:
    n_min [i] <= sum {j in FOOD } amt[i,j] * Buy[j] <= n_max [i];

