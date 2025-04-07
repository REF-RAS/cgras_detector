# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

from detector.models import logger
from detector.model import DETECT_DAO

class HealthEvaluateTaskHelper():
    @staticmethod
    def generate_function(func_name, func_def):
        if func_name in locals():
            if not DETECT_DAO.exist_health_model_func_name(func_name):
                raise AssertionError(f'The function name {func_name} clashes with a local identifier')
        try:
            exec(func_def)
        except Exception as e:
            raise AssertionError(f'Invalid function definition: {e}')
        if func_name not in locals():
            raise AssertionError(f'The function name in the definition is different from the one in the specification ({func_name})')
        return locals()[func_name]

class HealthEvaluateTaskModel():
    DEFAULT_NAME = '_default'
    def __init__(self):
        self.health_model_species_map = dict()

    # return a health value from -1 to +1 with 0 as the health/unhealthy divider
    def _evaluate_health_index(self, species:str, count_data:list) -> float:
        if species is None:
            return None
        if species in self.health_model_species_map:
            func = self.health_model_species_map[species]
        elif HealthEvaluateTaskModel.DEFAULT_NAME in self.health_model_species_map:
            func = self.health_model_species_map[species]
        else:
            health_model_dict = DETECT_DAO.get_health_model(species)
            if health_model_dict is None:
                return None
            try:
                func = HealthEvaluateTaskHelper.generate_function(health_model_dict['func_name'], health_model_dict['func_def'])
                self.health_model_species_map[species] = func
            except Exception as e:
                logger.warning(e)
                return None 
        return func(count_data)

    def detect_stat_to_cache_tile_health(self, tile_id_list:list=None, season:str=None):
        if tile_id_list is None:
            if season is None:
                raise AssertionError(f'{type(self).__name__} (cache_tile_health_from_detect_stat): The season cannot be None if tile_id_list is None')
            tile_id_list = DETECT_DAO.get_distinct_tile_id_as_list(season)
        elif type(tile_id_list) == str:
            tile_id_list = [tile_id_list]
        for tile_id in tile_id_list:
            tile_sample_info_list = DETECT_DAO.get_tile_sample_of_tile_id(tile_id, limit=1)
            # if there is no tile sample added to the coral counting system, skip this tile_id
            if tile_sample_info_list is None or len(tile_sample_info_list) == 0:
                continue
            tile_sample_info = tile_sample_info_list[0]
            # query the stat of the tile_id
            stat_list = DETECT_DAO.get_detect_stat_of_tile_id(tile_id)
            # if either no tile sample or the tile sample has not been processed, insert a placeholder to the cache for display
            num_samples = len(stat_list)
            if num_samples == 0:
                DETECT_DAO.update_basic_cache_tile_health_stat(tile_id, season, tile_sample_info['species'], tile_sample_info['settle_time'])
                continue
            # iterate through the detect stat of the tile id and collect statistics of the history of tile samples of the tile id
            count_data = []
            loss_rate_whole = loss_rate_recent = -1  # default value
            for index, stat in enumerate(stat_list):
                # if this is the earliest (or the only) tile sample, extract the statistics about the start of the tile
                if index == 0:
                    coral_count_start, age_start = stat['coral_alive_count'], stat['age']
                    species, season, settle_time = stat['species'], stat['season'], stat['settle_time']
                count_data.append({ 'coral_alive_count': stat['coral_alive_count'],
                                    'other_count': stat['other_count'],
                                    'coral_dead_count': stat['coral_dead_count'],
                                    'age': stat['age'],
                                })
                # if this is the latest tile sample, extract the statistics about the end of the tile
                if index == len(stat_list) - 1:
                    coral_count_latest, other_object_count_latest, dead_coral_count_latest = stat['coral_alive_count'], stat['other_count'], stat['coral_dead_count']
                    age_latest, batch_time_latest = stat['age'], stat['batch_time']
                    # the trend parameters can only be computed if there are two or more tile samples in the history
                    if len(stat_list) > 1:
                        loss_rate_recent = stat['coral_alive_count'] - stat_list[index - 1]['coral_alive_count']
                        if age_latest - stat_list[index - 1]['age'] >= 1:
                            loss_rate_recent = loss_rate_recent / (age_latest - stat_list[index - 1]['age'])
                        else:
                            loss_rate_recent = None
                        if age_latest - age_start >= 1:
                            loss_rate_whole = (coral_count_latest - coral_count_start) / (age_latest - age_start)
                        else:
                            loss_rate_whole = None
            
            # compute the health index
            health_index = self._evaluate_health_index(species, count_data)
            # store the health stat to the db
            DETECT_DAO.update_cache_tile_health_stat(tile_id, season, species, settle_time, coral_count_start, age_start, coral_count_latest, dead_coral_count_latest,
                                                other_object_count_latest, age_latest, batch_time_latest, loss_rate_whole, loss_rate_recent, num_samples, health_index, count_data)


# - test functions
def test_generate_function():
    FUNC_DEF = """
def eval_acropora_palmata(count_data):
    nominal_loss_rate_per_day = 0.015
    if len(count_data) <= 1:
        return 0   # neutral health index
    for index, data in enumerate(count_data):
        if index == 0:
            coral_count_start = data['coral_alive_count']
            age_start = data['age']
        elif index == len(count_data) - 1:
            coral_count_end = data['coral_alive_count']
            age_end = data['age']
    nominal_coral_count_end = coral_count_start - ((nominal_loss_rate_per_day * coral_count_start)  * (age_end - age_start))
    nominal_coral_count_end = max(0, nominal_coral_count_end)
    if coral_count_end > nominal_coral_count_end:
        score = (coral_count_end - nominal_coral_count_end) / (coral_count_start - nominal_coral_count_end)
        score = min(1.0, score)
    else:
        score = -(coral_count_start - coral_count_end) / (coral_count_start - nominal_coral_count_end) + 1
        score = max(-1.0, score)
    return score
"""
    func = HealthEvaluateTaskHelper.generate_function('eval_acropora_palmata', FUNC_DEF)
    return func

# the health indexing function for testing
def eval_acropora_palmata(count_data):
    nominal_loss_rate_per_day = 0.015
    if len(count_data) <= 1:
        return 0   # neutral health index
    for index, data in enumerate(count_data):
        if index == 0:
            coral_count_start = data['coral_alive_count']
            age_start = data['age']
        elif index == len(count_data) - 1:
            coral_count_end = data['coral_alive_count']
            age_end = data['age']
    nominal_coral_count_end = coral_count_start - ((nominal_loss_rate_per_day * coral_count_start)  * (age_end - age_start))
    nominal_coral_count_end = max(0, nominal_coral_count_end)
    if coral_count_end > nominal_coral_count_end:
        score = (coral_count_end - nominal_coral_count_end) / (coral_count_start - nominal_coral_count_end)
        score = min(1.0, score)
    else:
        score = -(coral_count_start - coral_count_end) / (coral_count_start - nominal_coral_count_end) + 1
        score = max(-1.0, score)
    return score

# test using the above function in a dynamic function definition to compute the health index
def test_health_model_func(func=None):
    count_data = []
    coral_count_start = 2000
    nominal_loss_rate_per_day = 0.015
    nominal_loss_per_day = coral_count_start * nominal_loss_rate_per_day
    actual_loss_per_day = coral_count_start * (nominal_loss_rate_per_day * 0.5)  # 120% of the nominal loss rate
    age_start = 3
    age_end = 50
    for age in range(age_start, age_end, 7):
        count_data.append({ 'coral_alive_count': coral_count_start - (age - age_start) * actual_loss_per_day,
                            'other_count': 0,
                            'coral_dead_count': 0,
                            'age': age
                            })
    if func is not None:
        health_index = func(count_data)
    else:
        health_index = eval_acropora_palmata(count_data)
    print(f'health index: {health_index}')

# test the HealthEvaluateTaskModel class
def test_update_cache_tile_health_model():
    health_task_model = HealthEvaluateTaskModel()
    health_task_model.detect_stat_to_cache_tile_health(season='2024Oct')

    tile_df = DETECT_DAO.list_tiles_in_tile_sample()
    DETECT_DAO.add_tile_df_to_cache_tile_health(tile_df)
    logger.info(f'cache health: {DETECT_DAO.list_all_cache_tile_health()}')  

if __name__ == '__main__':
    # func = test_generate_function()
    # test_health_model_func(func)

    test_update_cache_tile_health_model()
