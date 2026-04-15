import optimizer as op
from optimizer.rule_types import *
from optimizer.lp_formulation import *
from optimizer.sm_input.sm_functions import *


business_rules = []
# Only one movie in each slot
business_rules.append(op.Rule(name='one_movie_in_one_slot', indeces=[j, k], lhs=op.Sum(dvs[:, j, k]), rhs=1, comparator=op.EQUALTO))



#Restricted movies
# restricted_movies = GeneralRule('restricted_movies').set_applicability(movies=get_restricted_movies())\
# 	.set_constraint(slots=['7am-9am'], dates=[], max=0)
# business_rules.append(restricted_movies)


business_rules.append(op.Rule(name='limit_slot_repetition', indeces=[i, k], lhs=op.Sum(dvs[i, :, k]),
                              rhs='max_value_or_fixed_number(3, movies, slots, None)', comparator=op.LESSTHAN))

# Do not repeat same slot in next 10 days
prevent_slot_repetetion_next_10days = Rule(name='prevent_slot_repetetion_next_10days')\
	.set_applicability(movies=get_unique_movies(), dates=[], slots=[])\
	.set_constraint(relative_dates=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], relative_slots=[0], max=1,
                    exclude_check='exclude_slot_repeat_10days(movies, slots)')
business_rules += [limit_slot_repetition, prevent_slot_repetetion_next_10days]


# Only one airing in 2 days
max_one_airing_per_day = GeneralRule('max_one_airing_per_day').set_applicability(
	movies=get_unique_movies(), dates=[], exclude=get_fixed_airings('MOTM') + get_fixed_airings('MOTW') +
	                                              get_fixed_airings('TUNEIN'))\
	.set_constraint(slots=[], relative_dates=[0, 1], max='max_value_or_fixed_number(1, movies, None, all_dates)')
business_rules.append(max_one_airing_per_day)


# Max of contractual airings left for all movies
max_airings_per_movie = GeneralRule('max_airings_per_movie').set_applicability(movies=get_unique_movies())\
	.set_constraint(dates=[], slots=[], max='get_max_airings_for_title(movies)')
business_rules.append(max_airings_per_movie)


# Holdback for original airings
holdback_original_airings = GeneralRule('holdback_original_airings').set_applicability(airings=get_original_airings())\
	.set_constraint(relative_dates=list(range(-7, 1)), max=1)
business_rules.append(holdback_original_airings)


# Family movies
family_movies_on_sundays = GeneralRule('family_movies_on_sundays').set_applicability\
	(dates=get_all_of('dates', {'week_day': ['Sunday']}), slots=['9am-11am', '11am-1pm'])\
	.set_constraint(movies=get_family_movies(), min=1)
business_rules.append(family_movies_on_sundays)


# Highperforming titles - utilize all the runs
use_all_highperforming_titles = GeneralRule('use_all_highperforming_titles').set_applicability(movies=get_high_performing_titles())\
	.set_constraint(dates=[], slots=[], min='get_run_count_for_title(movies)')
business_rules.append(use_all_highperforming_titles)


# MOTM
remove_motm_before = GeneralRule('remove_motm_before').set_applicability(airings=[get_fixed_airings('MOTM')[0]])\
	.set_constraint(dates='get_previous_dates(dates)', slots=[], max=0)
# repeat_motm_after = GeneralRule('repeat_motm_after').set_applicability(airings=[get_fixed_airings('MOTM')[0]])\
# 	.set_constraint(relative_dates=list(range(1, 29)), slots=get_npt_slots(), min=4)
fixed_rules += [remove_motm_before]


# MOTW
repeat_motw_nextday = GeneralRule('repeat_motw_nextday').set_applicability(airings=get_fixed_airings('MOTW'))\
	.set_constraint(relative_dates=[1], slots=['9am-11am', '11am-1pm', '1pm-3pm', '3pm-5pm'], min=1)
airings = [a for a in get_fixed_airings('MOTW') if a['movies'] != 'EFF-LOGAN']
repeat_motw_in_week = GeneralRule('repeat_motw_in_week').set_applicability(airings=airings)\
	.set_constraint(relative_dates=list(range(2, 8)), slots=[], min=1)
repeat_motw_next_week = GeneralRule('repeat_motw_next_week').set_applicability(airings=airings)\
	.set_constraint(relative_dates=list(range(8, 15)), slots=[], min=1)
fixed_rules += [repeat_motw_in_week, repeat_motw_nextday, repeat_motw_next_week]

# Fox 1+1 constraint
enforce_repeat = GeneralRule('enforce_repeat').set_applicability(movies=get_fox_movies('original'), dates=[])\
	.set_constraint(movies=['get_fox_repeat(movies)'], relative_dates=list(range(1, 8)),
                    min='get_sum_of_airings_today(movies, dates)', scale_min_rule=False)
no_original_last_day = GeneralRule('no_original_last_day').set_applicability(movies=get_fox_movies('original'))\
	.set_constraint(dates=[get_all_of('dates')[-1]], max=0)
start_with_original = SequenceRule('start_with_original').set_applicability(movies=get_fox_movies())\
	.set_constraint(movies=['get_fox_original(movies)', 'get_fox_repeat(movies)'], dates=get_all_of('dates'))
repeat_after_original = SequenceRule('repeat_after_original').set_applicability(movies=get_fox_movies(), dates=[],
                                                                                within_day=True)\
	.set_constraint(movies=['get_fox_original(movies)', 'get_fox_repeat(movies)'])
original_after_repeat = SequenceRule('original_after_repeat').set_applicability(movies=get_fox_movies(), dates=[],
                                                                                within_day=True)\
	.set_constraint(movies=['get_fox_repeat(movies)', 'get_fox_original(movies)'])
business_rules += [no_original_last_day, start_with_original, enforce_repeat, repeat_after_original,
                           original_after_repeat]


# Timing Constraints
MIN_START = 0
MAX_START = 119
slot_9pm = ContinuityRule('9pm-11pm_start_rule').set_time_constraint(slots=['9pm-11pm'], min_start=-10, max_start=-10)
slot_11pm = ContinuityRule('11pm-1am_start_rule').set_time_constraint(slots=['11pm-1am'], min_start=-30, max_start=119)
slot_7pm = ContinuityRule('7pm-9pm_start_rule').set_time_constraint(slots=['7pm-9pm'], min_start=0, max_start=110)
business_rules += [slot_9pm, slot_7pm, slot_11pm]
all_slots = get_all_of('slots') + ['1am-3am']
all_slots.remove('9pm-11pm')
all_slots.remove('7pm-9pm')
all_slots.remove('11pm-1am')
for slot in all_slots:
	rule = ContinuityRule(slot+'_start_rule').set_time_constraint(slots=[slot], min_start=MIN_START, max_start=MAX_START)
	business_rules.append(rule)

exclude_timerules = [{'dates': 21}]
if exclude_timerules:
	for rule in [r for r in business_rules if type(r).__name__ == 'ContinuityRule']:
		rule.set_applicability(exclude=exclude_timerules)
