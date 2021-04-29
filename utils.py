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


def generate_target_map(shape, distance, aim_center, spread, gaussian=True, gaussian_scale=3.):
    x_spread = spread[0] * (np.pi / 180.) * distance * IM_SCALE
    y_spread = spread[1] * (np.pi / 180.) * distance * IM_SCALE
    Y, X = np.meshgrid(range(shape[0]), range(shape[1]))
    xa, xb = aim_center[0] - x_spread / 2, aim_center[0] + x_spread / 2
    ya, yb = aim_center[1] - y_spread / 2, aim_center[1] + y_spread / 2
    if gaussian:
        x_sigma = x_spread / gaussian_scale
        y_sigma = y_spread / gaussian_scale
        target_map = np.exp(-((X - aim_center[0]) / x_sigma) ** 2 - ((Y - aim_center[1]) / y_sigma) ** 2)
    else:
        target_map = np.zeros(shape, dtype=float)
        target_map[(X > xa) & (X < xb) & (Y > ya) & (Y < yb)] = 1
    target_map /= target_map.sum()
    return target_map


def measure_stk_ttk(dpr, distance, wpn, ads=False):
    hp = 250.0
    stk = int(np.ceil(hp / dpr))
    rps = wpn['fire_rate'] / 60.
    dps = dpr * rps
    t_travel = distance / wpn['bullet_velocity']
    t_reload = wpn['reload_time'] * int((stk - 1) / wpn['mag_size'])
    ttk = hp / dps + t_travel + t_reload
    if ads:
        ttk += wpn['ads'] / 1000.
    return dps, stk, ttk


def analyze(weapons, distances, center, ads=False, hitbox=HITBOX, hitbox_regions=HITBOX_REGIONS):
    num_distances = len(distances)
    dps = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    stk = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    ttk = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
    dps_nr = {wpn['gun']: np.zeros(num_distances) for wpn in weapons}
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
                dps_segment = np.zeros(len(distances_segment))
                stk_segment = np.zeros(len(distances_segment))
                ttk_segment = np.zeros(len(distances_segment))
                dps_nr_segment = np.zeros(len(distances_segment))
                stk_nr_segment = np.zeros(len(distances_segment))
                ttk_nr_segment = np.zeros(len(distances_segment))
                for j, distance in enumerate(distances_segment):
                    distance = distances_segment[j]
                    spread = wpn['spread']
                    target_map = generate_target_map(dmg_map.shape, distance, center, spread)
                    dpr = np.sum(dmg_map * target_map)
                    dps_segment[j], stk_segment[j], ttk_segment[j] = measure_stk_ttk(dpr, distance, wpn, ads=ads)
                    dps_nr_segment[j], stk_nr_segment[j], ttk_nr_segment[j] = measure_stk_ttk(dpr_nr, distance, wpn, ads=ads)
                dps[gun][segment] = dps_segment
                stk[gun][segment] = stk_segment
                ttk[gun][segment] = ttk_segment
                dps_nr[gun][segment] = dps_nr_segment
                stk_nr[gun][segment] = stk_nr_segment
                ttk_nr[gun][segment] = ttk_nr_segment
            else:
                raise ValueError("Aim center must be inside of hitbox")
    results = (dps, stk, ttk, dps_nr, stk_nr, ttk_nr)
    return results


def plot_results(distances, data, results, mode='ttk', log_x=False, log_y=False, show_nr=False):
    fig = go.Figure()
    fig.update_layout(
        width=1100,
        height=500,
        hovermode='x unified',
        template='plotly_dark',
    )
    if results is not None:
        dps, stk, ttk, dps_nr, stk_nr, ttk_nr = results
        guns = list(stk.keys())
        fig.data = []
        y_min = 1e99
        y_max = -1e99
        for i, gun in enumerate(guns):
            assert (mode in ('dps', 'stk', 'ttk')), "invalid plot mode"
            y = eval(mode)[gun]
            y_nr = eval(mode + '_nr')[gun]
            if min(y) < y_min:
                y_min = min(y)
            if max(y) > y_max:
                y_max = max(y)
            color = DEFAULT_PLOTLY_COLORS[i]
            if mode == 'stk':
                shape = 'hv'
            else:
                shape = 'linear'
            traces = [
                go.Scatter(
                    mode='lines',
                    x=distances,
                    y=y,
                    name=gun,
                    line=dict(color=color, shape=shape)
                ),
                go.Scatter(
                    mode='lines',
                    x=distances,
                    y=y_nr,
                    name=gun + ' (no recoil)',
                    line=dict(color=color, dash='dash', shape=shape),
                )
            ]
            mag_cap = np.argmax(np.asarray(stk[gun]) > data[i]['mag_size']) - 1
            if mag_cap > 0:
                traces.append(
                    go.Scatter(
                        mode='markers',
                        x=[distances[mag_cap]],
                        y=[y[mag_cap]],
                        name=gun + ' mag cap',
                        marker=dict(color=color, size=15, symbol='star'),
                        showlegend=False,
                    )
                )
            fig.add_traces(traces)
    update_fig(fig, mode=mode, log_x=log_x, log_y=log_y, show_nr=show_nr)
    return fig


def update_fig(fig, mode='ttk', log_x=False, log_y=False, show_nr=False):
    fig_data = fig['data']
    if len(fig_data) > 0:
        x_max = max([max(trace['x']) for trace in fig_data])
        y_min = min([min(trace['y']) for trace in fig_data])
        y_max = max([max(trace['y']) for trace in fig_data])
        if log_x:
            if x_max >= 100:
                fig.update_xaxes(title_text="Distance [m]", range=[1, np.log10(x_max)], type='log', tickformat='.1r')
            else:
                fig.update_xaxes(title_text="Distance [m]", range=[1, np.log10(x_max)], type='log', tickformat=None)
        else:
            fig.update_xaxes(title_text="Distance [m]", range=[0, x_max], type='linear')
        y_label = {
            'dps': "Damage per second",
            'stk': "Shots-to-kill",
            'ttk': "Time-to-kill [s]",
        }[mode]
        if log_y:
            if y_max > 10 * y_min:
                fig.update_yaxes(title_text=y_label, range=[np.log10(y_min), np.log10(y_max)], type='log', tickformat='.1r')
            else:
                fig.update_yaxes(title_text=y_label, range=[np.log10(y_min), np.log10(y_max)], type='log')
        else:
            fig.update_yaxes(title_text=y_label, range=[0, y_max], type='linear')
        for trace in fig_data:
            trace.visible = ('(no recoil)' not in trace['name'] or show_nr == 'show')
    else:
        fig.update_xaxes(title_text="Distance [m]", range=[1, 100])
        fig.update_yaxes(title_text="Time-to-kill [s]", range=[1, 5])
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
    spread = weapon_data['spread']
    x_spread = spread[0] * (np.pi / 180.) * distance * IM_SCALE
    y_spread = spread[1] * (np.pi / 180.) * distance * IM_SCALE
    target_x0 = center[0] - x_spread / 2
    target_y0 = center[1] - y_spread / 2
    # target_rect = patches.Rectangle((target_x0, target_y0), x_spread, y_spread,
    #                                 linewidth=1, linestyle=':', edgecolor='r', facecolor='none')
    target_map = generate_target_map(hitbox.shape, distance, center, spread)
    fig, ax = plt.subplots(1, 1, figsize=(screen_width, screen_width / screen_aspect))
    ax.set_position([0, 0, 1, 1])
    ax.imshow(hitbox.T, origin='lower', cmap='gray')
    ax.imshow(target_map.T, origin='lower', cmap='copper', alpha=0.8)
    ax.plot([target_x0, target_x0 + x_spread], [center[1], center[1]], color='r')
    ax.plot([center[0], center[0]], [target_y0, target_y0 + y_spread], color='r')
    # ax.plot(center[0], center[1], 'y+', ms=30)
    # ax.add_patch(target_rect)
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
    return fig
