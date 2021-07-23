import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS

plt.switch_backend('Agg')
plt.rcParams['font.size'] = 18
plt.style.use('dark_background')


# Hitbox was generated externally with photoshop and some down-sampling
DEFAULT_TARGET_FILEPATH = 'hitbox_cod1.npy'
# The "regions" are painted in with the following grayscale colors:
TARGET_REGIONS = {'head': 255, 'chest': 207, 'stomach': 126, 'extremities': 71, 'miss': 0}

# Load hit-box array and transpose it so that rows -> X values and columns -> Y values
TARGET = np.load(DEFAULT_TARGET_FILEPATH)[::-1].T

# Conversion factor for going between pixels and meters in target frame.
MODEL_HEIGHT_PIXELS = 404   # pixel height of HITBOX
MODEL_HEIGHT_METERS = 1.8   # estimated physical height, about 6 ft
IM_SCALE = MODEL_HEIGHT_PIXELS / MODEL_HEIGHT_METERS

# Target hp for TTK/STK calculation
DEFAULT_TARGET_HP = 250.0


def get_aim_center(offset, target=TARGET, im_center=None):
    offset_x = int(offset[0] * IM_SCALE)
    offset_y = int(offset[1] * IM_SCALE)
    if im_center is None:
        im_center = (int(target.shape[0] / 2), int(target.shape[1] / 2))
    aim_x = im_center[0] + offset_x
    aim_y = im_center[1] + offset_y
    center = (aim_x, aim_y)
    return center


def get_beam_box(center_pix, spread, distance, im_scale=IM_SCALE):
    spread_pix = (
        spread[0] * (np.pi / 180.) * distance * im_scale,
        spread[1] * (np.pi / 180.) * distance * im_scale
    )
    beam_box = (
        center_pix[0] - spread_pix[0] / 2,
        center_pix[0] + spread_pix[0] / 2,
        center_pix[1] - spread_pix[1] / 2,
        center_pix[1] + spread_pix[1] / 2,
    )
    return beam_box


def create_targets(damage_profile, target=TARGET, target_regions=TARGET_REGIONS):
    num_segments = len(damage_profile)
    out = np.zeros((num_segments, *target.shape), dtype=float)
    for i in range(out.shape[0]):
        dmg = {v: damage_profile[i][k] for k, v in target_regions.items() if k != 'miss'}
        for k, v in dmg.items():
            out[i, target == k] = v
    return out


def create_beam_profile(im_shape, beam_box, gaussian=True, gaussian_scale=3.):
    x0, x1, y0, y1 = beam_box
    x_spread = x1 - x0
    y_spread = y1 - y0
    center = (x0 + x_spread / 2, y0 + y_spread / 2)
    Y, X = np.meshgrid(range(im_shape[1]), range(im_shape[0]))
    if gaussian:
        x_sigma = x_spread / gaussian_scale
        y_sigma = y_spread / gaussian_scale
        out = np.exp(-((X - center[0]) / x_sigma) ** 2 - ((Y - center[1]) / y_sigma) ** 2)
    else:
        out = np.zeros(im_shape, dtype=float)
        out[(X > x0) & (X < x1) & (Y > y0) & (Y < y1)] = 1
    out /= out.sum()
    return out


def resize_target(target, center_pix, beam_box):
    x0, x1, y0, y1 = beam_box
    beam_x = x1 - x0
    beam_y = y1 - y0
    padding = (
        (
            max(0, int(np.ceil(-x0))),
            max(0, int(np.ceil(x1 - target.shape[0]))),
        ),
        (
            max(0, int(np.ceil(-y0))),
            max(0, int(np.ceil(y1 - target.shape[1]))),
        )
    )
    target_new = np.pad(target, padding)
    center_pix_new = (center_pix[0] + padding[0][0], center_pix[1] + padding[1][0])
    beam_box_new = (
        center_pix_new[0] - beam_x / 2,
        center_pix_new[0] + beam_x / 2,
        center_pix_new[1] - beam_y / 2,
        center_pix_new[1] + beam_y / 2,
    )
    return target_new, center_pix_new, beam_box_new


def apply_damage(dpr, distance, wpn, ads=False, hp=DEFAULT_TARGET_HP, free_hit=0):
    rps = wpn['fire_rate'] / 60.
    if free_hit > 0:
        hp -= free_hit
        stk = int(np.ceil(hp / dpr)) + 1
    else:
        stk = int(np.ceil(hp / dpr))
    dps = dpr * rps
    t_travel = distance / wpn['bullet_velocity']
    t_reload = wpn['reload_time'] * int((stk - 1) / wpn['mag_size'])
    ttk = hp / dps + t_travel + t_reload
    if free_hit > 0:
        ttk += 1. / rps
    if ads:
        ttk += wpn['ads'] / 1000.
    return dps, stk, ttk


def analyze(weapons, distances, center, ads=False, target=TARGET, target_regions=TARGET_REGIONS):
    center_pix = get_aim_center(center, target=target)
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
        targets_dmg = create_targets(
            damage_profile,
            target=target,
            target_regions=target_regions
        )
        edges = [d['dropoff'] for d in damage_profile]
        edges.append(1e99)
        for i in range(len(edges) - 1):
            target_dmg = targets_dmg[i]
            dpr_nr = target_dmg[center_pix[0], center_pix[1]]
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
                    beam_box = get_beam_box(center_pix, spread, distance)
                    target_dmg_new, _, beam_box_new = resize_target(target_dmg, center_pix, beam_box)
                    beam_profile = create_beam_profile(target_dmg_new.shape, beam_box_new)
                    dpr = np.sum(target_dmg_new * beam_profile)
                    results = apply_damage(dpr, distance, wpn, ads=ads, free_hit=dpr_nr)
                    results_nr = apply_damage(dpr_nr, distance, wpn, ads=ads)
                    dps_segment[j], stk_segment[j], ttk_segment[j] = results
                    dps_nr_segment[j], stk_nr_segment[j], ttk_nr_segment[j] = results_nr
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
        x_min = min([min(trace['x']) for trace in fig_data])
        x_max = max([max(trace['x']) for trace in fig_data])
        y_min = min([min(trace['y']) for trace in fig_data])
        y_max = max([max(trace['y']) for trace in fig_data])
        if log_x:
            if x_max >= 100:
                fig.update_xaxes(
                    title_text="Distance [m]",
                    range=[np.log10(x_min), np.log10(x_max)],
                    type='log',
                    tickformat='.1r'
                )
            else:
                fig.update_xaxes(
                    title_text="Distance [m]",
                    range=[np.log10(x_min), np.log10(x_max)],
                    type='log',
                    tickformat=None
                )
        else:
            fig.update_xaxes(title_text="Distance [m]", range=[x_min, x_max], type='linear')
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


def plot_beam_profile(weapon_data, distance, center, zoom=1, fov=80, target=TARGET):
    fov_rad = fov * np.pi / 180.
    screen_width = 10
    screen_aspect = 16 / 9.
    center_pix = get_aim_center(center, target=target)
    spread = weapon_data['spread']
    beam_box = get_beam_box(center_pix, spread, distance)
    target, center_pix, beam_box = resize_target(target, center_pix, beam_box)
    beam_profile = create_beam_profile(target.shape, beam_box)
    fig, ax = plt.subplots(1, 1, figsize=(screen_width, screen_width / screen_aspect))
    ax.set_position([0, 0, 1, 1])
    ax.imshow(target.T, origin='lower', cmap='gray')
    ax.imshow(beam_profile.T, origin='lower', cmap='copper', alpha=0.8)
    ax.plot(beam_box[:2], [center_pix[1], center_pix[1]], color='r')
    ax.plot([center_pix[0], center_pix[0]], beam_box[2:], color='r')
    ax.set_aspect('equal')
    ax.set_xlim(
        center_pix[0] - 0.5 * fov_rad * distance * IM_SCALE / zoom,
        center_pix[0] + 0.5 * fov_rad * distance * IM_SCALE / zoom
    )
    ax.set_ylim(
        center_pix[1] - 0.5 * fov_rad * distance * IM_SCALE / screen_aspect / zoom,
        center_pix[1] + 0.5 * fov_rad * distance * IM_SCALE / screen_aspect / zoom
    )
    plt.axis('off')
    return fig
