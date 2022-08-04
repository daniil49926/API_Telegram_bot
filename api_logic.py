import os
import json
import datetime
import requests
from typing import List, Dict
from load_env import load_environ

load_environ()

base_url = "https://hotels4.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": os.environ.get('RAPIDAPI_KEY'),
    "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
}


def make_get_request(url: str, head: Dict, querystring: Dict) -> requests.Response:
    try:
        return requests.request('GET', url=url, headers=head, params=querystring, timeout=10)
    except requests.exceptions.ReadTimeout as e:
        print(e)


def get_landmark_destination_id(city: str) -> int | bool:
    url = base_url + '/locations/v2/search'
    querystring = {"query": city}

    response = make_get_request(url=url, head=headers, querystring=querystring)

    if response and response.status_code == 200:
        body = json.loads(response.text)
        try:
            return body['suggestions'][0]['entities'][0]['destinationId']
        except IndexError as e:
            print(e)
        except KeyError as e:
            print(e)
    return False


def get_hotel(
        destination_id: int,
        count: int,
        sort_hotel: str,
        p_range: str,
        d_range: str,
        check_in: datetime.date,
        check_out: datetime.date
) -> List[Dict] | bool:

    dict_of_transform_sort = {
        'ASC': 'PRICE',
        'DESC': 'PRICE_HIGHEST_FIRST'
    }

    url = base_url + '/properties/list'

    if check_in is None:
        check_in = datetime.date.today()
    if check_out is None:
        check_out = datetime.date.today()

    querystring = {
        "destinationId": destination_id,
        "pageNumber": "1",
        "pageSize": "25",
        "checkIn": check_in,
        "checkOut": check_out,
        "adults1": "1",
        "sortOrder": dict_of_transform_sort[sort_hotel],
        "locale": "en_US",
        "currency": "USD"
    }
    if p_range:
        start_price, stop_price = p_range.split('-')
        querystring = {
            "destinationId": destination_id,
            "pageNumber": "1",
            "pageSize": "25",
            "checkIn": check_in,
            "checkOut": check_out,
            "adults1": "1",
            "priceMin": start_price,
            "priceMax": stop_price,
            "sortOrder": "DISTANCE_FROM_LANDMARK",
            "locale": "en_US",
            "currency": "USD",
            "landmarkIds": "City Center"
        }

    response = make_get_request(url=url, head=headers, querystring=querystring)
    if response and response.status_code == 200:
        body = json.loads(response.text)
        results = body['data']['body']['searchResults']['results']

        data_to_ret = []
        try:
            if not d_range:
                for i_res in results[:count]:
                    data_to_ret.append({
                        'id': f"{i_res['id']}",
                        'name': f"{i_res['name']}",
                        'address': f"{i_res['address']['locality']} {i_res['address']['streetAddress']}",
                        'distance_to_the_center': f"{i_res['landmarks'][0]['distance']}",
                        'price': f"{i_res['ratePlan']['price']['current']}",
                    })
            else:
                i = 0
                start_dist, stop_dist = d_range.split('-')
                while len(data_to_ret) < count:
                    if float(start_dist) < float(results[i]['landmarks'][0]['distance'].split(' ')[0]) < float(stop_dist):
                        data_to_ret.append({
                            'id': f"{results[i]['id']}",
                            'name': f"{results[i]['name']}",
                            'address': f"{results[i]['address']['locality']} {results[i]['address']['streetAddress']}",
                            'distance_to_the_center': f"{results[i]['landmarks'][0]['distance']}",
                            'price': f"{results[i]['ratePlan']['price']['current']}"
                        })
                    i += 1
            return data_to_ret
        except IndexError as e:
            print(e)
        except KeyError as e:
            print(e)
    return False


def get_hotel_photos(hotels: Dict, count_photos: int) -> List[str] | bool:
    url = base_url + '/properties/get-hotel-photos'
    querystring = {"id": hotels['id']}

    response = make_get_request(url=url, head=headers, querystring=querystring)
    if response and response.status_code == 200:
        body = json.loads(response.text)
        photos_list = []
        for i in range(count_photos):
            photos_list.append(body['hotelImages'][i]['baseUrl'])
        return photos_list
    return False
