from datetime import time
import pandas as pd

REPO_PATH = '/home/bhargava/optimizer/'
INPUT_PATH = REPO_PATH + 'optimizer/'
input_folder = 'input'


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


def init():
	global slots, ts, sort_ts, pt_ts, slot_times, reference_slot, dv_df, prior_df, fixed_df, fox_df, family_df, df_m
	global prob, business_rules, business_constraints, fixed_rules, fixed_constraints, schedule_for, fixed_dvs, \
		input_folder
	slots = ['1am-3am', '3am-5am', '5am-7am', '7am-9am', '9am-11am', '11am-1pm', '1pm-3pm', '3pm-5pm', '5pm-7pm',
	           '7pm-9pm', '9pm-11pm', '11pm-1am']
	ts = {"pt": ['7pm-9pm', '9pm-11pm', '11pm-1am'],
	      "npt": ['7am-9am', '9am-11am', '11am-1pm', '1pm-3pm', '3pm-5pm', '5pm-7pm'],
	      "dead": ['1am-3am', '3am-5am', '5am-7am']}
	sort_ts = dict(zip(slots, range(len(slots))))
	pt_ts = dict(zip(slots, ["NPT"] * (len(slots) - 2) + (2 * ["PT"])))
	slot_times = dict(zip(slots, [get_timerange_for_slot(slot) for slot in slots]))
	reference_slot = ('9pm-11pm', -10)
	dv_df = pd.read_csv(INPUT_PATH + input_folder + "/movie_x_date_timeslot.csv")
	prior_df = pd.read_csv(INPUT_PATH + input_folder + "/prior_airings.csv")
	fox_df = pd.read_csv(INPUT_PATH + input_folder + "/fox_movies.csv")
	family_df = pd.read_csv(INPUT_PATH + input_folder + "/family_movies.csv")
	fixed_df = pd.read_csv(INPUT_PATH + input_folder + "/fixed_slots.csv")
	prior_df["type"] = "PRIOR"
	df_m = pd.concat([prior_df, fixed_df])
	business_rules = []
	business_constraints = []
	fixed_rules = []
	fixed_constraints = []
	fixed_dvs = []
	schedule_for = get_dates_in_between(from_date='2019-06-01', to_date='2019-06-30')

