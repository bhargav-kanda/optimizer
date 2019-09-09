# from optimiser.rule_types import *
# from optimiser.sm_input.sm_functions import *
#
#
# # april1st_movies = []
# # pop_up_theatre = GeneralRule('pop_up_theatre').set_applicability(airings=get_fixed_airings('POP'))\
# # 	.set_constraint(dates='get_previous_dates(dates, base=13)', slots=[], max=0)
# # globals.fixed_rules.append(pop_up_theatre)
#
#
# # do_not_schedule_movies = ['EFF-THE BOSS BABY']
# # if do_not_schedule_movies:
# # 	exclude_movies = GeneralRule('exclude_movies').set_applicability(movies=do_not_schedule_movies)\
# # 		.set_constraint(dates=[], slots=[], max='get_fixed_number(movies)')
# # 	globals.fixed_rules.append(exclude_movies)
#
#
# #Enforce movies in plan
# # movies = ["EFF-AVATAR", "EFF-TITANIC"]
# # enforce_movies = GeneralRule('enforce_movies').set_applicability(movies=movies).set_constraint(dates=[], slots=[], min=1)
# # globals.business_rules.append(enforce_movies)
#
# # a1 = GeneralRule('Logan').set_applicability(movies=['EFF-LOGAN']).set_constraint(dates=list(range(18, 25)),
# #                                                                                 slots=get_npt_slots(), min=1)
# # a2 = GeneralRule('xmen1').set_applicability(movies=['EFF-X-MEN APOCALYPSE']).set_constraint(dates=list(range(18, 25)),
# #                                                                                 slots=get_npt_slots(), min=1)
# # a3 = GeneralRule('xmen2').set_applicability(movies=['EFF-X-MEN FIRST CLASS']).set_constraint(dates=list(range(18, 25)),
# #                                                                                 slots=get_npt_slots(), min=1)
# # globals.fixed_rules.append(a1)
# fixed_rules = []
# # Fixed slots
# enforce_fixed_slots = GeneralRule('enforce_fixed_slots').set_applicability(airings=get_fixed_airings())\
# 	.set_constraint(min=1, max=1)
# fixed_rules.append(enforce_fixed_slots)
#
#
#
#
