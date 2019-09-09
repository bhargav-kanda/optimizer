import optimizer as op
from optimizer.sm_input.sm_functions import process_input
# from optimizer.sm_input.sm_rules import business_rules
import optimizer.sm_input.sm_globals as globals
# import sympy as sp

globals.init()
process_input()

sms = op.OpFormulation('star_movies', max=True)

# data = globals.dv_df
data = None
movies, i = sms.create_range(name='movie_name', index='i', data=data)
dates, j = sms.create_range(name='dates', data=data, order=op.ASCENDING, index='j')
slots, k = sms.create_range(name='slots', data=data, order=globals.sort_ts, index='k')

# prime_slots = k.filter([''])

airings = sms.create_variables(prefix='', indeces=[i, j, k], suffix=None, data=data, type=op.BINARY)

tvrs = sms.create_values('tvrs', indeces=[i, j, k], data=data, values_col='TVR')

movie_used = sms.create_variables(prefix='used', indeces=[i], type=op.BINARY)


fixed_airings = sms.create_set(name='fixed_airings', ranges=[movies, dates, slots],
                               values=globals.fixed_df[['movie_name', 'dates', 'slots']])

sundays = dates.filter(lambda row: row.weekday() == 6)

fox_movies = sms.create_set(name='family_movies', ranges=[movies], values=globals.fox_df['movie_name'])
family_movies = sms.create_set(name='family_movies', ranges=[movies], values=globals.family_df['movie_name'])

motm_originals = sms.create_set(name='motm_originals', ranges=[movies, dates, slots])
motw_originals = sms.create_set(name='motw_originals', ranges=[movies, dates, slots])

motm_originals.set_values(globals.fixed_df['type' == 'MOTM'][['movie_name', 'dates', 'slots']])
motw_originals.set_values(globals.fixed_df['type' == 'MOTW'][['movie_name', 'dates', 'slots']])


r1 = sms.add_rule(name='indicator_1', indeces=[i], lhs=op.OpSum(airings[i, :, :]), rhs=movie_used[i] * 10000000,
                      comparator=op.LESSTHAN)

r2 = sms.add_rule(name='indicator_2', indeces=[i], lhs=op.OpSum(airings[i, :, :]),
                      rhs=(movie_used[i]-1) * 10000000 + 1, comparator=op.GREATERTHAN)

sms.add_rule(name='one_movie_in_one_slot', indeces=[j, k], lhs=op.OpSum(airings[:, j, k]), rhs=1,
                 comparator=op.EQUALTO)

sms.add_rule(name='limit_slot_repetition', indeces=[i, k], lhs=op.OpSum(airings[i, :, k]),
                 rhs='max_value_or_fixed_number(3, movies, slots, None)', comparator=op.LESSTHAN)

sms.add_rule(name='prevent_slot_repetetion_next_10days', indeces=[i, j, k],
                 lhs=op.OpSum(airings[i, j:j+10, k]), comparator=op.LESSTHAN, rhs=1)

sms.add_rule(name='max_one_airing_per_day', indeces=[i, j], lhs=op.OpSum(airings[i, [j, j+1], :]),
                 rhs='max_value_or_fixed_number(1, movies, None, all_dates)', comparator=op.LESSTHAN)

sms.add_rule(name='max_airings_per_movie', indeces=[i], lhs=op.OpSum(airings[i, :, :]),
                 comparator=op.LESSTHAN, rhs='get_max_airings_for_title(movies)')

sms.add_rule(name='family_movies_on_sundays', indeces=[sundays, k.filter([1, 2])],
                 lhs=op.OpSum(airings[family_movies, j, k]),
                 comparator=op.GREATERTHAN, rhs=1)

sms.add_rule(name='remove_motm_before', indeces=motm_originals, lhs=op.OpSum(airings[i, :j, :]), rhs=0,
                 comparator=op.LESSTHAN)

sms.add_rule(name='repeat_motw_nextday', indeces=motw_originals, )


tvrs.set_values(globals.dv_df, 'TVR')
problem = sms.create_problem(data=globals.dv_df)
# test_rule.create_constraints()
# r1.create_constraints()
# r2.create_constraints()


# problem = op.OpProblem(
#     name='Star_Movies_Scheduling',
#     # partial_solution=op.PartialSolution(
#     # 	dvs=airings,
# 	#     values=globals.fixed_df['partial'],
# 	# ),
# 	# initial_solution=op.InitialSolution(
# 	# 	values=data['initial'],
# 	# 	cost_to_change=data['cost']
# 	# ),
# 	objective_function=op.DotProduct(tvrs, airings),
# 	max=True,
# )

# problem.formulate(data=globals.dv_df)

problem.save('')

optimal = problem.solve(6000, 4)

# create_schedule_output(optimal, problem.name)

