import os
import time
import json
import random
import requests
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon


base_path = os.path.dirname(os.path.abspath(__file__))
sectors = {}

def fill_sectors(gdf):
    for i, row in gdf.iterrows():
        sector_id = row["CD_SETOR"]
        municipio_setor = row["NM_MUN"]
        distrito_setor = row["NM_DIST"]
        geom = row["geometry"]
        
        coords = []
        if isinstance(geom, Polygon):
            coords = list(geom.exterior.coords)
        elif isinstance(geom, MultiPolygon):
            for polygon in geom.geoms:
                coords.extend(polygon.exterior.coords)
        coords_2d = [(x, y) for x, y, z in coords]

        sectors[sector_id] = {
            "municipio_setor": municipio_setor,
            "distrito_setor": distrito_setor,
            "coords": coords_2d,
            "ads": []
        }
    
    return sectors


def get_bounds():
    [west, south, east, north] = gdf.total_bounds
    return { "east": float(east), "north": float(north), "south": float(south), "west": float(west) }


def get_payload_structure():
    json_file_path = os.path.join(base_path, os.pardir, 'src/utils', 'request.json')
    json_file_path = os.path.abspath(json_file_path)

    payload = {}
    with open(json_file_path, 'r') as file:
        payload = json.load(file)
    
    payload["filters"]["location"]["viewport"] = get_bounds()
    payload["pagination"] = { "pageSize": 250, "offset": 0 }

    return payload


def get_headers():
    json_file_path = os.path.join(base_path, os.pardir, 'src/utils', 'headers.json')
    json_file_path = os.path.abspath(json_file_path)

    headers = {}
    with open(json_file_path, 'r') as file:
        headers = json.load(file)
    
    return headers


def get_geojson_property(coords):
    geojson_obj = {
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': []
        },
        'properties': {}
    }

    coords_geojson = []
    for i in range(len(coords)):
        x = coords[i][0]
        y = coords[i][1]
        coords_geojson.append([x, y])
    
    geojson_obj["geometry"]["coordinates"].append(coords_geojson)

    return json.dumps(geojson_obj)


def make_request(payload, headers, sector_id, qnt_ads_analyzed):
    base_url = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/list"
    payload["filters"]["location"]["geoJson"] = get_geojson_property(sectors[sector_id]["coords"])

    print(f"Analisando setor {sector_id} em {sectors[sector_id]["distrito_setor"]} - {sectors[sector_id]["municipio_setor"]}")

    try:
        response = requests.post(base_url, json=payload, headers=headers)
    except requests.exceptions.ConnectionError as e:
        print("No internet connection. Waiting 5 minutes until making request again")
        time.sleep(300)
        response = requests.post(base_url, json=payload, headers=headers)
    except Exception as e:
        print("Unexpected error", e)
        return

    if response.ok:
        data = response.json()
        
        print(f"{len(data['hits']['hits'])} ad(s) identified in the sector")
        for i in range(len(data['hits']['hits'])):
            sectors[sector_id]["ads"].append(data['hits']['hits'])

            if i == len(data['hits']['hits'] - 1):
                print("Ads collected successfully")
                qnt_ads_analyzed += len(data['hits']['hits'])
                print(f"Total: {qnt_ads_analyzed}")
    else:
        print("Error", response.status_code)
    
    print("")
    time.sleep(random.uniform(1, 3))


def export_sectors(filename):
    sectors_no_coords = {
        id: {k: v for k, v in data.items() if k != "coords"}
        for id, data in sectors.items()
    }

    json_file_path = os.path.join(base_path, os.pardir, 'src/export', f'sectors-{filename.split(".")[0]}.json')
    json_file_path = os.path.abspath(json_file_path)
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(sectors_no_coords, f, ensure_ascii=False, indent=2)


for filename in os.listdir("src/data"):
    print(filename)
    gdf = gpd.read_file(f"src/data/{filename}")

    sectors = fill_sectors(gdf)
    payload = get_payload_structure()
    headers = get_headers()

    qnt_ads_analyzed = 0

    for id in sectors.keys():
        try:
            make_request(payload, headers, id, qnt_ads_analyzed)
            export_sectors(filename)
        except requests.exceptions.ConnectionError:
            print("No internet connection. Waiting 5 minutes until making request again")
    
    print("All ads collected successfully!") 
