import json
import requests
import time
from argparse import ArgumentParser


URL_SUMMARY = 'https://www.truegamedata.com/getShare.php'
URL_BASE_STATS = 'https://www.truegamedata.com/SQL_calls/base_data.php'
CRAWL_DELAY = 1


def get_summary(share_link):
    data = dict(shareToken=share_link.split('share=')[-1])
    r = requests.post(URL_SUMMARY, data=data)
    time.sleep(CRAWL_DELAY)
    return r.json()


def get_damage_profile(gun, mode, damage_type='Default'):
    weapon_name = json.dumps([gun, mode])
    data = dict(weapon_name=weapon_name)
    r = requests.post(URL_BASE_STATS, data=data)
    time.sleep(CRAWL_DELAY)
    base_stats = r.json()
    damage_data = json.loads(base_stats[0]['damage_data'])
    profile = damage_data[damage_type]
    return profile


def get_weapons_data(link):
    summary = get_summary(link)
    weapons = summary[0]
    mode = summary[-1]
    gun_counts = {}
    out = []
    for wpn in weapons:
        gun = wpn['gun']
        if gun in gun_counts.keys():
            gun_counts[gun] += 1
            gun_name = f"{gun} ({gun_counts[gun]})"
        else:
            gun_counts[gun] = 1
            gun_name = gun
        stats = wpn['summaryStats']
        fire_rate, range_modifier, ads, sprint_to_fire, tactical_sprint_to_fire = stats[:5]
        bullet_velocity, reload_time, mag_size = stats[10:13]
        damage_profile = get_damage_profile(gun, mode)
        for d in damage_profile:
            d['dropoff'] = d['dropoff'] * (1 + range_modifier)
        out.append(dict(
            gun=gun_name,
            fire_rate=fire_rate,
            range_modifier=range_modifier,
            ads=ads,
            sprint_to_fire=sprint_to_fire,
            tactical_sprint_to_fire=tactical_sprint_to_fire,
            bullet_velocity=bullet_velocity,
            reload_time=reload_time,
            mag_size=mag_size,
            damage_profile=damage_profile,
        ))
    return out


if __name__ == '__main__':
    # Test link 1: 'https://www.truegamedata.com?share=ge4jvU'
    # Test link 2: 'https://www.truegamedata.com?share=PQDWpQ'
    # Test link 3: 'https://www.truegamedata.com?share=7E4ESl'
    # Test link 4: 'https://www.truegamedata.com?share=9xBkmS'
    parser = ArgumentParser()
    parser.add_argument("link")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()
    weapons_data = get_weapons_data(args.link)
    print(weapons_data)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json.dumps(weapons_data, indent=2))
