import numpy as np
import pandas as pd
from datetime import time
import optimizer.sm_input.sm_globals as globals


REPO_PATH = '/home/bhargava/TA_Lab/'
INPUT_PATH = REPO_PATH + 'optimizer/'
input_folder = 'input'



COLUMN_NAME_MAP = {
	'movies': 'movie_name',
	'dates': 'day',
	'slots': 'slots',
}


def get_time_from_str(str):
	str = str.lower()
	hour = int(str[:-2])
	if str[-2:] == 'pm':
		hour += 12
	return time(hour=hour)


def get_timerange_for_slot(slot):
	from_time, to_time = slot.split('-')
	return (get_time_from_str(from_time), get_time_from_str(to_time))


def get_dates_in_between(from_date, to_date):
	from datetime import datetime, timedelta
	from_date = datetime.strptime(from_date, '%Y-%m-%d')
	to_date = datetime.strptime(to_date, '%Y-%m-%d')
	dates = [from_date]
	for i in range(1, (to_date - from_date).days):
		dates.append(from_date + timedelta(days=i))
	dates.append(to_date)
	return [pd.to_datetime(datetime.strftime(date, '%Y-%m-%d')) for date in dates]


def get_unique_movies():
	movie_names = globals.dv_df["movie_name_orig"].unique().tolist()
	if 'dummy' in movie_names:
		movie_names.remove('dummy')
	return movie_names


def get_all_of(type, filter=None):
	if filter:
		dv_filter = None
		for key in filter.keys():
			if not dv_filter:
				dv_filter = (globals.dv_df[key].isin(filter[key]))
			else:
				dv_filter &= (globals.dv_df[key].isin(filter[key]))
		if dv_filter.sum() > 0:
			return globals.dv_df.loc[dv_filter, COLUMN_NAME_MAP[type]].unique().tolist()
		else:
			return None
	return globals.dv_df[COLUMN_NAME_MAP[type]].unique().tolist()


def get_max_airings_for_title(movie_name):
	m_fil = globals.dv_df["movie_name_orig"] == movie_name
	remaining_runs = globals.dv_df.loc[m_fil, "remaining_runs"].unique()[0]
	no_of_months = globals.dv_df.loc[m_fil, "no_of_months"].unique()[0]
	no_of_airings = np.ceil(remaining_runs / float(no_of_months))
	if no_of_airings > 4:
		no_of_airings = 4
	# if no_of_airings < 4:
	# 	no_of_airings = 4
	if movie_name in [x['movies'] for x in get_fixed_airings('MOTW')]:
		no_of_airings = 4
	if movie_name in [x['movies'] for x in get_fixed_airings('MOTM')]:
		no_of_airings = 6
	if no_of_airings < len(globals.fixed_df.loc[(globals.fixed_df['movie_name'] == movie_name)].movie_name.tolist()):
		no_of_airings = len(globals.fixed_df.loc[(globals.fixed_df['movie_name'] == movie_name)].movie_name.tolist())
		if movie_name in get_fox_movies():
			no_of_airings = no_of_airings * 2
	if remaining_runs <= no_of_airings:
		no_of_airings = remaining_runs
	return no_of_airings


def get_run_count_for_title(movie_name):
	m_fil = globals.dv_df["movie_name_orig"] == movie_name
	remaining_runs = globals.dv_df.loc[m_fil, "remaining_runs"].unique()[0]
	no_of_months = globals.dv_df.loc[m_fil, "no_of_months"].unique()[0]
	no_of_airings = np.ceil(remaining_runs / float(no_of_months))
	return no_of_airings


def get_day_from_date(date):
	try:
		return globals.dv_df.loc[(globals.dv_df['dates'] == date), 'day'].tolist()[0]
	except:
		import pdb
		pdb.set_trace()


def get_fixed_airings(type=None):
	airings = []
	if type:
		airings_df = globals.fixed_df.loc[(globals.fixed_df['type'] == type)]
	else:
		airings_df = globals.fixed_df
	for item in airings_df.iterrows():
		item = item[1]
		airings.append({'movies': item.movie_name, 'dates': get_day_from_date(item.dates), 'slots': item.slots})
	return airings


def get_fixed_number(movie_name, slots=None, dates=None):
	filter = (globals.fixed_df['movie_name'] == movie_name)
	if slots:
		filter &= (globals.fixed_df[COLUMN_NAME_MAP['slots']].isin(slots))
	if dates:
		filter &= (globals.fixed_df['dates'].dt.day.isin(dates))
	return filter.sum()


def max_value_or_fixed_number(c, value):
	# import pdb
	# pdb.set_trace()
	if c['dates']:
		if type(c['dates']).__name__ != 'list':
			dates = [c['dates']]
		else:
			dates = c['dates']
	else:
		dates = None
	if c['slots']:
		if type(c['slots']).__name__ != 'list':
			slots = [c['slots']]
		else:
			slots = c['slots']
	else:
		slots = None
	return max(value, get_fixed_number(c['movie_name'], slots=slots, dates=dates))


def exclude_slot_repeat_10days(movie_name, slot):
	return get_fixed_number(movie_name, slots=[slot]) >= 2


def get_motm_airings():
	airings = []
	for item in globals.fixed_df.loc[(globals.fixed_df['type']=='MOTM')].iterrows():
		item = item[1]
		airings.append({'movies': item.movie_name, 'dates': get_day_from_date(item.dates), 'slots': item.slots})
	return airings


def get_motw_airings():
	airings = []
	for item in globals.fixed_df.loc[(globals.fixed_df['type'] == 'MOTW')].iterrows():
		item = item[1]
		airings.append({'movies': item.movie_name, 'dates': get_day_from_date(item.dates), 'slots': item.slots})
	return airings


# def get_airings_in_schedule(movie_name):
# 	if '_R' in movie_name or '_O' in movie_name:
# 		movie_name.replace('_O', '').replace('_R', '')
# 	filter = (globals.dv_df['movie_name_orig'].isin([movie_name]))
# 	filtered_dvs = globals.dv_df.loc[filter, 'DV'].tolist()
# 	from pulp import lpSum
# 	return lpSum([0.5 * i for i in filtered_dvs])


def get_npt_slots():
	return globals.ts['npt']


def get_pt_slots():
	return globals.ts['pt']


def get_original_airings():
	return []


def get_fox_movies(type=None):
	all_movies = globals.fox_df["movie_name"].unique().tolist()
	if type:
		if type == 'original':
			return [(name + '_O') for name in all_movies]
		elif type == 'repeat':
			return [(name + '_R') for name in all_movies]
	return all_movies


def get_performing_fox_originals():
	all_movies = globals.fox_df["movie_name"].unique().tolist()
	avg_tvrs = []
	tvr_dict = {}
	for movie in all_movies:
		movie_name = movie + '_O'
		tvrs = globals.dv_df.loc[(globals.dv_df['movie_name'].isin([movie_name])), 'TVR'].tolist()
		if len(tvrs) > 0:
			avg_tvr = sum(tvrs)/len(tvrs)
		else:
			avg_tvr = 0
		if avg_tvr:
			avg_tvrs.append(avg_tvr)
			tvr_dict.update({avg_tvr: movie})
	avg_tvrs = sorted(avg_tvrs, reverse=True)
	high_tvrs = avg_tvrs[:round(len(all_movies)/3)]
	return [tvr_dict[tvr] for tvr in high_tvrs]


def get_family_movies():
	return family_df[family_df.columns[0]].unique().tolist()


def get_high_performing_titles():
	return None


def get_restricted_movies():
	return []


def return_self(object):
	return object


def get_fox_repeat(movie_name):
	suffix = movie_name[-2:]
	if suffix in ['_R', '_O']:
		return movie_name[:-2] + '_R'
	else:
		return movie_name + '_R'


def get_fox_original(movie_name):
	suffix = movie_name[-2:]
	if suffix in ['_R', '_O']:
		return movie_name[:-2] + '_O'
	else:
		return movie_name + '_O'


def get_sum_of_airings_today(movie_name, date):
	filter = (globals.dv_df[COLUMN_NAME_MAP['movies']].isin([movie_name]))
	filter &= (globals.dv_df[COLUMN_NAME_MAP['dates']].isin([date]))
	filtered_dvs = globals.dv_df.loc[filter, 'DV'].tolist()
	from pulp import lpSum
	return lpSum([1 * i for i in filtered_dvs])


def read_input():
	globals.df_m["dates"] = pd.to_datetime(globals.df_m["dates"], format="%Y-%m-%d")
	globals.dv_df["dates"] = pd.to_datetime(globals.dv_df["dates"], format="%Y-%m-%d")
	globals.dv_df = globals.dv_df.loc[globals.dv_df.slots.isin(globals.ts["dead"]) == False]
	globals.dv_df["day"] = globals.dv_df["dates"].dt.day
	if globals.schedule_for:
		globals.dv_df = globals.dv_df[globals.dv_df['dates'].isin(globals.schedule_for)]
	globals.dv_df["sort_ts"] = globals.dv_df["slots"].map(globals.sort_ts)
	globals.dv_df.sort_values(["dates", "sort_ts"], inplace=True)
	globals.dv_df.reset_index(inplace=True, drop=True)
	globals.dv_df["pt"] = (globals.dv_df["slots"].isin(globals.ts["pt"])).astype(int)
	globals.fixed_df['dates'] = pd.to_datetime(globals.fixed_df['dates'])
	# globals.dv_df = pd.merge(globals.dv_df, globals.fixed_df, how='left', on=['movie_name', 'dates', 'slots'])
	# globals.dv_df['fixed_input'] = np.where(~(globals.dv_df['type'].isna()), 1, 0)
	# Add variables pre calculations
	globals.dv_df["sort_day_ts"] = globals.dv_df.day * 100 + globals.dv_df.sort_ts
	# Compute adjusted duration by adding FPC & ads
	globals.dv_df["week_day"] = globals.dv_df["dates"].dt.day_name()
	# globals.dv_df["week"] = globals.dv_df["dates"].map(week_map)
	globals.dv_df.loc[globals.dv_df["TVR"] < 0, "TVR"] = 0
	globals.dv_df = globals.dv_df.loc[globals.dv_df["remaining_runs"].isin(["Not Added", "TBC"]) == False].reset_index(drop=True)
	# ===============Update remaning runs by march plan===============
	globals.dv_df["remaining_runs"] = globals.dv_df["remaining_runs"].astype(float)
	# ===============Update remaning runs by march plan===============
	globals.dv_df = globals.dv_df.loc[((globals.dv_df["remaining_runs"] > 0) & (globals.dv_df.day > 15)) | (globals.dv_df.day <= 15)]
	# Remove A WRINKLE IN TIME from inventory
	fil_ = (globals.dv_df.movie_name == "A WRINKLE IN TIME")
	globals.dv_df.drop(globals.dv_df.index[fil_], inplace=True)
	print('At the end of read_input size of globals.dv_df is {}'.format(len(globals.dv_df)))


def add_fox_repeats():
	fox_tier_movies = globals.fox_df["movie_name"].unique().tolist()
	globals.dv_df['movie_name_orig'] = globals.dv_df['movie_name']
	globals.dv_df['mul'] = 0
	fil = globals.dv_df.movie_name.isin(fox_tier_movies)
	globals.dv_df.loc[fil, 'mul'] = 1
	df_fox_repeat_temp = globals.dv_df[fil]
	df_fox_repeat_temp = df_fox_repeat_temp[df_fox_repeat_temp.slots != "9pm-11pm"]
	df_fox_repeat_temp["mul"] = -1
	# df_fox_repeat_temp.orig_repeat_flag = 'R'
	globals.dv_df.loc[fil, 'movie_name'] = globals.dv_df.loc[fil, 'movie_name'] + "_O"  # .apply(lambda s: s+"_O")
	df_fox_repeat_temp['movie_name'] = df_fox_repeat_temp['movie_name'] + "_R"
	globals.dv_df = pd.concat([globals.dv_df, df_fox_repeat_temp])
	# Adjust fox movies from prior
	df_temp = globals.df_m[(globals.df_m["type"] == "PRIOR") & (globals.df_m.movie_name.isin(fox_tier_movies)) & (
			globals.df_m.dates >= pd.to_datetime("2019-03-01", format="%Y-%m-%d"))]
	df_temp = df_temp.sort_values(["movie_name", "dates"])
	df_temp["fox_rank"] = df_temp.groupby("movie_name").dates.rank()
	df_temp["tag_orig_repeat"] = "O"
	df_temp.loc[df_temp["fox_rank"] % 2 == 0, "tag_orig_repeat"] = "R"
	df_temp.drop(["type", "fox_rank"], inplace=True, axis=1)
	df_temp.rename(columns={'movie_name': 'movie_name_orig'}, inplace=True)
	globals.dv_df = globals.dv_df.merge(df_temp, on=["dates", "slots", "movie_name_orig"], how="left")
	fil_ = (~(globals.dv_df.tag_orig_repeat.isnull())) & (globals.dv_df.movie_name.str.split("_").str[1] !=
	                                                      globals.dv_df.tag_orig_repeat)
	globals.dv_df.drop(globals.dv_df.index[fil_], inplace=True)
	globals.dv_df.drop("tag_orig_repeat", axis=1, inplace=True)


def set_durations():
	globals.dv_df["start_date"] = pd.to_datetime(globals.dv_df["start_date"], format="%Y-%m-%d")
	globals.dv_df["end_date"] = pd.to_datetime(globals.dv_df["end_date"], format="%Y-%m-%d")
	globals.dv_df["no_of_months"] = ((globals.dv_df["end_date"] - globals.dv_df["dates"].min()) / np.timedelta64(1, 'M')).apply(np.ceil)
	globals.dv_df["duration_adjusted"] = globals.dv_df["Duration"].astype(float)
	fil_ = globals.dv_df["slots"].isin(["9pm-11pm", "11pm-1am", "7pm-9pm", "5pm-7pm"])
	globals.dv_df.loc[fil_, "duration_adjusted"] = globals.dv_df.loc[fil_, "duration_adjusted"] * 60 / 44
	fil_ = globals.dv_df["slots"].isin(["9am-11am", "11am-1pm", "1pm-3pm", "3pm-5pm"]) & globals.dv_df["week_day"].isin(
		['Saturday', 'Sunday'])
	globals.dv_df.loc[fil_, "duration_adjusted"] = globals.dv_df.loc[fil_, "duration_adjusted"] * 60 / 46
	fil_ = globals.dv_df["slots"].isin(["9am-11am", "11am-1pm", "1pm-3pm", "3pm-5pm"]) & (
		~(globals.dv_df["week_day"].isin(['Saturday', 'Sunday'])))
	globals.dv_df.loc[fil_, "duration_adjusted"] = globals.dv_df.loc[fil_, "duration_adjusted"] * 60 / 49
	globals.dv_df["duration_adjusted"] = globals.dv_df["duration_adjusted"] + 2  # Adding 2 min credits


def add_dummies():
	sort_duration = {'1am-3am': 0, '3am-5am': 0, '5am-7am': 830, '7am-9am': 710, '9am-11am': 590, '11am-1pm': 470,
	                 '1pm-3pm': 350, '3pm-5pm': 230, '5pm-7pm': 110, '7pm-9pm': 50, '9pm-11pm': 0, '11pm-1am': 0}
	# sort_duration = {'1am-3am':0,'3am-5am':0,'5am-7am':60,'7am-9am':60,'9am-11am':60,'11am-1pm':60,'1pm-3pm':60,
	# '3pm-5pm':60,'5pm-7pm':60,'7pm-9pm':50,'9pm-11pm':0,'11pm-1am':0}
	grp_cols = ["dates", "slots", "day", "week_day", 'sort_ts', 'pt', 'sort_day_ts']
	df_temp = globals.dv_df.groupby(grp_cols).movie_name_orig.nunique()
	df_temp = df_temp[df_temp > 1]
	sel_cols = list(set(globals.dv_df.columns) - set(grp_cols) - set({'movie_name', 'movie_name_orig'}))
	df_temp = pd.concat([globals.dv_df.groupby(grp_cols)[sel_cols].min(), df_temp], axis=1).reset_index()
	df_temp.dropna(inplace=True)
	# df_temp = globals.dv_df[globals.dv_df.day>15].groupby(["dates","slots"]).min().reset_index()
	df_temp["movie_name"] = "dummy"
	df_temp["movie_name_orig"] = "dummy"
	df_temp["mul"] = 0
	df_temp["duration_adjusted"] = 0		# Giving 0 duration to all dummy movies
	df_temp["TVR"] = globals.dv_df.TVR.min() * .001
	# df_temp.fillna(globals.dv_df.min(),inplace=True) #avoiding null entries from affecting LP problem
	df_temp = df_temp[globals.dv_df.columns.tolist()]
	globals.dv_df = pd.concat([globals.dv_df, df_temp])


def process_input():
	read_input()
	add_fox_repeats()
	set_durations()
	add_dummies()
	globals.dv_df.reset_index(drop=True, inplace=True)
	return globals.dv_df

