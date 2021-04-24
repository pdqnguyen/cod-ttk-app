import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker
import matplotlib.patches as patches
from argparse import ArgumentParser

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS

plt.switch_backend('Agg')
plt.rcParams['font.size'] = 18
plt.style.use('dark_background')


# Hitbox was generated externally with photoshop and some down-sampling
DEFAULT_HITBOX_FILEPATH = 'hitbox_cod1.npy'
# The "regions" are painted in with the following grayscale colors:
HITBOX_REGIONS = {'head': 255, 'chest': 207, 'stomach': 126, 'extremities': 71, 'miss': 0}

# Load hit-box array and transpose it so that rows -> X values and columns -> Y values
HITBOX = np.load(DEFAULT_HITBOX_FILEPATH)[::-1].T

# Model height scale is the ratio of the model height in the image, as a percentage of image height,
# to the physical model height in meters. The hitbox used by default has a height about 85% of the
# image height and estimated 1.8m ~ 6ft physical height.
MODEL_HEIGHT_RATIO = 0.85
MODEL_HEIGHT_METERS = 1.8
IM_SCALE = MODEL_HEIGHT_RATIO / MODEL_HEIGHT_METERS * HITBOX.shape[1]


def get_aim_center(offset, hitbox=HITBOX):
    offset_x = offset[0] * MODEL_HEIGHT_RATIO
    offset_y = offset[1] * MODEL_HEIGHT_RATIO
    im_center = (int(hitbox.shape[0] / 2), int(hitbox.shape[1] / 2))
    aim_x = im_center[0] + int(offset_x * hitbox.shape[0])
    aim_y = im_center[1] + int(offset_y * hitbox.shape[1])
    center = (aim_x, aim_y)
    return center


def generate_dmg_maps(profile, hitbox=HITBOX, hitbox_regions=HITBOX_REGIONS):
    num_segments = len(profile)
    out = np.zeros((num_segments, *hitbox.shape), dtype=float)
    for i in range(out.shape[0]):
        dmg = {v: profile[i][k] for k, v in hitbox_regions.items() if k != 'miss'}
        for k, v in dmg.items():
            out[i, hitbox == k] = v
    return out


def generate_target_map(shape, distance, aim_center, spread):
    x_spread = spread[0] * (np.pi / 180.) * distance * IM_SCALE
    y_spread = spread[1] * (np.pi / 180.) * distance * IM_SCALE
    target_map = np.zeros(shape, dtype=float)
    Y, X = np.meshgrid(range(shape[0]), range(shape[1]))
    xa, xb = aim_center[0] - x_spread / 2, aim_center[0] + x_spread / 2
    ya, yb = aim_center[1] - y_spread / 2, aim_center[1] + y_spread / 2
    target_map[(X > xa) & (X < xb) & (Y > ya) & (Y < yb)] = 1
    target_map /= target_map.sum()
    return target_map


def measure_stk_ttk(dpr, distance, wpn):
    hp = 250.0
    stk = int(np.ceil(hp / dpr))
    rps = wpn['fire_rate'] / 60.
    t_travel = distance / wpn['bullet_velocity']
    t_reload = wpn['reload_time'] * int(stk / wpn['mag_size'])
    ttk = hp / (dpr * rps) + t_travel + t_reload
    return stk, ttk


def analyze(weapons, distances, center, hitbox=HITBOX, hitbox_regions=HITBOX_REGIONS):
    num_distances = len(distances)
    stk = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    ttk = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    stk_nr = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    ttk_nr = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    for wpn in weapons:
        gun = wpn['gun']
        damage_profile = wpn['damage_profile']
        dmg_maps = generate_dmg_maps(damage_profile, hitbox=hitbox, hitbox_regions=hitbox_regions)
        edges = [d['dropoff'] for d in damage_profile]
        edges.append(1e99)
        for i in range(len(edges) - 1):
            dmg_map = dmg_maps[i]
            dpr_nr = dmg_map[center[0], center[1]]
            if dpr_nr > 0:
                a, b = edges[i: i + 2]
                segment = (distances >= a) & (distances < b)
                distances_segment = distances[segment]
                stk_segment = np.zeros(len(distances_segment))
                ttk_segment = np.zeros(len(distances_segment))
                stk_nr_segment = np.zeros(len(distances_segment))
                ttk_nr_segment = np.zeros(len(distances_segment))
                for j, distance in enumerate(distances_segment):
                    distance = distances_segment[j]
                    spread = wpn['spread']
                    target_map = generate_target_map(dmg_map.shape, distance, center, spread)
                    dpr = np.sum(dmg_map * target_map)
                    stk_segment[j], ttk_segment[j] = measure_stk_ttk(dpr, distance, wpn)
                    stk_nr_segment[j], ttk_nr_segment[j] = measure_stk_ttk(dpr_nr, distance, wpn)
                stk[gun][segment] = stk_segment
                ttk[gun][segment] = ttk_segment
                stk_nr[gun][segment] = stk_nr_segment
                ttk_nr[gun][segment] = ttk_nr_segment
            else:
                raise ValueError("Aim center must be inside of hitbox")
    results = (stk, ttk, stk_nr, ttk_nr)
    return results


def plot_results(fig, distances, data, results, log_x=False, log_y=False):
    stk, ttk, stk_nr, ttk_nr = results
    guns = list(stk.keys())
    ttk_min = min([ttk[gun].min() for gun in guns])
    ttk_max = max([ttk[gun].max() for gun in guns])
    fig.data = []
    for i, gun in enumerate(guns):
        wpn = data[i]
        color = DEFAULT_PLOTLY_COLORS[i]
        line1 = go.Scatter(
            mode='lines',
            x=distances,
            y=ttk[gun],
            name=gun,
            line=dict(color=color)
        )
        line2 = go.Scatter(
            mode='lines',
            x=distances,
            y=ttk_nr[gun],
            name=gun + ' (no recoil)',
            line=dict(color=color, dash='dash'),
            # showlegend=False,
        )
        traces = [line1, line2]
        mag_cap = np.argmax(stk[gun] >= wpn['mag_size']) - 1
        if mag_cap > 0:
            line3 = go.Scatter(
                mode='markers',
                x=[distances[mag_cap]],
                y=[ttk[gun][mag_cap]],
                name=gun + ' mag cap',
                marker=dict(color=color, size=10, symbol='star'),
                showlegend=False,
            )
            traces.append(line3)
        fig.add_traces(traces)
    if log_x:
        fig.update_xaxes(title_text="Distance [m]", range=[1, np.log10(max(distances))], type='log', tickformat='.1r')
    else:
        fig.update_xaxes(title_text="Distance [m]", range=[0, max(distances)], type='linear')
    if log_y:
        fig.update_yaxes(title_text="Time-to-kill [s]", range=[np.log10(ttk_min), np.log10(ttk_max)], type='log', tickformat='.1r')
    else:
        fig.update_yaxes(title_text="Time-to-kill [s]", range=[0, ttk_max], type='linear')

    return fig


def tick_format(value):
    exp = np.floor(np.log10(value))
    base = value / 10 ** exp
    if int(base) != 1 and int(base) % 2 != 0:
        return ''
    elif exp >= 0:
        return '${0:d}$'.format(int(value))
    else:
        return '${0:.1f}$'.format(value)


def plot_target_area(weapon_data, distance, center, zoom=1, fov=80, hitbox=HITBOX):
    fov_rad = fov * np.pi / 180.
    screen_width = 10
    screen_aspect = 16 / 9.
    # im_center = (int(hitbox.shape[0] / 2), int(hitbox.shape[1] / 2))
    spread = weapon_data['spread']
    x_spread = spread[0] * (np.pi / 180.) * distance * IM_SCALE
    y_spread = spread[1] * (np.pi / 180.) * distance * IM_SCALE
    target_x0 = center[0] - x_spread / 2
    target_y0 = center[1] - y_spread / 2
    target_rect = patches.Rectangle((target_x0, target_y0), x_spread, y_spread,
                                    linewidth=1, edgecolor='r', facecolor='none')
    fig, ax = plt.subplots(1, 1, figsize=(screen_width, screen_width / screen_aspect))
    ax.set_position([0, 0, 1, 1])
    ax.imshow(hitbox.T, origin='lower', cmap='gray')
    ax.plot(center[0], center[1], 'r+', ms=10)
    ax.add_patch(target_rect)
    ax.set_aspect('equal')
    ax.set_xlim(
        center[0] - 0.5 * fov_rad * distance * IM_SCALE / zoom,
        center[0] + 0.5 * fov_rad * distance * IM_SCALE / zoom
    )
    ax.set_ylim(
        center[1] - 0.5 * fov_rad * distance * IM_SCALE / screen_aspect / zoom,
        center[1] + 0.5 * fov_rad * distance * IM_SCALE / screen_aspect / zoom
    )
    plt.axis('off')
    # ax.set_xticks([])
    # ax.set_yticks([])
    return fig
