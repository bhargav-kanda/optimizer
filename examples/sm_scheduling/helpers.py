from optimizer.sm_input.sm_functions import *
from pulp import pulp, lpSum
import pandas as pd
import datetime
import optimizer.sm_input.sm_globals as globals
import re


def is_fixed(dv):
	if (globals.fixed_dv_df['DV'].astype(str) == str(dv)).sum() > 0:
		filtered = globals.fixed_dv_df[globals.fixed_dv_df['DV'].astype(str) == str(dv)]
		movie_name = filtered.movie_name_orig.iloc[0]
		day = filtered.day.iloc[0]
		slot = filtered.slots.iloc[0]
		all_dvs = globals.fixed_dv_df[(globals.fixed_dv_df.movie_name_orig == movie_name) &
		                              (globals.fixed_dv_df.slots == slot) &
		                              (globals.fixed_dv_df.day == day)]
		if len(all_dvs) == 1:
			return True
	return False


def prune_dv_space(dvs, message=None):
	common_dvs = [dv for dv in dvs if is_fixed(dv)]
	if common_dvs:
		if message:
			print(message)
		import pdb
		pdb.set_trace()
		raise Exception('Having to drop fixed slots! '+str(common_dvs))
	else:
		dvs_str = [str(dv) for dv in dvs]
		filter = (globals.dv_df['DV'].astype(str).isin(dvs_str))
		globals.dv_df.drop(globals.dv_df.index[filter], inplace=True)
		if message:
			print(message)
		else:
			print('Dropped {} dvs'.format(len(dvs)))


def evaluate_string_as_func(string, context=None):
	function_name, params = string.split('(')
	if len(params[:-1]) == 0:
		evaled_value = eval(function_name + '()')
	else:
		if not context:
			raise Exception('The function "{}" has params and hence needs context.'.format(function_name))
		params = params[:-1].replace(' ', '').split(',')
		evaled_params = []
		for param in params:
			if '=' in param:
				evaled_params.append(param)
			elif param in context:
				value = context[param]
				evaled_params.append(('"' + value + '"') if type(value).__name__ == 'str' else str(value))
			else:
				try:
					evaled_params.append(str(eval(param)))
				except Exception:
					import pdb
					pdb.set_trace()
					raise Exception('Parameter given to rhs function does not exist in context. {}'.format(context['name']))
		param_string = ','.join(evaled_params)
		evaled_value = eval(function_name + '(' + param_string + ')')
	return evaled_value


def break_down_lp_expression(lp_expression):
	items = lp_expression.items()
	dvs = []
	weights = []
	for item in items:
		dvs.append(item[0])
		weights.append(-item[1])
	rhs = lp_expression.constant
	return dvs, weights, rhs


def append_to_constraints(constraints, weights, dvs, rhs, comparator, context):
	if type(weights).__name__ != 'list':
		weights = [weights] * len(dvs)
	else:
		if len(weights) != len(dvs):
			raise Exception('Lengths of weights and dvs do not match for lhs')
	if type(rhs).__name__ == 'str':
		rhs = evaluate_string_as_func(rhs, context)
	if type(rhs).__name__ == 'LpAffineExpression':
		new_dvs, new_weights, rhs = break_down_lp_expression(rhs)
		dvs += new_dvs
		weights += new_weights
	constraints.append({'weights': weights, 'dvs': dvs, 'rhs': rhs, 'comparator': comparator, 'rule': context['name']})
	return constraints


def is_same(x, y):
	if type(x).__name__ == 'LpAffineExpression':
		x = str(x)
	if type(y).__name__ == 'LpAffineExpression':
		y = str(y)
	return x == y


def get_context(element, filters, constraint):
	context = dict(zip(filters, element))
	if constraint['relative_dates'] and context['dates']:
		context.update({'all_dates': get_relative_dates(context['dates'], constraint['relative_dates'])})
	if constraint['relative_slots'] and context['slots']:
		context.update({'all_slots': get_relative_slots(context['slots'], constraint['relative_slots'])})
	return context


def get_reference_slot():
	if not globals.reference_slot:
		for rule in [r for r in globals.business_rules if type(r).__name__ == 'ContinuityRule']:
			if rule.constraint['min_start'] == rule.constraint['max_start']:
				globals.reference_slot = (rule.constraint['slot'], rule.constraint['min_start'])
	if not globals.reference_slot:
		raise Exception('Could not compute the reference slot.')
	else:
		return globals.reference_slot


def get_constraints_for_rule(rule):
	constraints = []
	rule_type = type(rule).__name__
	if rule_type == 'GeneralRule':
		constraints = rule.create_constraints()
	elif rule_type == 'SequenceRule':
		constraints = rule.create_constraints()
	elif rule_type == 'ContinuityRule':
		constraints = rule.create_constraints()
	return constraints


def define_dv(s):
	variable = "x_" + re.sub('[^A-Za-z0-9]+', '', s["movie_name"]) + "_" + s["dates"].strftime("%Y-%m-%d") + "_" + s[
		"slots"]
	variable = pulp.LpVariable(str(variable), lowBound=0, upBound=1, cat='Integer')  # make variable binary
	return variable


def define_indicator_dv(s):
	variable = "ind_" + re.sub('[^A-Za-z0-9]+', '', s)
	variable = pulp.LpVariable(str(variable), lowBound=0, upBound=1, cat='Integer')  # make variable binary
	return variable


def define_tvr_slacks(start, end):
	var1 = "slack_{}_{}_period".format(start, end)
	var2 = "slack_{}_{}_avg".format(start, end)
	var1 = pulp.LpVariable(str(var1), lowBound=0)
	var2 = pulp.LpVariable(str(var2), lowBound=0)
	return var1, var2


def create_uniform_tvr_constraint(start, end, lhs_slack, rhs_slack):
	all_days = get_all_of('dates')
	selected_days = [x for x in all_days if start <= x <= end]
	week_days = []
	for day in selected_days:
		week_days += [y.strftime('%A') for y in globals.schedule_for if y.day == day]
	all_week_days = [y.strftime('%A') if y.strftime('%A') in week_days else None for y in globals.schedule_for]
	super_set_start = all_week_days.index(week_days[0])
	super_set_end = len(all_week_days) - all_week_days[::-1].index(week_days[-1]) - 1
	super_set_days = [day for index, day in enumerate(all_days[super_set_start:super_set_end+1]) if all_week_days[index] is not None]
	selected_tvr = lpSum([row[1].TVR * row[1].DV for row in globals.dv_df[globals.dv_df['day'].isin(selected_days)]
	                     .iterrows()])
	total_tvr = lpSum([row[1].TVR * row[1].DV for row in globals.dv_df[globals.dv_df['day'].isin(super_set_days)].iterrows()])
	average_tvr = total_tvr * len(selected_days)/len(super_set_days)
	constraint = selected_tvr + lhs_slack == average_tvr + rhs_slack
	return constraint


def create_schedule_output(df_plan, file_name):
	df_ = globals.dv_df.copy()
	df_["DV"] = df_["DV"].astype(str)
	df_plan = df_plan.merge(df_, on="DV")
	df_plan_raw = df_plan.copy()
	try:
		df_plan = df_plan[
			["movie_name_orig", "dates", "slots", 'sort_ts', "Duration", "duration_adjusted", "studios", "TVR",
			 "movie_name", "day", "week_day", "sort_day_ts"]]
		df_plan["sort_ts_desc"] = -1 * df_plan["sort_ts"]
		df_temp = df_plan[(df_plan.sort_ts <= 9) & (df_plan.movie_name_orig != "dummy")].groupby(
			by=['day', 'sort_ts_desc', 'slots']).duration_adjusted.sum().groupby(level=[0]).cumsum().reset_index()
		df_temp.drop("sort_ts_desc", inplace=True, axis=1)
		df_temp["Start_time"] = pd.to_datetime("20:50", format="%H:%M")
		df_temp["Start_time"] = df_temp.apply(
			lambda s: s["Start_time"] - pd.Timedelta(seconds=s["duration_adjusted"] * 60), axis=1)
		df_temp_2 = df_plan[df_plan.sort_ts == 10].groupby(by=['day']).duration_adjusted.sum().groupby(
			level=[0]).cumsum().reset_index()
		df_temp_2["slots"] = "11pm-1am"
		df_temp_2["Start_time"] = pd.to_datetime("20:50", format="%H:%M")
		df_temp_2["Start_time"] = df_temp_2.apply(
			lambda s: s["Start_time"] + pd.Timedelta(seconds=s["duration_adjusted"] * 60), axis=1)
		df_temp = pd.concat([df_temp[['day', 'slots', 'Start_time']], df_temp_2[['day', 'slots', 'Start_time']]])
		df_plan = df_plan.merge(df_temp, on=['day', 'slots'], how="left")
		df_plan.loc[df_plan.slots == "9pm-11pm", "Start_time"] = pd.to_datetime("20:50", format="%H:%M")
		df_plan.drop("sort_ts_desc", inplace=True, axis=1)
		df_plan["slot_rank"] = df_plan.groupby(['movie_name_orig', 'slots']).day.rank()
		df_temp = df_plan.groupby(['movie_name_orig', 'slots']).slot_rank.count().reset_index()
		df_temp.columns = list(df_temp.columns[:-1]) + ["n_airs"]
		df_plan = df_plan.merge(df_temp, on=['movie_name_orig', 'slots'], how="left")
		df_temp = df_plan.groupby(['movie_name_orig', 'week_day', 'slots']).slot_rank.count().reset_index()
		df_temp.columns = list(df_temp.columns[:-1]) + ["n_airs_weekdays"]
		df_plan = df_plan.merge(df_temp, on=['movie_name_orig', 'week_day', 'slots'], how="left")
		df_plan.sort_values(by=["dates", 'sort_ts'], ascending=[True, True], inplace=True)
		df_plan["dates"] = pd.to_datetime(df_plan["dates"])
		df_plan.dates = df_plan.dates.dt.strftime("%Y-%m-%d")
		df_plan.Start_time = df_plan.Start_time.dt.strftime("%H:%M")
		print('{} dummies in the plan.'.format(len(df_plan[df_plan['movie_name']=='dummy'])))
		for day in get_all_of('dates'):
			if len(df_plan[(df_plan['day']==day)]) < 9:
				print('Missing slots on {}'.format(day))
		df_plan.to_csv(globals.INPUT_PATH + globals.input_folder + "/lp_output/" + file_name + ".csv", index=False)
	except Exception as E:
		print(datetime.datetime.now().isoformat() + ' Exception in consolidation' + E.message())
		df_plan.to_csv(globals.INPUT_PATH + globals.input_folder + "/lp_output/" + file_name + ".csv", index=False)

