# recommender engine
'''
Content based recommender  v1
Sets up the recommender model to rank list of places, to be used by the predictor

This model doesn't require any of the ML libraries, pure content matrix approach
'''

import pandas as pd
import numpy as np
import googlemaps
from utils import utilities
from typing import List, Tuple
# -- # pre-processing & pipelines
# from sklearn.decomposition import PCA, KernelPCA
# from sklearn.pipeline import Pipeline
# from sklearn.preprocessing import Imputer, LabelEncoder, StandardScaler
# # -- # model building
# from sklearn.linear_model import LinearRegression, LogisticRegression, Lasso
# # -- # scoring & validation
# from sklearn.metrics import mean_squared_log_error as msle


""" Model purpose
Using an input matrix of 2 chosen locations, rank all possible location vectors
1. Define input data matrix (assume clean data already)
2. Set up model params 

"""

# -- # Testing data input
# pd.read_csv()

def get_gmaps(key='AIzaSyBrY7HAvOgb8NHhW-mir7CQERHER8saC28'):
    gmaps = googlemaps.Client(key=key)
    return gmaps

def get_best_recs(gmaps, dfLoc, input_gpids: List[str], rectype: str, reclimit=5,
        radius=500):
    ''' generic recommender controller function to handle various scenarios
    e.g.:
        - no items in location on the list
        - not enough items on the list (should be 5, or some other number)
        - expanding the search radius and seeing how far away it is
        - calling the google api to get a 'new' item
        - saving new items to the list 
    '''
    # NOTE: TESTING
    # input_gpids = [
    #     "ChIJdedaLk5d1moRQOX0CXZWBB0",  # sthn cross
    #     "ChIJczgQh8lC1moR9r9gP44FRvY",  # chinatown
    # ]

    num_locations = len(input_gpids)
    if num_locations == 1:    
        target_lat_lon = get_latlong_from_gpid(gmaps, input_gpids[0])
    
    elif num_locations == 2:
        target_lat_lon = calc_midpoint_of_locs(gmaps, input_gpids)
    
    # NOTE: TESTING
    # target_lat_lon = (-37.823470, 144.970761)
    # rectype = 'eat'

    rec_results = rec_search_list_at_latlon(dfLoc, target_lat_lon, rectype, radius)
    if len(rec_results) < 5:
        new_results = rec_search_new_at_latlon(gmaps, target_lat_lon, rectype='restaurant')
        # TODO: 
        # set operation to remove existing gpids
        # re-ranking of new options (could be based on 'real' recommender in future)
        # add the new ones to the old ones, save to DF
        # return to the main list
    

    
def calc_midpoint_of_locs(gmaps, input_gpids: List[str]) -> Tuple[float]:
    lat1, lon1 = get_latlong_from_gpid(gmaps, input_gpids[0])
    lat2, lon2 = get_latlong_from_gpid(gmaps, input_gpids[1])
    lat_mid = (lat1 + lat2) / 2
    lon_mid = (lon1 + lon2) / 2
    return lat_mid, lon_mid

def rec_search_list_at_latlon(dfLoc, target_lat_lon: Tuple[float], rectype: str,
        reclimit=5, radius=500) -> pd.core.frame.DataFrame:

    dfLoc = dfLoc[dfLoc.Category.str.lower()==rectype]  # filter for lower only
    
    lat, lon = target_lat_lon
    # note we are relying on numpy broadcasting for the following vector calc to work
    dist = utilities.haversineVectDist(lat, lon, dfLoc.lat.to_numpy(), dfLoc.lng.to_numpy())
    
    dfRec = dfLoc[dist < radius]
    # gets the top 5 ids, sorts them by rating
    dfRec.head(reclimit).sort_values('rating', ascending=False, inplace=True)
    print(dfRec.name)
    return dfRec.gpid

def rec_search_new_at_latlon(gmaps, target_lat_lon: Tuple[float], rectype: str, reclimit=5, 
        radius=500):
    """
    Searches google maps for avaliable places at the following
    Note rectype must be "restaurant" in googlemaps, see https://developers.google.com/places/supported_types
    """
    new_places = gmaps.places_nearby(location=target_lat_lon, radius=radius, type='restaurant',
            rank_by='prominence')  # note that 'prominence' is a google term for popularity
    dfNewplaces = convert_gmaps_search_result_string_to_df(new_places)

    return dfNewplaces

def convert_gmaps_search_result_string_to_df(result_string: str) -> pd.core.frame.DataFrame:
    results = []
    for _ in new_places['results']:
        name = _['name']
        lat = _['geometry']['location']['lat']
        lng = _['geometry']['location']['lng']
        place_id = _['place_id']
        try:  # not all places have a rating
            rating = _['rating']
            user_ratings_total = _['user_ratings_total']
        except KeyError:
            rating = None
            user_ratings_total = 0
        try:  # not all places have price-level info
            price_level = _['price_level']
        except KeyError:
            price_level = None
        address = _['vicinity']
        results.append([name, lat, lng, place_id, rating, user_ratings_total, price_level, address,])

    dfResults = pd.DataFrame(results,
        columns=["name", "lat", "lng", "gpid", "rating", "user_ratings_total", "price_level", "address",])
    return dfResults

def rec_from_list(gmaps, id1, id2, dfLoc, rectype='eat', reclimit=5,radius=500):
    """ Given 2 google ids, works out where to perform a search, and does so in a radius
    Searches a pre-defined list of places

    TODO: see getBestRec function
    """

    dfLoc = dfLoc[dfLoc.Category.str.lower()==rectype]  # filter for lower only

    # NOTE TESTING
    # id1 = "ChIJdedaLk5d1moRQOX0CXZWBB0"
    # id2 = "ChIJczgQh8lC1moR9r9gP44FRvY"

    place1 = gmaps.place(place_id=id1)
    place2 = gmaps.place(place_id=id2)

    lat = place1['result']['geometry']['location']['lat']
    lng = place1['result']['geometry']['location']['lng']

    lat2 = place2['result']['geometry']['location']['lat']
    lng2 = place2['result']['geometry']['location']['lng']

    lat_mid = (lat + lat2) / 2
    lng_mid = (lng + lng2) / 2

    dist = utilities.haversineVectDist(lat_mid, lng_mid, 
        dfLoc.lat.to_numpy(), dfLoc.lng.to_numpy())
    dfRec = dfLoc[dist < radius]  # 300m walking distance

    dfRec.head(reclimit).sort_values('rating', ascending=False, inplace=True)

    return dfRec.gpid  # gets the top 5 ids


def rec_search_at_latlon_point(lat: float, lon: float, radius: int):
    """ Given a single point, search in a radius
    """
    # NOTE WIP
    return lat + lon + radius



def get_latlong_from_gpid(gmaps, gpid: str) -> Tuple[float]:
    '''
    Retrieves the lat-long position of a given google place id
    gmaps: Requires a google maps object with a valid API Key
    '''
    place_result = gmaps.place(place_id=gpid)

    lat = place_result['result']['geometry']['location']['lat']
    lng = place_result['result']['geometry']['location']['lng']
    
    return (lat, lng)
